# Repository Configuration Tools

This directory contains tools for configuring GitHub repositories to
work with the debusine-action reusable workflows.

## Specification

[`SPECIFICATION.md`](SPECIFICATION.md) describes the required
configuration state of a production `qualcomm-linux/pkg-*` repository —
settings, secrets, environments, and workflow file contents. It covers
repository state only; this README documents the tooling used to achieve
and verify that state.

## Prerequisites

- `gh` CLI tool must be installed and authenticated (`gh auth login`)
- Appropriate permissions on the target repository

## Tools

### enable-repo

Convenience wrapper that runs `configure-repo`, `set-repo-secrets`, and
`update-workflow-files` in sequence to fully enable a new repository.

**Usage:**
```bash
./enable-repo <repo-name>
```

**Arguments:**
- `repo-name`: Repository name with `pkg-` prefix (e.g., `pkg-fastrpc`
  expands to `qualcomm-linux/pkg-fastrpc`)

**Example:**
```bash
./enable-repo pkg-fastrpc
```

See the individual tool sections below for details on what each step
does and the options available when running them separately.

### configure-repo

Configures a GitHub repository with the required settings for
debusine-action workflows.

**Usage:**
```bash
./configure-repo [--check] [--production | --stage] <repo-name>
```

**Arguments:**
- `repo-name`: Repository name with pkg- prefix (e.g., `pkg-fastrpc`
  expands to `qualcomm-linux/pkg-fastrpc`)

**Options:**
- `--check`: Only report what needs changing without making changes
- `--force`: Proceed even if prerequisite checks fail (public visibility
  and `is-pkg-repo` property)
- `--production`: Set `DEBUSINE_HOST` to `debusine.qualcomm.com`
  (default)
- `--stage`: Set `DEBUSINE_HOST` to `stage.debusine.qualcomm.com`

**What it configures:**

Settings defined in SPECIFICATION.md apart from secrets.

**Examples:**
```bash
# Check what needs to be configured
./configure-repo --check pkg-fastrpc

# Apply configuration
./configure-repo pkg-fastrpc
```

### set-repo-secrets

Sets the required secrets for a GitHub repository used by
debusine-action workflows.

**Usage:**
```bash
./set-repo-secrets <repo-name>
```

**Arguments:**
- `repo-name`: Repository name with pkg- prefix (e.g., `pkg-fastrpc`
  expands to `qualcomm-linux/pkg-fastrpc`)

**What it sets:**

Secrets defined in SPECIFICATION.md.

The tool will prompt for four secrets:

1. **DEBUSINE_USER** (repository-level): Debusine user (defaults to
   `DebusineGitHubCI@qualcomm.com` if left blank)
2. **DEBUSINE_TOKEN** (repository-level): Debusine API authentication
   token
3. **DEBUSINE_RELEASE_TOKEN** (Production environment): Token for
   release operations
4. **DEBUSINE_RELEASE_TOKEN** (Staging environment): Token for release
   operations

**Note:** Run `configure-repo` first to ensure the Production
environment exists.

**Limitation:** The GitHub API does not expose secret values, so
`set-repo-secrets` has no `--check` mode. There is no way to verify that
secrets are already set or have the correct values without overwriting
them.

**Example:**
```bash
./set-repo-secrets pkg-fastrpc
```

The tool will interactively prompt for each secret value.

### update-workflow-files

Ensures that workflow files in each relevant branch of a `pkg-*`
repository match the current state of `packaging-workflows/` in a branch
of `qualcomm-linux/debusine-action` (default: `main`). Clones both
repositories into a temporary directory, compares files branch by
branch, and pushes changes directly to each branch that needs updating.

**Usage:**
```bash
./update-workflow-files [--check | --pr | --direct] [--no-clean] [--debug-source-branch <branch>] <repo-name> [branch ...]
```

**Arguments:**
- `repo-name`: Repository name with `pkg-` prefix (e.g., `pkg-fastrpc`
  expands to `qualcomm-linux/pkg-fastrpc`)
- `branch ...`: Optional list of branches to process. When specified,
  only those branches are processed and auto-detection of packaging
  branches is skipped. By default, processes `qli-ci` plus any packaging
  branches present in the repository.

**Options:**
- `--check`: Report what needs changing; commits are made locally but
  not pushed and no PRs are created/modified
