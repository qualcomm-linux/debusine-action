# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear

"""
Session-scoped fixture that runs the publish pipeline once per
(suite, component, target_workspace) combination and shares the result
across all tests.
"""

import logging

import pytest

from debusine.artifacts.models import CollectionCategory
from debusine.client.models import CreateWorkflowRequest

from helpers import make_client, poll_work_request


@pytest.fixture(scope="session")
def publish_result(creds, release_token, build_result, target_workspace):
    """
    Run the package-publish workflow for one (suite, component, target_workspace).

    Session-scoped: pytest runs this once per (suite, component, target_workspace)
    combination and reuses the result for every test that requests it.
    """
    host = creds["host"]
    scope = creds["scope"]

    suite = build_result["suite"]
    component = build_result["component"]

    logger = logging.getLogger(
        f"debusine.infra_test.publish.{suite}.{component}.{target_workspace}"
    )
    release_client = make_client(host, release_token, scope, logger)

    suite_collection = next(
        (
            c for c in build_result["client"].collection_iter(build_result["workspace"])
            if c.category == CollectionCategory.SUITE and c.name == suite
        ),
        None,
    )
    assert suite_collection is not None, (
        f"Suite collection {suite!r} not found in workspace {build_result['workspace']!r}"
    )

    pkg_name = build_result["pkg_name"]
    pkg_version = build_result["pkg_version"]

    logger.info(
        "Starting package-publish to %s (suite collection id=%d)",
        target_workspace, suite_collection.id,
    )
    wr = release_client.workflow_create(CreateWorkflowRequest(
        template_name="package-publish",
        workspace=target_workspace,
        task_data={
            "source_artifact": (
                f"{suite_collection.id}@collections/{pkg_name}_{pkg_version}"
            ),
            "binary_artifacts": {
                "category": "debian:binary-package",
                "collection": f"{suite_collection.id}@collections",
            },
            "target_suite": f"{suite}@{CollectionCategory.SUITE}",
            "unembargo": True,
        },
    ))

    logger.info("Publish workflow started: id=%d", wr.id)
    final_wr = poll_work_request(release_client, wr.id, logger)
    logger.info("Publish workflow %d finished: result=%s", wr.id, final_wr.result)

    return {
        "final_wr": final_wr,
        "workflow_id": wr.id,
        "target_workspace": target_workspace,
        "suite": suite,
        "component": component,
        "pkg_name": pkg_name,
        "pkg_version": pkg_version,
        "apt_url_base": f"https://deb.{host}/{scope}/{target_workspace}",
    }
