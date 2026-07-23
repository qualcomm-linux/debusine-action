#!/usr/bin/python3

# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear

"""
Wait for a debusine workflow (work request) to reach a terminal state.

Usage
-----
Extract the work request ID from ``debusine workflow start --yaml`` and pass
it to this script::

    # PowerShell
    $id = (debusine workflow start --yaml --data params.yaml my-template |
           python -c "import sys,yaml; print(yaml.safe_load(sys.stdin)['id'])")
    python scripts/poll_workflow.py $id

    # Bash
    id=$(debusine workflow start --yaml --data params.yaml my-template |
         python -c "import sys,yaml; print(yaml.safe_load(sys.stdin)['id'])")
    python scripts/poll_workflow.py "$id"

Exit codes
----------
0  Workflow completed with result ``success``.
1  Workflow completed with result ``failure``, ``error``, or ``skipped``.
2  Timeout reached before the workflow completed.
3  Configuration or connection error.
"""

import argparse
import asyncio
import logging
import os
import sys
import yaml

from debusine.client.config import ConfigHandler
from debusine.client.debusine import Debusine
from debusine.client.exceptions import (
    ClientConnectionError,
    NotFoundError,
    UnexpectedResponseError,
)
from debusine.client.models import OnWorkRequestCompleted, WorkRequestResponse

# Results that indicate the work request has finished.
_TERMINAL_RESULTS = {"success", "failure", "error", "skipped"}

# Statuses that mean the work request is still actively progressing.
_ACTIVE_STATUSES = {"pending", "running"}

# Timeout (seconds) for establishing the WebSocket connection.
_CONNECTION_TIMEOUT = 60


def _build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="poll_workflow.py",
        description=(
            "Wait for a debusine workflow (work request) to complete."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "work_request_id",
        type=int,
        help=(
            "Work request ID to wait for. "
            "Obtain it from the 'id' field of 'debusine workflow start --yaml'."
        ),
    )
    parser.add_argument(
        "--server",
        default=None,
        help=(
            "Debusine server to use, either by section name or as FQDN/scope. "
            "Uses the configuration file default if not specified."
        ),
    )
    parser.add_argument(
        "--config-file",
        default=ConfigHandler.DEFAULT_CONFIG_FILE_PATH,
        help="Path to the debusine client configuration file.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=None,
        metavar="SECONDS",
        help=(
            "Maximum total time to wait for the workflow to complete, in seconds. "
            "If not specified, wait indefinitely."
        ),
    )
    parser.add_argument(
        "--yaml",
        action="store_true",
        help="Print the final WorkRequestResponse as YAML on stdout.",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress progress messages (errors are still printed).",
    )
    return parser


def _setup_logging(quiet: bool) -> logging.Logger:
    logger = logging.getLogger("poll_workflow")
    logger.setLevel(logging.WARNING if quiet else logging.INFO)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    return logger


def _build_debusine_client(args: argparse.Namespace, logger: logging.Logger) -> Debusine:
    """Load configuration and return an authenticated Debusine client."""
    server_name: str | None = os.environ.get("DEBUSINE_SERVER_NAME")
    if args.server is not None:
        server_name = args.server

    try:
        config = ConfigHandler(
            server_name=server_name,
            config_file_path=args.config_file,
        )
        server_info = config.server_configuration()
    except SystemExit:
        # ConfigHandler calls sys.exit(3) on bad config; re-raise as-is.
        raise
    except ValueError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        raise SystemExit(3) from exc

    return Debusine(
        base_api_url=server_info.api_url,
        api_token=server_info.api_token,
        scope=server_info.scope,
        logger=logger,
    )


