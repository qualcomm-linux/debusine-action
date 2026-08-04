# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear

"""
Shared fixtures for the Debusine infrastructure test suite.

All Debusine API calls use python3-debusine >= 0.14.9 directly.
Run: source ./setenv, then py.test-3 with any pytest args.
"""

import os

import pytest

pytest_plugins = ["build_fixtures", "publish_fixtures"]


# ---------------------------------------------------------------------------
# Credential enforcement — fail at collection time, not per-test
# ---------------------------------------------------------------------------

_REQUIRED_VARS = [
    "DEBUSINE_HOST",
    "DEBUSINE_SCOPE",
    "DEBUSINE_USER",
    "DEBUSINE_TOKEN",
    "DEBUSINE_PRODUCTION_RELEASE_TOKEN",
    "DEBUSINE_STAGING_RELEASE_TOKEN",
]


def pytest_configure(config):
    missing = [v for v in _REQUIRED_VARS if not os.environ.get(v)]
    if missing:
        pytest.exit(
            f"Missing required environment variables: {', '.join(missing)}. "
            "Run: source ./setenv",
            returncode=3,
        )


# ---------------------------------------------------------------------------
# Parametrized fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session", params=["trixie", "forky"])
def suite(request):
    return request.param


@pytest.fixture(scope="session", params=["main", "contrib", "non-free", "non-free-firmware"])
def component(request):
    return request.param


@pytest.fixture(scope="session", params=["qli", "qli-staging"])
def target_workspace(request):
    return request.param


# ---------------------------------------------------------------------------
# Credential fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def creds():
    return {
        "host": os.environ["DEBUSINE_HOST"],
        "scope": os.environ["DEBUSINE_SCOPE"],
        "user": os.environ["DEBUSINE_USER"],
        "token": os.environ["DEBUSINE_TOKEN"],
        "parent_workspace": os.environ.get("DEBUSINE_PARENT_WORKSPACE", "qli-ci"),
    }


@pytest.fixture(scope="session")
def release_token(target_workspace):
    if target_workspace == "qli":
        return os.environ["DEBUSINE_PRODUCTION_RELEASE_TOKEN"]
    return os.environ["DEBUSINE_STAGING_RELEASE_TOKEN"]
