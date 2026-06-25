# debusine-action — Agent Guidelines

## Purpose

`debusine-action` owns the Debusine-specific packaging logic used by Qualcomm Linux
repositories.

This repo is responsible for:

1. The reusable Debusine CI workflow in `.github/workflows/debusine.yml`
2. The helper scripts under `lib/`
3. The Debusine builder images published from `Dockerfiles/debusine-builder/`
4. The reference `packaging-workflows/` files that downstream `pkg-*` repos copy

`qcom-build-utils` orchestrates package-repo behavior around this repo, but
`debusine-action` is the source of truth for Debusine helper behavior and image
publication.

## Scope Boundary

For current Qualcomm Linux package CI/release behavior, treat these as active:

- `.github/workflows/debusine.yml`
- `lib/*` helper scripts called by that reusable workflow
- `Dockerfiles/debusine-builder/*`
- `packaging-workflows/*` and `packaging-workflows/README*.md`

Top-level composite action files (`action.yml`, `setup/`, `import-artifact/`,
`run-workflow/`) still exist, but they are not the primary source of truth for
the current `pkg-*` Debusine workflow model.

## Current Workflow Architecture

- `.github/workflows/debusine.yml` is the main reusable packaging workflow.
- The workflow is split into:
  - `resolve`
  - `source-package`
  - `build`
  - `release`
- Source-package generation runs in the suite-matched builder image:
  - `ghcr.io/qualcomm-linux/debusine-pkg-builder:<suite>`
- Debusine client / build orchestration / release steps run in the `trixie`
  builder image.
- Source package artifacts are staged via a named `source-package/` directory
  artifact and restored in the build job before calling `lib/build`.
- Branch-to-suite resolution is explicit in `resolve`:
  - `qli/debian/latest`, `qli-staging/debian/latest`, or `qcom/debian/latest` (transitional) -> `forky`
  - `qli/debian/trixie`, `qli-staging/debian/trixie`, or `qcom/debian/trixie` (transitional) -> `trixie`
- Branch prefix also determines the package version string identifier:
  - `qli/` or `qcom/` (transitional) -> `qli`
  - `qli-staging/` -> `qli+staging`

## Important Active Contracts

### Reusable workflow inputs

`debusine.yml` now expects these important caller inputs:

- `target_branch`
- `source_ref`
- `release`
- `debusine-action-ref`
- `debusine-parent-workspace`
- `job_index`

### Required reusable-workflow secrets

`debusine.yml` currently requires callers to pass:

- `DEBUSINE_USER`
- `DEBUSINE_TOKEN`
- `DEBUSINE_RELEASE_TOKEN`

### Explicit ref selection

Do **not** reintroduce workflow-SHA lookup from the job OIDC token.

The current design is intentional:

- callers pass `debusine-action-ref` explicitly
- internal `actions/checkout` steps use that explicit ref
- packaging-workflow callers pass the helper ref they want

This replaced an earlier OIDC-claim-based `job_workflow_sha` mechanism and was
done in response to review feedback about depending on undocumented token
claims.

### Parent workspace

The Debusine parent workspace is intentionally configurable through
`debusine-parent-workspace`, defaulting to `qli-ci`.

Preserve this pass-through unless a documented and approved design change is implemented.

## Packaging Workflow Layout

The `packaging-workflows/` directory contains reference workflow files that are
copied into downstream package repositories.

Current intended placement:

- default branch:
  - `debusine-daily.yml`
  - `debusine-pr-check.yml`
- packaging branches (`qli/debian/*` or `qli-staging/debian/*`; `qcom/debian/*` also continues to be accepted for backwards compatibility during the transition):
  - `debusine-pr-hook.yml`
  - `debusine-release.yml`

Also follow:

- `packaging-workflows/README.md`
- `packaging-workflows/README.debusine.md`

`README.debusine.md` should be copied into `.github/workflows/` in downstream
branches alongside the workflow files.

## Important UX / Behavior Decisions

### Release workflow UI

Keep `packaging-workflows/debusine-release.yml` branch-local.

That means:

- it belongs on packaging branches
- it derives the release target from `github.ref_name`
- it does **not** ask for a separate `target-branch` input

This was an explicit review-driven decision to avoid a confusing “pick a branch
and then type a branch again” release UI.

### Source package handling

Preserve the current source-package flow:

- generate the source package from the checked-out packaging tree
- stage files from the generated `.changes`
- upload them as the `source-package` artifact
- restore them into the build workspace root before Debusine import/build

This fixed earlier missing-orig-tarball and path-restoration issues.

## Downstream Sync Model

- Changes to `packaging-workflows/*` must also be copied into managed `pkg-*`
  repositories.
- Changes to `packaging-workflows/README*.md` should be copied too.
- That sync is currently manual.
- The source files in this repo should keep their stable merge target refs.

Important convention:

- in `debusine-action`, the reference packaging workflows should point to
  `@main`
- for validation before merge, temporary downstream copies may point to
  `@dev/sbeaudoi`

Do not leave validation-only branch refs in the source files that are intended
to merge to `main`.

## Do Not Reintroduce

- OIDC-token parsing to derive `job_workflow_sha`
- extra `id-token: write` permissions in packaging-workflow callers solely for
  workflow-ref resolution
- default-branch `debusine-release.yml` with a separate `target-branch` input
- ad hoc source-package file moves that bypass the current staged artifact flow
- branch/suite drift between:
  - `.github/workflows/debusine.yml` (`resolve` suite map)
  - `packaging-workflows/debusine-daily.yml` (`check-branches` candidates list)

## When Editing This Repo

1. **Changing `lib/` helper behavior**: Check all workflow call sites in
   `.github/workflows/debusine.yml`.

2. **Changing reusable workflow contracts**: Update all of:
   - `packaging-workflows/*`
   - `packaging-workflows/README.md`
   - `packaging-workflows/README.debusine.md`
   - Downstream validation copies in managed `pkg-*` repos when needed

3. **Adding/removing supported Debian packaging branches or suites**: Update both:
   - `.github/workflows/debusine.yml` branch-to-suite map
   - `packaging-workflows/debusine-daily.yml` branch candidates

4. **Adding/removing supported builder suites**: Also update
   `.github/workflows/debusine-container-build-and-upload.yml` image matrix.

5. **Changing builder-image contents**: Ensure the image publication workflow
   path is updated and rebuild relevant GHCR images before concluding.

## Validation Expectations

For changes to active packaging behavior:

1. validate `debusine-action` workflows directly when possible
2. validate at least one downstream default-branch path:
   - `Debusine Daily` or `Debusine PR Check`
3. validate the branch-local release path separately when release behavior
   changes
4. distinguish workflow wiring failures from repo-specific package/test failures

Known pattern:

- a downstream run reaching build/test and then failing on missing packages,
  invalid upstream tags, or package-specific dependency problems is usually not
  a `debusine-action` wiring failure by itself

## Important Files

- `.github/workflows/debusine.yml`
- `.github/workflows/debusine-container-build-and-upload.yml`
- `packaging-workflows/README.md`
- `packaging-workflows/README.debusine.md`
- `packaging-workflows/debusine-daily.yml`
- `packaging-workflows/debusine-pr-check.yml`
- `packaging-workflows/debusine-pr-hook.yml`
- `packaging-workflows/debusine-release.yml`
- `Dockerfiles/debusine-builder/Dockerfile`
- `Dockerfiles/debusine-builder/base-packages.txt`
- `lib/build`
- `lib/generate-source-package`
- `lib/generate-step-summary`
- `lib/prepare-release`
- `lib/release`
- `lib/push-release`