async def _wait_until_complete(
    client: Debusine,
    work_request_id: int,
    *,
    timeout: float | None,
    logger: logging.Logger,
) -> str:
    """
    Wait for ``work_request_id`` to reach a terminal state via WebSocket push.

    Establishes the WebSocket connection and waits for the "connected"
    acknowledgement before checking the current HTTP status. This ordering
    ensures no completion is missed: once the server acknowledges the
    connection it will deliver any subsequent completion over the socket,
    and the HTTP check catches anything that completed before that point.

    :param client: authenticated Debusine client.
    :param work_request_id: ID of the work request to wait for.
    :param timeout: maximum time to wait for the workflow to complete (seconds),
        or ``None`` to wait indefinitely.
    :param logger: logger for progress messages.
    :returns: the result string (e.g. ``"success"``, ``"failure"``).
    :raises asyncio.TimeoutError: if the workflow timeout is reached.
    :raises SystemExit(3): on connection timeout or unexpected stream end.
    """
    async with client.server_notifications(
        endpoint="1.0/work-request/on-completed/"
    ) as sn:
        loop = asyncio.get_running_loop()
        connected_event = asyncio.Event()
        result_future: asyncio.Future[str] = loop.create_future()

        async def _listen() -> None:
            async for payload in sn.messages():
                text = payload.get("text")
                if text == "connected":
                    logger.info(
                        "Connected. Waiting for work request %d to complete…",
                        work_request_id,
                    )
                    # Now that the server is tracking completions, check
                    # whether the work request already finished.
                    try:
                        wr = client.work_request_get(work_request_id)
                    except Exception as exc:
                        if not result_future.done():
                            result_future.set_exception(exc)
                        return
                    if wr.result in _TERMINAL_RESULTS:
                        if not result_future.done():
                            result_future.set_result(wr.result)
                        return
                    if wr.status not in _ACTIVE_STATUSES:
                        # Non-active status with no recognised result (e.g.
                        # aborted): no push will arrive, so resolve now.
                        if not result_future.done():
                            result_future.set_result(wr.result or "error")
                        return
                    connected_event.set()
                elif text == "work_request_completed":
                    msg = OnWorkRequestCompleted.model_validate(payload)
                    if msg.work_request_id == work_request_id:
                        if not result_future.done():
                            result_future.set_result(msg.result)
                        return
                    logger.debug(
                        "Ignoring completion of work request %d",
                        msg.work_request_id,
                    )
                else:
                    logger.warning("Unexpected message from server: %r", text)
            if not result_future.done():
                result_future.set_exception(
                    RuntimeError("Server notification stream ended unexpectedly")
                )

        listen_task = asyncio.create_task(_listen())
        try:
            # Wait for "connected" (or immediate result if already complete).
            connected_wait_task = asyncio.ensure_future(connected_event.wait())
            done, _ = await asyncio.wait(
                {connected_wait_task, result_future},
                timeout=_CONNECTION_TIMEOUT,
                return_when=asyncio.FIRST_COMPLETED,
            )
            if not done:
                print(
                    f"Error: timed out waiting for server connection "
                    f"after {_CONNECTION_TIMEOUT:.0f} s.",
                    file=sys.stderr,
                )
                raise SystemExit(3)
            if result_future in done:
                return result_future.result()

            # Connected; now wait for the workflow result.
            return await asyncio.wait_for(result_future, timeout=timeout)
        finally:
            connected_wait_task.cancel()
            listen_task.cancel()
            for task in (connected_wait_task, listen_task):
                try:
                    await task
                except (asyncio.CancelledError, Exception):
                    pass


def poll_until_complete(
    client: Debusine,
    work_request_id: int,
    *,
    max_interval: float,
    timeout: float | None,
    logger: logging.Logger,
) -> WorkRequestResponse:
    """
    Wait for ``work_request_id`` to reach a terminal state.

    ``max_interval`` is accepted for interface compatibility but ignored;
    notifications are now push-based via WebSocket.

    :param client: authenticated Debusine client.
    :param work_request_id: ID of the work request to wait for.
    :param max_interval: ignored (kept for interface compatibility).
    :param timeout: maximum total time to wait in seconds, or ``None``.
    :param logger: logger for progress messages.
    :returns: the final :class:`WorkRequestResponse`.
    :raises SystemExit(3): on unrecoverable connection errors.
    """
    asyncio.run(
        _wait_until_complete(
            client,
            work_request_id,
            timeout=timeout,
            logger=logger,
        )
    )
    return client.work_request_get(work_request_id)


def main() -> None:
    """Entry point."""
    parser = _build_argument_parser()
    args = parser.parse_args()

    logger = _setup_logging(args.quiet)

    client = _build_debusine_client(args, logger)

    logger.info(
        "Waiting for work request %d%s …",
        args.work_request_id,
        f" (timeout={args.timeout:.0f} s)" if args.timeout else "",
    )

    try:
        final_wr = poll_until_complete(
            client,
            args.work_request_id,
            max_interval=0,
            timeout=args.timeout,
            logger=logger,
        )
    except asyncio.TimeoutError:
        print(
            f"Timeout: work request {args.work_request_id} did not complete "
            f"within {args.timeout:.0f} s.",
            file=sys.stderr,
        )
        raise SystemExit(2)
    except NotFoundError:
        print(
            f"Error: work request {args.work_request_id} not found.",
            file=sys.stderr,
        )
        raise SystemExit(3)
    except (ClientConnectionError, UnexpectedResponseError) as exc:
        print(f"Connection error: {exc}", file=sys.stderr)
        raise SystemExit(3)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(3)

    logger.info(
        "Work request %d finished: status=%s result=%s",
        args.work_request_id,
        final_wr.status,
        final_wr.result,
    )

    if args.yaml:
        output = yaml.safe_dump(
            final_wr.model_dump(mode="json"), sort_keys=False
        )
        print(output, end="")

    if final_wr.result == "success":
        raise SystemExit(0)
    else:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
