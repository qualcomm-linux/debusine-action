# Debusine Package Manager Action

A GitHub Actions composite action that automates uploading Debian source packages and triggering Debusine workflows.

---

## Overview

This action wraps three sub-actions into a single configurable step:

| Sub-action | Purpose |
|---|---|
| `setup` | Installs `debusine-client` and configures authentication |
| `import-artifact` | Uploads a `.dsc` source package to a Debusine workspace |
| `run-workflow` | Starts a named Debusine workflow with the uploaded artifact |

---

## Usage

```yaml
- name: Run Debusine Package Manager
  uses: ./.github/actions/debusine-action
  with:
    mode: 'upload+run'
    debusine_token: ${{ secrets.DEBUSINE_TOKEN }}
    artifact_path: 'path/to/package.dsc'
    workspace: 'developers'
    workflow_name: 'my-workflow'
    runtime_parameters: |
      codename: trixie
      lintian_backend: unshare
```

---

## Inputs

| Input | Required | Default | Description |
|---|---|---|---|
| `mode` | No | `upload+run` | Execution mode (see below) |
| `debusine_token` | **Yes** | — | Debusine API token |
| `artifact_path` | No | — | Path to the `.dsc` file |
| `workspace` | No | `developers` | Debusine workspace name |
| `workflow_name` | No | — | Workflow name to execute |
| `artifact_id` | No | `0` | Artifact ID (for `run_only` mode) |
| `runtime_parameters` | No | — | Runtime parameters as a YAML block |
| `debusine_server` | No | `dev.debian.qualcomm.com` | Debusine server URL |
| `debusine_scope` | No | `qualcomm` | Debusine API scope |

### Modes

| Mode | Runs Setup | Imports Artifact | Runs Workflow |
|---|:---:|:---:|:---:|
| `upload+run` | ✓ | ✓ | ✓ |
| `upload_only` | ✓ | ✓ | — |
| `run_only` | ✓ | — | ✓ |

---

## Outputs

| Output | Description |
|---|---|
| `artifact_id` | ID of the uploaded artifact |
| `workflow_id` | ID of the started workflow |
| `workflow_url` | Direct URL to the workflow on the Debusine server |

---

## Example Workflow

```yaml
jobs:
  build-and-test:
    runs-on: ubuntu-latest
    container:
      image: debian:trixie
      options: --user root
    steps:
      - uses: actions/checkout@main
        with:
          path: .github/actions/debusine-action

      - uses: ./.github/actions/debusine-action
        id: debusine
        with:
          mode: 'upload+run'
          debusine_token: ${{ secrets.DEBUSINE_TOKEN }}
          artifact_path: 'path/to/package.dsc'
          workspace: 'developers'
          workflow_name: 'test-sbuild-pipe'
          debusine_server: 'dev.debian.qualcomm.com'
          debusine_scope: 'qualcomm'
          runtime_parameters: |
            codename: trixie
            lintian_backend: unshare
            sbuild_backend: unshare

      - run: |
          echo "Artifact ID:  ${{ steps.debusine.outputs.artifact_id }}"
          echo "Workflow ID:  ${{ steps.debusine.outputs.workflow_id }}"
          echo "Workflow URL: ${{ steps.debusine.outputs.workflow_url }}"
```

---

## Secrets

Add the following secret to your repository under **Settings → Secrets and variables → Actions**:

| Secret | Description |
|---|---|
| `DEBUSINE_TOKEN` | Your Debusine API authentication token |

---

## Tests

Tests are located in `tests/` and are executed automatically as part of the `build-test.yml` workflow.

```
tests/
├── debusine-trigger-test.sh        # Test runner
└── test-cases/
    ├── setup_tests.json            # Verifies installation and config
    ├── import_artifact_tests.json  # Verifies .dsc upload and artifact ID
    └── run_workflow_tests.json     # Verifies workflow start and outputs
```