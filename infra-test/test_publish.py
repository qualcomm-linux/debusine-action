# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear

"""
Publish tests: validates that the Debusine package-publish workflow produces
a publicly accessible APT repository for each
(suite × component × target_workspace) combination.
"""

import pytest
import requests

from helpers import (
    check_apt_authenticated,
    check_apt_unauthenticated,
    fetch_packages_xz,
    find_package_in_index,
    verify_inrelease_signature,
)


@pytest.mark.publish
def test_release_workflow_succeeded(publish_result):
    wr = publish_result["final_wr"]
    assert wr.result == "success", (
        f"Publish workflow {publish_result['workflow_id']} finished with "
        f"result={wr.result!r} status={wr.status!r}"
    )


@pytest.mark.publish
def test_apt_target_public_inrelease(creds, publish_result):
    from debian.deb822 import Release

    suite = publish_result["suite"]
    component = publish_result["component"]
    url = f"{publish_result['apt_url_base']}/dists/{suite}/InRelease"
    resp = check_apt_unauthenticated(url)
    assert resp.status_code == 200, (
        f"Expected 200 (public) for InRelease at {url}, got {resp.status_code}"
    )
    _, payload, _ = Release.split_gpg_and_payload(resp.content.splitlines())
    release = Release(b"\n".join(payload).decode())
    components = release["Components"].split()
    assert component in components, (
        f"Component {component!r} not found in InRelease Components at {url}: {components}"
    )
    key_url = f"{publish_result['apt_url_base']}/signing-keys.asc"
    key_resp = check_apt_authenticated(key_url, creds["user"], creds["token"])
    assert key_resp.status_code == 200, (
        f"Expected 200 for signing-keys.asc at {key_url}, got {key_resp.status_code}"
    )
    verify_inrelease_signature(resp.content, key_resp.text)


@pytest.mark.publish
def test_apt_target_packages_contains_pkg(publish_result):
    suite = publish_result["suite"]
    component = publish_result["component"]
    url_base = f"{publish_result['apt_url_base']}/dists/{suite}/{component}/binary-all"
    content = fetch_packages_xz(url_base)
    stanza = find_package_in_index(content, publish_result["pkg_name"])
    assert stanza is not None, (
        f"Package {publish_result['pkg_name']!r} not found in {url_base}/Packages.xz"
    )


@pytest.mark.publish
def test_apt_target_deb_available(publish_result):
    suite = publish_result["suite"]
    component = publish_result["component"]
    url_base = f"{publish_result['apt_url_base']}/dists/{suite}/{component}/binary-all"
    content = fetch_packages_xz(url_base)

    stanza = find_package_in_index(content, publish_result["pkg_name"])
    assert stanza is not None, (
        f"Package {publish_result['pkg_name']!r} not found in Packages index at {url_base}/Packages.xz"
    )

    deb_url = f"{publish_result['apt_url_base']}/{stanza['Filename']}"
    # CDN returns 403 for HEAD; use streaming GET to avoid downloading the .deb
    resp = requests.get(deb_url, stream=True, timeout=30)
    resp.close()
    assert resp.status_code == 200, (
        f"Expected 200 for GET {deb_url}, got {resp.status_code}"
    )
