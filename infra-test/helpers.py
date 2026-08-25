# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear

"""
Shared helpers for the Debusine infrastructure test suite.
"""

import io
import logging
import lzma
import pathlib
import subprocess
import sys
import tempfile
import textwrap
import time
from collections import namedtuple
from email.utils import formatdate

import requests
import requests.auth
from tenacity import before_sleep_log, retry, retry_if_result, stop_after_delay, wait_exponential

import debian.deb822

from debusine.client.debusine import Debusine

_log = logging.getLogger(__name__)

# poll_workflow lives in lib/, which is not on sys.path by default
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "lib"))
from poll_workflow import poll_until_complete


SourcePackageInfo = namedtuple("SourcePackageInfo", ["dsc_path", "name", "version"])


def make_client(host: str, token: str, scope: str, logger: logging.Logger) -> Debusine:
    """Return an authenticated Debusine API client."""
    return Debusine(
        base_api_url=f"https://{host}/api",
        api_token=token,
        scope=scope,
        logger=logger,
    )


def poll_work_request(client: Debusine, work_request_id: int, logger: logging.Logger):
    """Poll a work request until it reaches a terminal state."""
    return poll_until_complete(
        client,
        work_request_id,
        max_interval=60,
        timeout=None,
        logger=logger,
    )


def create_minimal_source_package(
    build_dir: pathlib.Path, component: str
) -> SourcePackageInfo:
    """
    Build a minimal 3.0 (native) Debian source package in build_dir.

    Returns a SourcePackageInfo with the path to the .dsc, the package name,
    and the version.
    """
    pkg_name = "debusine-infra-test"
    ts = int(time.time())
    version = f"1.0+test{ts}"

    section_map = {
        "main": "misc",
        "contrib": "contrib/misc",
        "non-free": "non-free/misc",
        "non-free-firmware": "non-free-firmware/firmware",
    }
    section = section_map[component]

    srcdir = build_dir / f"{pkg_name}-{version}"
    debian_dir = srcdir / "debian"
    source_dir = debian_dir / "source"
    source_dir.mkdir(parents=True)

    rfc_date = formatdate(ts, localtime=False)
    (debian_dir / "changelog").write_text(
        f"{pkg_name} ({version}) UNRELEASED; urgency=low\n"
        f"\n"
        f"  * Minimal test package for Debusine infra testing.\n"
        f"\n"
        f" -- Infra Test Bot <infra-test@example.com>  {rfc_date}\n",
        encoding="utf-8",
    )

    (debian_dir / "control").write_text(
        textwrap.dedent(f"""\
            Source: {pkg_name}
            Section: {section}
            Priority: optional
            Maintainer: Infra Test Bot <infra-test@example.com>
            Build-Depends: debhelper-compat (= 13)
            Standards-Version: 4.6.0

            Package: {pkg_name}
            Architecture: all
            Section: {section}
            Description: Minimal test package for Debusine infra testing
             This package exists solely to exercise the Debusine build pipeline.
            """),
        encoding="utf-8",
    )

    rules = (
        "#!/usr/bin/make -f\n"
        "%:\n"
        "\tdh $@\n"
        "\n"
        "override_dh_auto_build:\n"
        "\n"
        "override_dh_auto_test:\n"
        "\n"
        "override_dh_auto_install:\n"
        f"\tmkdir -p debian/{pkg_name}/usr/share/{pkg_name}\n"
        f"\techo test > debian/{pkg_name}/usr/share/{pkg_name}/marker\n"
    )
    rules_path = debian_dir / "rules"
    rules_path.write_text(rules, encoding="utf-8")
    rules_path.chmod(0o755)

    (source_dir / "format").write_text("3.0 (native)\n", encoding="utf-8")

    subprocess.run(
        ["dpkg-source", "-b", srcdir.name],
        cwd=str(build_dir),
        check=True,
    )

    dsc_files = list(build_dir.glob(f"{pkg_name}_*.dsc"))
    assert len(dsc_files) == 1, f"Expected one .dsc, found: {dsc_files}"
    return SourcePackageInfo(dsc_path=dsc_files[0], name=pkg_name, version=version)


def check_apt_unauthenticated(url: str) -> requests.Response:
    """GET url without authentication."""
    return requests.get(url, timeout=30)


def fetch_packages_xz(url_base: str, auth: requests.auth.HTTPBasicAuth | None = None) -> str:
    """Fetch Packages.xz and return the decompressed content as a string."""
    url = f"{url_base}/Packages.xz"
    resp = requests.get(url, auth=auth, timeout=30)
    assert resp.status_code == 200, (
        f"Expected 200 for Packages.xz at {url}, got {resp.status_code}"
    )
    return lzma.decompress(resp.content).decode("utf-8")


@retry(
    retry=retry_if_result(lambda r: r.status_code == 404),
    wait=wait_exponential(multiplier=1, min=5, max=60),
    stop=stop_after_delay(300),
    before_sleep=before_sleep_log(_log, logging.WARNING),
)
def check_apt_authenticated(url: str, user: str, token: str) -> requests.Response:
    """GET url with HTTP Basic authentication, retrying on 404."""
    return requests.get(url, auth=requests.auth.HTTPBasicAuth(user, token), timeout=30)


def head_url(url: str, auth: requests.auth.HTTPBasicAuth | None = None) -> requests.Response:
    """GET request used to check URL availability; HEAD returns 403 on some endpoints."""
    resp = requests.get(url, auth=auth, allow_redirects=True, timeout=30, stream=True)
    resp.close()
    return resp


def find_package_in_index(content: str, pkg_name: str):
    """
    Parse a plain-text Packages file and return the stanza for pkg_name.

    Returns a debian.deb822.Packages stanza (dict-like) or None.
    """
    for stanza in debian.deb822.Packages.iter_paragraphs(io.StringIO(content)):
        if stanza.get("Package") == pkg_name:
            return stanza
    return None


def verify_inrelease_signature(inrelease_bytes: bytes, signing_key_asc: str) -> None:
    """Assert that inrelease_bytes carries a valid signature from signing_key_asc."""
    with tempfile.TemporaryDirectory() as d:
        keyring = pathlib.Path(d) / "keyring.gpg"
        inrelease_file = pathlib.Path(d) / "InRelease"
        inrelease_file.write_bytes(inrelease_bytes)
        subprocess.run(
            ["gpg", "--no-default-keyring", "--keyring", str(keyring), "--import"],
            input=signing_key_asc.encode(),
            check=True,
            capture_output=True,
        )
        result = subprocess.run(
            ["gpgv", "--keyring", str(keyring), str(inrelease_file)],
            capture_output=True,
        )
        assert result.returncode == 0, (
            f"gpgv signature verification failed:\n{result.stderr.decode()}"
        )
