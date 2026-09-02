# Repository Configuration Specification

This document specifies the required configuration state of a production
`qualcomm-linux/pkg-*` GitHub repository for debusine-action workflows
to function correctly. It covers repository state only; tooling used to
achieve or verify that state is not in scope. See README.md for details
of that.

This specification is the source of truth for the tooling in this
directory. Any change to what the tools do to a repository must be
described here first, and the implementation then brought into sync with
it.

## Settings

### GitHub Actions Variables

The following repository-level Actions variables must be set:

| Variable         | Value                                                                          |
|------------------|--------------------------------------------------------------------------------|
| `DEBUSINE_HOST`  | `debusine.qualcomm.com` (production) or `stage.debusine.qualcomm.com` (stage)  |
| `DEBUSINE_SCOPE` | `qualcomm`                                                                     |

The following repository-level Actions variable must **not** be set:

- `DEBUSINE_PARENT_WORKSPACE`

The following repository-level Actions variable may be set temporarily to
suspend Debusine workflow execution without removing workflow files,
secrets, or environments:

| Variable                       | Value  | Effect                                      |
|--------------------------------|--------|---------------------------------------------|
| `DEBUSINE_WORKFLOWS_DISABLED`  | `true` | Skip Debusine CI, daily, and release runs   |

If `DEBUSINE_WORKFLOWS_DISABLED` is unset or has any value other than `true`,
Debusine workflows are enabled.

### GitHub Actions Secrets

The following repository-level Actions secrets must be set:

| Secret           | Purpose                           |
|------------------|-----------------------------------|
| `DEBUSINE_USER`  | Debusine user identity            |
| `DEBUSINE_TOKEN` | Debusine API authentication token |

### Organization Secret Visibility

The following organization-level Actions secrets are managed centrally
and must be visible to the repository — i.e. the secret's organization
visibility setting must be "All repositories", or "Selected
repositories" with this repository selected:

| Secret                     | Purpose                                                                          |
|----------------------------|-----------------------------------------------------------------------------------|
| `DEB_PKG_BOT_CI_QSC_TOKEN` | QArtifactory API key used for Ubuntu apt artifactory uploads during release      |
| `DEB_PKG_BOT_CI_TOKEN`     | Bot token used by qli-ci reusable workflows/scripts to clone internal repositories and perform authenticated write operations |

Granting visibility is an organization-level change that requires org
admin access; this tooling can only verify and report it, not grant it.

### Organization Variable Visibility

The following organization-level Actions variables are managed
centrally and must be visible to the repository with the exact values
below — i.e. the variable's organization visibility setting must be
"All repositories", or "Selected repositories" with this repository
selected:

| Variable                  | Required Value                    | Purpose                                                              |
|----------------------------|-----------------------------------|-----------------------------------------------------------------------|
| `DEB_PKG_BOT_CI_EMAIL`     | `githubservice@qti.qualcomm.com`  | Bot git commit/changelog author email used by qli-ci workflows       |
| `DEB_PKG_BOT_CI_NAME`      | `GitHub Service Bot`              | Bot git commit/changelog author name used by qli-ci workflows        |
| `DEB_PKG_BOT_CI_USERNAME`  | `qcom-service-bot`                | Bot GitHub username used by qli-ci workflows                         |

Granting visibility and setting these values is an organization-level
change that requires org admin access; this tooling can only verify and
report it, not apply it.

### GitHub Environment: Production

A GitHub Actions environment named `Production` must exist with the
following configuration:

#### Required Reviewers

The following users must all be configured as required reviewers
(keep this list sorted alphabetically):

- `basak-qcom`
- `gagath`
- `lool`
- `obbardc`
- `slyon`

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

The following users must all be configured as required reviewers
(keep this list sorted alphabetically):

- `abickett`
- `bjordiscollaku`
- `keerthi-go`

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
files that are in `pkg-workflows/debusine/` in the main branch
of the qualcomm-linux/qli-ci repository as follows:

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
