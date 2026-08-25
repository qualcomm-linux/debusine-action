# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear

"""
Build pipeline tests: exercises the Debusine build flow for each
(suite × component) combination and validates the resulting APT repository.
"""

import pytest
import requests.auth

from helpers import (
    check_apt_authenticated,
    check_apt_unauthenticated,
    fetch_packages_xz,
    find_package_in_index,
    head_url,
    verify_inrelease_signature,
)


@pytest.mark.build
def test_artifact_imported(build_result):
    assert isinstance(build_result["artifact_id"], int)
    assert build_result["artifact_id"] > 0


@pytest.mark.build
def test_build_workflow_succeeded(build_result):
    wr = build_result["final_wr"]
    assert wr.result == "success", (
        f"Build workflow {build_result['workflow_id']} finished with "
        f"result={wr.result!r} status={wr.status!r}"
    )


@pytest.mark.build
def test_apt_child_requires_auth(creds, build_result):
    suite = build_result["suite"]
    url = f"{build_result['apt_url_base']}/dists/{suite}/InRelease"
    resp = check_apt_unauthenticated(url)
    assert resp.status_code in (401, 403, 404), (
        f"Expected 401/403/404 without auth for child workspace, got {resp.status_code}"
    )


@pytest.mark.build
def test_apt_child_inrelease(creds, build_result):
    suite = build_result["suite"]
    component = build_result["component"]
    url = f"{build_result['apt_url_base']}/dists/{suite}/InRelease"
    resp = check_apt_authenticated(url, creds["user"], creds["token"])
    assert resp.status_code == 200, (
        f"Expected 200 for InRelease with auth, got {resp.status_code}"
    )
    assert component in resp.text, (
        f"Component {component!r} not found in InRelease"
    )
    key_url = f"{build_result['apt_url_base']}/signing-keys.asc"
    key_resp = check_apt_authenticated(key_url, creds["user"], creds["token"])
    assert key_resp.status_code == 200, (
        f"Expected 200 for signing-keys.asc at {key_url}, got {key_resp.status_code}"
    )
    verify_inrelease_signature(resp.content, key_resp.text)


@pytest.mark.build
def test_apt_child_packages_contains_pkg(creds, build_result):
    suite = build_result["suite"]
    component = build_result["component"]
    url_base = f"{build_result['apt_url_base']}/dists/{suite}/{component}/binary-all"
    auth = requests.auth.HTTPBasicAuth(creds["user"], creds["token"])
    content = fetch_packages_xz(url_base, auth=auth)
    stanza = find_package_in_index(content, build_result["pkg_name"])
    assert stanza is not None, (
        f"Package {build_result['pkg_name']!r} not found in {url_base}/Packages.xz"
    )


@pytest.mark.build
def test_apt_child_deb_available(creds, build_result):
    suite = build_result["suite"]
    component = build_result["component"]
    url_base = f"{build_result['apt_url_base']}/dists/{suite}/{component}/binary-all"
    auth = requests.auth.HTTPBasicAuth(creds["user"], creds["token"])
    content = fetch_packages_xz(url_base, auth=auth)

    stanza = find_package_in_index(content, build_result["pkg_name"])
    assert stanza is not None, (
        f"Package {build_result['pkg_name']!r} not found in Packages index"
    )

    deb_url = f"{build_result['apt_url_base']}/{stanza['Filename']}"
    head = head_url(deb_url, auth=auth)
    assert head.status_code in (200, 206), (
        f"Expected 200/206 for HEAD {deb_url}, got {head.status_code}"
    )
