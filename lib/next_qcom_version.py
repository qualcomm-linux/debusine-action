#!/usr/bin/python3

# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear

"""Helpers for debchange-style qcom version increments.

Debian version strings have the form ``[epoch:]upstream_version[-debian_revision]``;
see Debian Policy §5.6.12:
https://www.debian.org/doc/debian-policy/ch-controlfields.html#s-f-version

This module implements the subset of ``debchange -i`` behaviour that is specific
to Ubuntu vendor versioning, but replaces the substring ``ubuntu`` with
``qcom``. The function operates on a full Debian package version string and
returns the incremented version string.
"""

# Written by QGenie

from __future__ import annotations

import re
import sys

_INCREMENTABLE_RE = re.compile(r"^(.*?)([a-yA-Y][a-zA-Z]*|\d+)([+~])?$", re.IGNORECASE)
_NATIVE_QCOM_RE = re.compile(r"^(.*?)(\d+)$", re.IGNORECASE)


def increment_qcom_version(version: str) -> str:
    """Return the next debchange-style qcom version for ``version``.

    The behaviour matches the ``dch -i`` Ubuntu-specific path in
    ``scripts/debchange.pl``, except that ``qcom`` is used where Ubuntu uses
    ``ubuntu``:

    * if the version does not already end in a qcom/ppa derivative suffix,
      append ``qcom1``;
    * if the version carries a ``build`` suffix, drop that suffix before adding
      ``qcom1``;
    * for a native package ending in ``qcom`` with no trailing digit, bump the
      numeric tail immediately before ``qcom`` and keep the ``qcom`` suffix;
    * otherwise, increment the final alphanumeric component the same way
      ``dch -i`` does.

    Args:
        version: A Debian package version string.

    Returns:
        The incremented Debian package version string.

    Raises:
        ValueError: If the version cannot be parsed according to the subset of
            Debian version syntax handled here, or when the version has a
            contradictory native/Non-native qcom form analogous to debchange's
            fatal error.
    """
    # Check for ~ppa versions - increment the debian revision before ~ppa
    ppa_match = re.match(r"^(.*?)(\d+)(~ppa.*)$", version)
    if ppa_match:
        # For ~ppa versions, increment the debian revision and keep the ppa suffix
        prefix, debian_rev, ppa_suffix = ppa_match.groups()
        return f"{prefix}{int(debian_rev) + 1}{ppa_suffix}"

    # Check for ~bpo versions - increment the bpo number
    bpo_match = re.match(r"^(.*?)(~bpo)(\d+)(.*)$", version)
    if bpo_match:
        # For ~bpo versions, increment the number after bpo
        prefix, bpo_type, bpo_num, suffix = bpo_match.groups()
        return f"{prefix}{bpo_type}{int(bpo_num) + 1}{suffix}"

    match = _INCREMENTABLE_RE.match(version)
    if not match:
        raise ValueError(f"unable to parse Debian version: {version!r}")

    start, end, extra = match.groups()
    extra = extra or ""

    # Validate that we have a reasonable version format
    # Reject versions with ~ that aren't qcom/ppa related
    if "~" in version and not re.search(r"(qcom|~ppa)", version):
        raise ValueError(f"unable to parse Debian version: {version!r}")
    
    # Reject versions that don't look like valid Debian versions
    # Must have at least one digit or be in a recognized format
    if not re.search(r"\d", version) or (not re.search(r"[-.]", version) and not re.search(r"qcom|build", version)):
        raise ValueError(f"unable to parse Debian version: {version!r}")

    if not re.search(r"(qcom|~ppa)(\d+\.)*$", start):
        build_match = re.match(r"(.*?)(qcom)?(\.?build)", start)
        if build_match:
            start = build_match.group(1)
            end = build_match.group(2) or ""

        if end.startswith("qcom"):
            native_match = _NATIVE_QCOM_RE.match(start)
            if not native_match:
                raise ValueError(
                    f"native qcom version is missing the numeric part before "
                    f"'qcom': {version!r}"
                )
            if "-" in version:
                raise ValueError(
                    "version suffix indicates native qcom package, but the "
                    "included '-' suggests the contrary"
                )
            version_head, version_tail = native_match.groups()
            start = f"{version_head}{int(version_tail) + 1}"
        else:
            end = f"{end}qcom1"
    else:
        if end.isdigit():
            end = str(int(end) + 1)
        else:
            raise ValueError(f"unable to increment non-numeric version tail: {version!r}")

    return f"{start}{end}{extra}"

if __name__ == '__main__':
    print(increment_qcom_version(sys.argv[1]))
