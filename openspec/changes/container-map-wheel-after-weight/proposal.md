# Proposal

## Why

Commit `c1aa25f6` reordered the `Containerfile` builder stage so the removal
weight is fetched before the locked local map package's wheel is installed, and
made that post-fetch sync refresh the wheel. The `container-image` capability
still states the old ordering: model acquisition "SHALL follow locked dependency
installation and precede application-source copying". That sentence is now
inexact for the one locked package that installs after acquisition, and the
wheel-freshness invariant the ordering exists to protect has no requirement at
all, so traceability cannot claim it.

## What Changes

- MODIFIED requirement `Multi-stage Containerfile` in `container-image` (title
  unchanged, so the canonical ID
  `container-image::multi-stage-containerfile` stays valid): the body names
  locked third-party dependency installation as acquisition's predecessor and
  requires the locked local `elosern-map-core` wheel to install from
  `packages/map-core/` after acquisition and to be rebuilt, never reused as a
  cached wheel.
- Two new scenarios in that requirement: a map-package source edit reuses the
  layer holding the acquired weight and rebuilds exactly that one package; a
  rebuilt image carries the current package code. Every existing scenario in the
  requirement is retained verbatim.
- Traceability: annotate
  `tests/test_container_contract.py::ContainerContractTests.test_the_map_package_wheel_is_rebuilt_after_the_weight_is_acquired`
  with `covers_requirement("container-image::multi-stage-containerfile")`.

No executable behavior changes. `Containerfile`, `tests/`, the image, and the
measured build timings are already committed and verified; this change only
aligns the normative text and closes the annotation gap.

Non-goals: editing `Containerfile` or `tests/`, rebuilding containers, creating
branches or worktrees, archiving, syncing main specs, and any other capability,
gameplay requirement, or docs page.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `container-image`: the `Multi-stage Containerfile` requirement text and its
  scenarios only.

## Impact

- Specs: `openspec/specs/container-image/spec.md` through this change's delta.
- Tests: one `covers_requirement` decorator line in
  `tests/test_container_contract.py`; no assertion changes.
- Code, dependencies, image: none.
- Human-reviewed: nothing in this change. The two new scenarios are mechanical
  properties of the static contract tests, not qualities a person must judge.
