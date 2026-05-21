# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear

"""Rewrite debusine-action branch references in packaging workflow YAML files."""

# This is a hack that modifies the stub workflow files to use a branch of
# debusine-action to supply the reusable workflow to allow for development and
# debugging of changes to the reusable workflow in a branch without having to
# land the changes in the main branch first. For this to work, it has to have
# some knowledge of the structure of the workflow stubs, which is the necessary
# hack. It is only used in the development/debug case and deliberately excluded
# from the production code path. The `modify_workflow_files()` entry point is
# invoked via `./update-workflow-files --debug-source-branch=...`.

import itertools
from pathlib import Path

import ruamel.yaml

DEBUSINE_USES_PREFIX = "qualcomm-linux/debusine-action/.github/workflows/debusine.yml@"
DEBUSINE_USES_MAIN = DEBUSINE_USES_PREFIX + "main"


def modify_workflow_files(directory: Path, branch: str) -> None:
    """Rewrite @main references to @branch in all .yml files in directory."""
    yaml = ruamel.yaml.YAML()
    yaml.preserve_quotes = True

    for path in itertools.chain(directory.glob("*.yml"), directory.glob("*.yaml")):
        doc = yaml.load(path)
        if not isinstance(doc, dict):
            continue
        jobs = doc.get("jobs")
        if not isinstance(jobs, dict):
            continue
        modified = False
        for job in jobs.values():
            if not isinstance(job, dict):
                continue
            uses = job.get("uses", "")
            if isinstance(uses, str) and uses.startswith(DEBUSINE_USES_PREFIX):
                if uses != DEBUSINE_USES_MAIN:
                    raise ValueError(
                        f"{path}: unexpected ref in uses: {uses!r} (expected @main)"
                    )
                with_block = job.get("with")
                if not isinstance(with_block, dict) or with_block.get("debusine-action-ref") != "main":
                    raise ValueError(
                        f"{path}: debusine-action-ref must be 'main' when uses is {DEBUSINE_USES_MAIN!r}"
                    )
                job["uses"] = DEBUSINE_USES_PREFIX + branch
                with_block["debusine-action-ref"] = branch
                modified = True
        if modified:
            with path.open("w") as f:
                yaml.dump(doc, f)
