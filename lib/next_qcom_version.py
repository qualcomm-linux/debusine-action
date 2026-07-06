#!/usr/bin/python3

# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear

"""Helpers for debchange-style vendor version increments.

Debian version strings have the form ``[epoch:]upstream_version[-debian_revision]``;
see Debian Policy §5.6.12:
https://www.debian.org/doc/debian-policy/ch-controlfields.html#s-f-version

This module implements the subset of ``debchange -i`` behaviour that is specific
to Ubuntu vendor versioning, but replaces the substring ``ubuntu`` with a
configurable identifier (default: ``qli``). The function operates on a full
Debian package version string and returns the incremented version string.

Migration: if the version already carries a legacy ``qcom`` suffix and the
requested identifier differs, the ``qcom`` suffix is replaced by the new
identifier and the version number is incremented rather than re-appended.
"""

# Written by QGenie

from __future__ import annotations

import re
import sys

_INCREMENTABLE_RE = re.compile(r"^(.*?)([a-yA-Y][a-zA-Z]*|\d+)([+~])?$", re.IGNORECASE)
_NATIVE_QCOM_RE = re.compile(r"^(.*?)(\d+)$", re.IGNORECASE)


def increment_qcom_version(version: str, identifier: str = 'qli') -> str:
    """Return the next debchange-style vendor version for ``version``.

    The behaviour matches the ``dch -i`` Ubuntu-specific path in
    ``scripts/debchange.pl``, except that ``identifier`` is used where Ubuntu
    uses ``ubuntu``:

    * if the version does not already end in an identifier/ppa derivative
      suffix, append ``<identifier>1``;
    * if the version carries a ``build`` suffix, drop that suffix before adding
      ``<identifier>1``;
    * for a native package ending in ``identifier`` (or legacy ``qcom``) with no
      trailing digit, bump the numeric tail immediately before the suffix and
      keep the suffix (migrating ``qcom`` to ``identifier`` if they differ);
    * otherwise, increment the final alphanumeric component the same way
      ``dch -i`` does, migrating a legacy ``qcom`` suffix to ``identifier``.

    Args:
        version: A Debian package version string.
        identifier: The vendor identifier string to use (e.g. ``qli`` or
            ``qli+staging``).

    Returns:
        The incremented Debian package version string.

    Raises:
        ValueError: If the version cannot be parsed according to the subset of
            Debian version syntax handled here, or when the version has a
            contradictory native/Non-native identifier form analogous to
            debchange's fatal error.
    """
    # Check for ~ppa versions - increment the debian revision before ~ppa
    ppa_match = re.match(r"^(.*?)(\d+)(~ppa.*)$", version)
    if ppa_match:
        # For ~ppa versions, increment the debian revision and keep the ppa suffix
        prefix, debian_rev, ppa_suffix = ppa_match.groups()
        return f"{prefix}{int(debian_rev) + 1}{ppa_suffix}"

    # Check for ~bpo versions: ~bpoN+M increments M; ~bpoN increments N
    bpo_match = re.match(r"^(.*?~bpo)(\d+)(\+(\d+))?$", version)
    if bpo_match:
        prefix, bpo_num, plus_group, local_num = bpo_match.groups()
        if local_num is not None:
            return f"{prefix}{bpo_num}+{int(local_num) + 1}"
        return f"{prefix}{int(bpo_num) + 1}"

    match = _INCREMENTABLE_RE.match(version)
    if not match:
        raise ValueError(f"unable to parse Debian version: {version!r}")

    start, end, extra = match.groups()
    extra = extra or ""

    # Validate that we have a reasonable version format
    # Reject versions with ~ that aren't identifier/ppa related
    if "~" in version and not re.search(rf"({re.escape(identifier)}|qcom|~ppa)", version):
        raise ValueError(f"unable to parse Debian version: {version!r}")

    # Reject versions that don't look like valid Debian versions
    # Must have at least one digit or be in a recognized format
    if not re.search(r"\d", version) or (not re.search(r"[-.]", version) and not re.search(rf"{re.escape(identifier)}|qcom|build", version)):
        raise ValueError(f"unable to parse Debian version: {version!r}")

    # "already versioned" pattern: matches new identifier, or legacy qcom
    already_versioned_re = rf"({re.escape(identifier)}|qcom|~ppa)(\d+\.)*$"
    if not re.search(already_versioned_re, start):
        build_id_pattern = f"(?:{re.escape(identifier)}|qcom)"
        build_match = re.match(rf"(.*?)({build_id_pattern})?(\.?build)", start)
        if build_match:
            start = build_match.group(1)
            end = build_match.group(2) or ""

        known_end = end in (identifier, 'qcom')
        if known_end:
            native_match = _NATIVE_QCOM_RE.match(start)
            if not native_match:
                raise ValueError(
                    f"native vendor version is missing the numeric part before "
                    f"the identifier: {version!r}"
                )
            if "-" in version:
                raise ValueError(
                    "version suffix indicates native vendor package, but the "
                    "included '-' suggests the contrary"
                )
            version_head, version_tail = native_match.groups()
            start = f"{version_head}{int(version_tail) + 1}"
            # Migrate legacy qcom to new identifier
            end = identifier
        else:
            end = f"{end}{identifier}1"
    else:
        # Migrate legacy qcom suffix to new identifier before incrementing
        if identifier != 'qcom' and re.search(r"qcom(\d+\.)*$", start):
            start = re.sub(r"qcom$", identifier, start)
        if end.isdigit():
            end = str(int(end) + 1)
        else:
            raise ValueError(f"unable to increment non-numeric version tail: {version!r}")

    return f"{start}{end}{extra}"

if __name__ == '__main__':
    ident = sys.argv[2] if len(sys.argv) > 2 else 'qli'
    print(increment_qcom_version(sys.argv[1], ident))
