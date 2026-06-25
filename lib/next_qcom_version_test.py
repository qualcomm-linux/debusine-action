"""pytest coverage for debchange-style vendor version increments."""

# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear

import pytest

from next_qcom_version import increment_qcom_version

# Written by QGenie

@pytest.mark.parametrize(
    ("version", "identifier", "expected"),
    [
        # --- qli identifier (standard) ---
        ("1.2-3", "qli", "1.2-3qli1"),
        ("2:1.2-3", "qli", "2:1.2-3qli1"),
        ("1.2", "qli", "1.2qli1"),
        ("1.2qli1", "qli", "1.2qli2"),
        ("1.2-3qli1", "qli", "1.2-3qli2"),
        ("1.2-3qli9", "qli", "1.2-3qli10"),
        ("1.2-3qli1~", "qli", "1.2-3qli2~"),
        ("1.2-3qli1+", "qli", "1.2-3qli2+"),
        ("1.2-3~ppa1", "qli", "1.2-4~ppa1"),
        ("1.2-3~ppa1.1", "qli", "1.2-4~ppa1.1"),
        ("1.2build1", "qli", "1.2qli1"),
        ("1.2qlibuild1", "qli", "1.3qli"),
        ("1.2qli", "qli", "1.3qli"),
        ("1.0.7qli10~bpo1", "qli", "1.0.7qli10~bpo2"),
        # --- qcom migration: qcom suffix replaced by qli ---
        ("1.2qcom1", "qli", "1.2qli2"),
        ("1.2-3qcom1", "qli", "1.2-3qli2"),
        ("1.2-3qcom9", "qli", "1.2-3qli10"),
        ("1.2qcom", "qli", "1.3qli"),
        ("1.2qcombuild1", "qli", "1.3qli"),
        # --- qli+staging identifier ---
        ("1.2-3", "qli+staging", "1.2-3qli+staging1"),
        ("1.2-3qli+staging1", "qli+staging", "1.2-3qli+staging2"),
        ("1.2-3qli+staging9", "qli+staging", "1.2-3qli+staging10"),
        ("1.2", "qli+staging", "1.2qli+staging1"),
        # --- qcom identifier: backward-compat ---
        ("1.2-3", "qcom", "1.2-3qcom1"),
        ("1.2qcom1", "qcom", "1.2qcom2"),
        ("1.2-3qcom1", "qcom", "1.2-3qcom2"),
        ("1.2qcom", "qcom", "1.3qcom"),
        ("1.2build1", "qcom", "1.2qcom1"),
        ("1.2qcombuild1", "qcom", "1.3qcom"),
    ],
)
def test_increment_qcom_version(version: str, identifier: str, expected: str) -> None:
    """Increment versions the same way dch -i does for Ubuntu, but with identifier."""
    assert increment_qcom_version(version, identifier) == expected


@pytest.mark.parametrize(
    "version",
    [
        "1.2-3qcom",
        "1.2~rc1",
        "invalid",
    ],
)
def test_increment_qcom_version_rejects_invalid_inputs(version: str) -> None:
    """Reject versions outside the supported debchange-derived cases."""
    with pytest.raises(ValueError):
        increment_qcom_version(version, 'qli')
