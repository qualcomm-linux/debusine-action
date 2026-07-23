# Repository Configuration Specification

This document specifies the required configuration state of a production
`qualcomm-linux/pkg-*` GitHub repository for debusine-action workflows
to function correctly. It covers repository state only; tooling used to
achieve or verify that state is not in scope. See README.md for details
of that.

## Settings

### GitHub Actions Variables

The following repository-level Actions variables must be set:

| Variable         | Value                                                                          |
|------------------|--------------------------------------------------------------------------------|
| `DEBUSINE_HOST`  | `debusine.qualcomm.com` (production) or `stage.debusine.qualcomm.com` (stage)  |
| `DEBUSINE_SCOPE` | `qualcomm`                                                                     |

The following repository-level Actions variable must **not** be set:

- `DEBUSINE_PARENT_WORKSPACE`

### GitHub Actions Secrets

The following repository-level Actions secrets must be set:

| Secret           | Purpose                           |
|------------------|-----------------------------------|
| `DEBUSINE_USER`  | Debusine user identity            |
| `DEBUSINE_TOKEN` | Debusine API authentication token |

### GitHub Environment: Production

A GitHub Actions environment named `Production` must exist with the
following configuration:

#### Required Reviewers

The following users must all be configured as required reviewers:

- `basak-qcom`
- `gagath`
- `lool`

#### Administrator Bypass

"Allow administrators to bypass configured protection rules" must be
disabled.

#### Environment Secret

The following secret must be set in the `Production` environment:

| Secret                   | Purpose                           |
|--------------------------|-----------------------------------|
| `DEBUSINE_RELEASE_TOKEN` | Debusine release operations token |

### GitHub Environment: Ubuntu Production

A GitHub Actions environment named `Ubuntu Production` must exist with
the following configuration. This environment is being introduced ahead
of Ubuntu-specific release workflow changes, in order to align Ubuntu
release approval with the existing Debian `Production` environment
model.

#### Required Reviewers

The following users must all be configured as required reviewers:

- `keerthi-go`
- `abickett`
- `bjordiscollaku`

#### Administrator Bypass

"Allow administrators to bypass configured protection rules" must be
disabled.

#### Environment Secret

No environment secret is required in `Ubuntu Production` at this time.

### GitHub Environment: Staging

A GitHub Actions environment named `Staging` must exist with no
protection rules.

#### Environment Secret

The following secret must be set in the `Staging` environment:

| Secret                   | Purpose                           |
|--------------------------|-----------------------------------|
| `DEBUSINE_RELEASE_TOKEN` | Debusine release operations token |

## Workflow Files

Workflow files must be present and be duplicates of the corresponding
files that are in `packaging-workflows/` in the main branch of the
qualcomm-linux/debusine-action repository as follows:

### Default Branch

The default branch must be named `qli-ci` and contain the following in
`.github/workflows/`:

| File                    |
|-------------------------|
| `debusine-daily.yml`    |
| `debusine-pr-check.yml` |
| `debusine-pr-hook.yml`  |
| `debusine-release.yml`  |
| `README.debusine.md`    |

### Each Packaging Branch

The following packaging branches are managed. They do not need to exist,
but if they do, they must contain the following in `.github/workflows/`:

- `qcom/debian/trixie`
- `qcom/debian/latest`
- `qli/debian/trixie`
- `qli/debian/latest`
- `qli-staging/debian/trixie`
- `qli-staging/debian/latest`

| File                    |
|-------------------------|
| `debusine-pr-hook.yml`  |
| `debusine-release.yml`  |
| `README.debusine.md`    |

No other packaging branches are managed.
