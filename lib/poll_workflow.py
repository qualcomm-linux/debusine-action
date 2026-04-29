#!/usr/bin/python3

# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear

# Written by QGenie / claude-4-6-sonnet

"""
Poll a debusine workflow (work request) until it reaches a terminal state.

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
import logging
import os
import sys
from collections.abc import Callable

import tenacity
import yaml

from debusine.client.config import ConfigHandler
from debusine.client.debusine import Debusine
from debusine.client.exceptions import (
    ClientConnectionError,
    NotFoundError,
    UnexpectedResponseError,
)
from debusine.client.models import WorkRequestResponse

# Results that indicate the work request has finished.
_TERMINAL_RESULTS = {"success", "failure", "error", "skipped"}

# Statuses that mean the work request is still actively progressing and should
# continue to be polled if no terminal result has been recorded yet.
_ACTIVE_STATUSES = {"pending", "running"}

# Default adaptive polling parameters (seconds).
_DEFAULT_WAIT_START = 5
_DEFAULT_WAIT_INCREMENT = 5
_DEFAULT_WAIT_MAX = 60


def _build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="poll_workflow.py",
        description=(
            "Poll a debusine workflow (work request) until it completes."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "work_request_id",
        type=int,
        help=(
            "Work request ID to poll. "
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
        "--max-interval",
        type=float,
        default=_DEFAULT_WAIT_MAX,
        metavar="SECONDS",
        help=(
            "Maximum polling interval in seconds. "
            "The script starts polling every %(default)s s and increases the "
            "interval by %(default)s s each attempt up to this cap."
        ),
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=None,
        metavar="SECONDS",
        help=(
            "Maximum total time to wait in seconds before giving up. "
            "If not specified, poll indefinitely."
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


def _make_before_sleep_log(
    work_request_id: int,
    logger: logging.Logger,
) -> "Callable[[tenacity.RetryCallState], None]":
    """Return a tenacity before_sleep hook that logs the current status."""

    def _before_sleep(retry_state: tenacity.RetryCallState) -> None:
        if retry_state.outcome is None:
            return
        exc = retry_state.outcome.exception()
        if exc is not None:
            logger.info(
                "Work request %d: connection error (%s). Retrying in %.0f s …",
                work_request_id,
                exc,
                retry_state.next_action.sleep,  # type: ignore[union-attr]
            )
            return
        wr: WorkRequestResponse = retry_state.outcome.result()
        elapsed = retry_state.outcome_timestamp - retry_state.start_time
        logger.info(
            "Work request %d: status=%s result=%r  (elapsed %.0f s, "
            "next poll in %.0f s)",
            work_request_id,
            wr.status,
            wr.result or "(pending)",
            elapsed,
            retry_state.next_action.sleep,  # type: ignore[union-attr]
        )

    return _before_sleep


def _should_continue_polling(wr: WorkRequestResponse) -> bool:
    """Return True while the work request is still in a non-terminal state."""
    if wr.result in _TERMINAL_RESULTS:
        return False
    return wr.status in _ACTIVE_STATUSES


def poll_until_complete(
    client: Debusine,
    work_request_id: int,
    *,
    max_interval: float,
    timeout: float | None,
    logger: logging.Logger,
) -> WorkRequestResponse:
    """
    Poll ``work_request_id`` until it reaches a terminal state.

    Uses tenacity to:
    * Retry on transient connection/HTTP errors (exponential backoff, up to
      ~30 s between attempts).
    * Keep polling while the result is still empty, with an incrementing wait
      that starts at ``_DEFAULT_WAIT_START`` s and grows by
      ``_DEFAULT_WAIT_INCREMENT`` s each attempt up to ``max_interval`` s.

    :param client: authenticated Debusine client.
    :param work_request_id: ID of the work request to poll.
    :param max_interval: cap on the polling interval (seconds).
    :param timeout: maximum total elapsed time before giving up (seconds),
        or ``None`` to poll indefinitely.
    :param logger: logger for progress messages.
    :returns: the final :class:`WorkRequestResponse`.
    :raises tenacity.RetryError: if the timeout is reached.
    :raises SystemExit(3): on unrecoverable connection errors.
    """
    # Inner retry: handle transient network errors when fetching the status.
    # Uses exponential backoff capped at 30 s, up to ~5 minutes total.
    _fetch_retry = tenacity.retry(
        retry=tenacity.retry_if_exception_type(
            (ClientConnectionError, UnexpectedResponseError)
        ),
        wait=tenacity.wait_exponential(multiplier=1, min=2, max=30),
        stop=tenacity.stop_after_delay(300),
        reraise=True,
    )

    @_fetch_retry
    def _fetch(wr_id: int) -> WorkRequestResponse:
        return client.work_request_get(wr_id)

    # Outer retry: keep polling while the work request is still active and no
    # terminal result has been recorded yet. If the server reports a
    # non-active/terminal status without a success result (for example an error
    # state), stop polling and let the caller exit non-zero.
    # The wait increments from _DEFAULT_WAIT_START up to max_interval.
    stop_condition: tenacity.stop.stop_base
    if timeout is not None:
        stop_condition = tenacity.stop_after_delay(timeout)
    else:
        stop_condition = tenacity.stop_never

    before_sleep = _make_before_sleep_log(work_request_id, logger)

    poll_retry = tenacity.retry(
        retry=tenacity.retry_if_result(_should_continue_polling),
        wait=tenacity.wait_incrementing(
            start=_DEFAULT_WAIT_START,
            increment=_DEFAULT_WAIT_INCREMENT,
            max=max_interval,
        ),
        stop=stop_condition,
        before_sleep=before_sleep,
        # Do not wrap the result in RetryError on success; re-raise on stop.
        reraise=False,
    )

    @poll_retry
    def _poll() -> WorkRequestResponse:
        return _fetch(work_request_id)

    return _poll()


def main() -> None:
    """Entry point."""
    parser = _build_argument_parser()
    args = parser.parse_args()

    logger = _setup_logging(args.quiet)

    client = _build_debusine_client(args, logger)

    logger.info(
        "Polling work request %d (max_interval=%.0f s%s) …",
        args.work_request_id,
        args.max_interval,
        f", timeout={args.timeout:.0f} s" if args.timeout else "",
    )

    try:
        final_wr = poll_until_complete(
            client,
            args.work_request_id,
            max_interval=args.max_interval,
            timeout=args.timeout,
            logger=logger,
        )
    except tenacity.RetryError:
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
