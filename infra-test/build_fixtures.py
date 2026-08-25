# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear

"""
Session-scoped fixture that runs the build pipeline once per
(suite, component) combination and shares the result across all tests.
"""

import logging
import pathlib
import tempfile
import time

import pytest

from debusine.artifacts.models import CollectionCategory
from debusine.client.client_utils import prepare_dsc_for_upload
from debusine.client.models import (
    CreateWorkflowRequest,
    WorkflowTemplateDataNew,
    CollectionDataNew,
)

from helpers import create_minimal_source_package, make_client, poll_work_request


@pytest.fixture(scope="session")
def build_result(creds, suite, component):
    """
    Run the full Debusine build pipeline for one (suite, component) pair.

    Session-scoped: pytest runs this once per (suite, component) combination
    and reuses the result for every test that requests it.
    """
    host = creds["host"]
    scope = creds["scope"]
    token = creds["token"]
    parent_workspace = creds["parent_workspace"]

    logger = logging.getLogger(f"debusine.infra_test.build.{suite}.{component}")
    client = make_client(host, token, scope, logger)

    abbrev = {"main": "m", "contrib": "c", "non-free": "nf", "non-free-firmware": "nff"}[component]
    ts = int(time.time())
    child_suffix = f"infra-test-{suite}-{abbrev}-{ts}"
    workspace = f"{parent_workspace}-{child_suffix}"

    build_dir = pathlib.Path(tempfile.mkdtemp(prefix="debusine-infra-test-"))
    srcpkg = create_minimal_source_package(build_dir, component)

    # 1. Create child workspace
    logger.info("Creating child workspace %s", workspace)
    wr = client.workflow_create(CreateWorkflowRequest(
        template_name="create-child-workspace",
        workspace=parent_workspace,
        task_data={"suffix": child_suffix},
    ))
    final = poll_work_request(client, wr.id, logger)
    assert final.result == "success", (
        f"create-child-workspace failed: result={final.result} status={final.status}"
    )

    # 2. Create archive suite with all four components in one collection
    logger.info("Creating archive suite %s in %s", suite, workspace)
    client.collection_create(
        workspace,
        CollectionDataNew(
            name=suite,
            category=CollectionCategory.SUITE,
            data={
                "components": ["main", "contrib", "non-free", "non-free-firmware"],
                "architectures": ["all", "amd64", "arm64"],
            },
        ),
    )

    # 3. Create debian_pipeline workflow template
    logger.info("Creating workflow template in %s", workspace)
    client.workflow_template_create(
        workspace,
        WorkflowTemplateDataNew(
            name="debian_pipeline",
            task_name="debian_pipeline",
            static_parameters={
                "vendor": "debian",
                "sbuild_environment_variant": "buildd",
                "enable_autopkgtest": False,
                "enable_lintian": False,
                "enable_piuparts": False,
                "enable_blhc": False,
                "codename": suite,
                "suite": f"{suite}@{CollectionCategory.SUITE}",
            },
            runtime_parameters={"source_artifact": "any"},
        ),
    )

    # 4. Import source package
    logger.info("Importing source package %s %s", srcpkg.name, srcpkg.version)
    local_artifact = prepare_dsc_for_upload(srcpkg.dsc_path)
    remote = client.upload_artifact(local_artifact, workspace=workspace)
    artifact_id = remote.id
    logger.info("Imported artifact id=%d", artifact_id)

    # 5. Start build workflow
    logger.info("Starting debian_pipeline workflow for artifact %d", artifact_id)
    wr = client.workflow_create(CreateWorkflowRequest(
        template_name="debian_pipeline",
        workspace=workspace,
        task_data={"source_artifact": f"{artifact_id}@artifacts"},
    ))
    workflow_id = wr.id
    logger.info(
        "Build workflow started: id=%d  URL: https://%s/%s/%s/work-request/%d/",
        workflow_id, host, scope, workspace, workflow_id,
    )

    # 6. Poll until complete
    final_wr = poll_work_request(client, workflow_id, logger)
    logger.info("Build workflow %d finished: result=%s", workflow_id, final_wr.result)

    return {
        "workspace": workspace,
        "artifact_id": artifact_id,
        "workflow_id": workflow_id,
        "final_wr": final_wr,
        "pkg_name": srcpkg.name,
        "pkg_version": srcpkg.version,
        "suite": suite,
        "component": component,
        "apt_url_base": f"https://deb.{host}/{scope}/{workspace}",
        "client": client,
    }
