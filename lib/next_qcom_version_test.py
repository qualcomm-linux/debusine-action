"""pytest coverage for debchange-style qcom version increments."""

# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear

import pytest

from next_qcom_version import increment_qcom_version

# Written by QGenie

@pytest.mark.parametrize(
    ("version", "expected"),
    [
        ("1.2-3", "1.2-3qcom1"),
        ("2:1.2-3", "2:1.2-3qcom1"),
        ("1.2", "1.2qcom1"),
        ("1.2qcom1", "1.2qcom2"),
        ("1.2-3qcom1", "1.2-3qcom2"),
        ("1.2-3qcom9", "1.2-3qcom10"),
        ("1.2-3qcom1~", "1.2-3qcom2~"),
        ("1.2-3qcom1+", "1.2-3qcom2+"),
        ("1.2-3~ppa1", "1.2-4~ppa1"),
        ("1.2-3~ppa1.1", "1.2-4~ppa1.1"),
        ("1.2build1", "1.2qcom1"),
        ("1.2qcombuild1", "1.3qcom"),
        ("1.2qcom", "1.3qcom"),
        ("1.0.7qcom10~bpo1", "1.0.7qcom10~bpo2"),
    ],
)
def test_increment_qcom_version(version: str, expected: str) -> None:
    """Increment versions the same way dch -i does for Ubuntu, but with qcom."""
    assert increment_qcom_version(version) == expected


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
        increment_qcom_version(version)