- `--pr`: Push changes to a `chore/pkg-management-update/<branch>`
  branch and file a pull request, or comment on an existing PR if one is
  already open. Mutually exclusive with `--check`
- `--direct`: Deprecated. Direct push is now the default behaviour; this
  option is accepted for backwards compatibility but will be removed in
  a future release
- `--no-clean`: Leave the temporary directory on exit and print its path
  (useful with `--check` to inspect the commit that would be pushed)
- `--debug-source-branch <branch>`: Branch of
  `qualcomm-linux/debusine-action` to use as the source (default:
  `main`). Rewrites `@main` references in workflow files to `@<branch>`
  before deploying. Cannot be used when processing production-managed
  branches of a `pkg-*` repository.

**What it does:**

By default, pushes changes directly to each target branch that needs
updating.  With `--pr`, changes are instead routed through a
`chore/pkg-management-update/<branch>` branch and a pull request is
created or updated.

#### Branch Selection

By default, `update-workflow-files` processes `qli-ci` plus any
packaging branches that exist in the target repository. Optionally, one
or more branch names may be provided as additional positional arguments
to restrict processing to exactly those branches (e.g.
`./update-workflow-files pkg-foo qcom/debian/latest
qcom/debian/trixie`). When branches are specified explicitly, the
`qli-ci` existence check and auto-detection of packaging branches are
skipped.

#### Direct Push Mode

By default, `update-workflow-files` pushes changes directly to the
target branch.  The `chore/pkg-management-update/<branch>` branch and
any existing pull requests for that branch are ignored entirely.
`--direct` is accepted as a deprecated alias for the default behaviour;
using it prints a deprecation warning.

#### Pull Request Mode

When invoked with `--pr`, `update-workflow-files` pushes changes to a
`chore/pkg-management-update/<branch>` branch and creates or updates a
pull request targeting the original branch instead of pushing directly.
If a pull request is already open, a comment is added noting that the
branch has been updated. `--pr` is mutually exclusive with `--check`.

#### Non-default Source Branch (Debug)

When `update-workflow-files` is invoked with `--debug-source-branch
<branch>` where `<branch>` differs from the default (`main`), the
sourced workflow files are modified before being deployed or compared:

- Every `uses:
  qualcomm-linux/debusine-action/.github/workflows/debusine.yml@main`
  value is rewritten to `@<branch>`.
- The corresponding `with.debusine-action-ref: main` value is rewritten
  to `<branch>`.

This allows workflow files from a feature branch of debusine-action to
be tested against the same feature branch at runtime. This modification
is not applied in normal operation.

Using `--debug-source-branch` on a `pkg-*` repository is an error if any
branch being processed is in the default managed set — that is, if it
intersects with `qli-ci` plus any packaging branches that exist in the
repository. This prevents accidentally deploying debug branch references
to production-managed branches. The check passes only when all branches
to process are outside that default set (e.g. a dedicated test branch),
whether they were specified explicitly or derived from defaults.

**Examples:**
```bash
# Check what needs updating
./update-workflow-files --check pkg-fastrpc

# Check and inspect the temporary directory
./update-workflow-files --check --no-clean pkg-fastrpc

# Apply updates directly (default)
./update-workflow-files pkg-fastrpc

# Apply updates via pull request
./update-workflow-files --pr pkg-fastrpc

# Test against a feature branch before it merges to main
./update-workflow-files --debug-source-branch my-feature-branch --check pkg-fastrpc
```

## Workflow

To fully enable a new repository in one step:

```bash
./enable-repo pkg-fastrpc
```

Or run the steps individually:

1. Check current configuration:
   ```bash
   ./configure-repo --check pkg-fastrpc
   ```

2. Apply configuration:
   ```bash
   ./configure-repo pkg-fastrpc
   ```

3. Set secrets:
   ```bash
   ./set-repo-secrets pkg-fastrpc
   ```

4. Deploy workflow files:
   ```bash
   ./update-workflow-files pkg-fastrpc
   ```

## Troubleshooting

**"gh is not authenticated"**
- Run `gh auth login` and follow the prompts

**"Failed to set environment secret"**
- Ensure the Production environment exists by running `configure-repo`
  first

**Protection rule configuration issues**
- Some protection rule settings may need to be verified or adjusted
  manually via the GitHub web UI
- Navigate to: Repository Settings → Environments → Production →
  Protection rules
