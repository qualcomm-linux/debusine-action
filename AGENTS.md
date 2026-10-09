# debusine-action — Agent Guidelines

## Purpose

`debusine-action` publishes the Debusine builder images used by Qualcomm Linux
package CI.

This repo is responsible for:

1. The Debusine builder images published from `Dockerfiles/debusine-builder/`

The reusable Debusine CI workflow (`.github/workflows/debusine.yml`) and its
helper scripts (`lib/`) have moved, with history, to `qualcomm-linux/qli-ci`.
See `qli-ci/AGENTS.md` for their architecture, contracts, and design
decisions. The repo configuration tools and Debusine workflow stubs also live
in `qli-ci` (`tools/repo-management/` and `pkg-workflows/debusine/`).

## Scope Boundary

For current Qualcomm Linux package CI/release behavior, treat these as active:

- `Dockerfiles/debusine-builder/*`
- `.github/workflows/debusine-container-build-and-upload.yml`

Top-level composite action files (`action.yml`, `setup/`, `import-artifact/`,
`run-workflow/`) still exist, but they are not the primary source of truth for
the current `pkg-*` Debusine workflow model.

## Builder Images

- Images are published as `ghcr.io/qualcomm-linux/debusine-pkg-builder:<suite>`.
- `qli-ci`'s `debusine.yml` runs source-package generation in the
  suite-matched image and Debusine client / build orchestration / release
  steps in the `trixie` image. `qli-ci`'s `pkg-build` and `pkg-release`
  reusable workflows use the same images for the Debian path.

## When Editing This Repo

1. **Adding/removing supported builder suites**: Update the
   `.github/workflows/debusine-container-build-and-upload.yml` image matrix,
   and keep it consistent with the suite map in `qli-ci`'s
   `.github/workflows/debusine.yml`.

2. **Changing builder-image contents**: Ensure the image publication workflow
   path is updated and rebuild relevant GHCR images before concluding.

## Validation Expectations

For builder-image changes:

1. rebuild and publish the affected images
2. validate at least one downstream default-branch path:
   - `Debusine Daily` or `Debusine PR Check`
3. distinguish image/tooling failures from repo-specific package/test failures

## Important Files

- `.github/workflows/debusine-container-build-and-upload.yml`
- `Dockerfiles/debusine-builder/Dockerfile`
- `Dockerfiles/debusine-builder/base-packages.txt`
