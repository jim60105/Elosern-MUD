# Design

## Context

See `proposal.md` — Why. The current state that shapes the approach:

- `Containerfile` (builder stage, commit `c1aa25f6`) copies
  `pyproject.toml`/`uv.lock`, then `packages/map-core/pyproject.toml`, runs
  `uv sync --locked --no-dev --no-install-project --no-editable
  --no-install-package elosern-map-core`, fetches the weight with
  `BriaRmBgSession.download_models()`, copies `packages/map-core/` source, then
  re-syncs with `--refresh-package elosern-map-core`.
- `uv.lock` records `source = { editable = "packages/map-core" }` with no
  content hash, so the wheel cannot be installed without the package source;
  the source therefore sits above the weight layer. uv 0.12.0 caches the built
  local-directory wheel and reinstalls the previous contents after a source
  edit unless the package is explicitly refreshed.
- The main spec requirement at `openspec/specs/container-image/spec.md:7`
  carries the stale ordering sentence. Its canonical ID from
  `uv run --locked python -m tools.spec_traceability list` is
  `container-image::multi-stage-containerfile`.
- `tests/test_container_contract.py` already holds the mechanical assertions:
  `test_the_default_removal_weight_is_acquired_during_the_image_build` asserts
  the only `COPY` after the fetch is
  `COPY --chown=root:0 packages/map-core/ packages/map-core/`;
  `test_the_map_package_wheel_is_rebuilt_after_the_weight_is_acquired` asserts
  the fetch precedes that copy and that `--refresh-package
  elosern-map-core` appears after it. The latter has no `covers_requirement`.

## Goals / Non-Goals

**Goals:**

- Make the `Multi-stage Containerfile` requirement state the ordering that is
  actually built, with both the acquisition predecessor and the post-acquisition
  wheel install normative.
- Give the wheel-freshness invariant a home that the existing static contract
  assertions can establish.
- Leave the canonical requirement ID and every existing scenario intact.

**Non-Goals:**

- Any edit to `Containerfile`, `tests/test_container_contract.py` assertions,
  `compose.yaml`, or `docs/`.
- Any new requirement, any other capability, any container build or rebuild.
- Archive-time sync of the main spec; that is a later workflow.

## Decisions

**D1 — MODIFIED, not ADDED, and the title is copied byte-for-byte.**
`openspec` derives the canonical ID from `<capability>::<requirement title>`
(lowercased, hyphenated). The delta header is exactly
`### Requirement: Multi-stage Containerfile`, so every existing
`covers_requirement("container-image::multi-stage-containerfile")` annotation in
`tests/test_container_contract.py` stays valid and the traceability ledger does
not gain or lose an entry. Alternative rejected: adding a second requirement for
the wheel — it would create a second behavior requirement for the same invariant
and leave two requirements describing one builder-stage ordering.

**D2 — The full requirement block is reproduced in the delta, all nine
existing scenarios included.** A MODIFIED delta replaces the whole requirement
at sync time; a partial block would delete the retained scenarios. The nine
existing scenarios are copied with their text unchanged, so nothing that is
currently asserted is dropped. Two scenarios are appended:
`Map-package source edits reuse model acquisition` and `A rebuilt image carries
the current map-package code`.

**D3 — The body stays under 500 characters (496) by moving detail into the
scenarios.** The new body reads:

> `Containerfile` SHALL be a Podman-focused multi-stage build: a downloader
> verifying the init binary, a builder, an application-layout stage that
> prepares the runtime tree, and a final stage carrying only the venv, init
> binary, application code, and the acquired removal weight. Model acquisition
> SHALL follow locked third-party dependency installation. The locked local
> `elosern-map-core` wheel SHALL install from `packages/map-core/` after
> acquisition and SHALL be rebuilt, never a cached wheel.

The replaced sentence is `Model acquisition SHALL follow locked dependency
installation and precede application-source copying`. It is inexact because one
locked package installs after acquisition, and because "application-source
copying" no longer describes the builder stage (application source is copied by
the separate `app-layout` stage, which consumes the builder). "venv", not
"virtual environment", matches the wording the retained scenario `Final
artifacts use independent linked layers` already uses.

**D4 — Traceability comes from an annotation on the existing test, not a new
test.** The behavior is already committed and asserted; a second test would
duplicate the same two assertions and pin the same `Containerfile` lines twice.
The annotation is `covers_requirement("container-image::multi-stage-containerfile")`
on `ContainerContractTests.test_the_map_package_wheel_is_rebuilt_after_the_weight_is_acquired`
— a literal ID, on a test whose assertions establish both new scenarios (the
post-fetch `COPY` boundary for the first, the ordering plus
`--refresh-package elosern-map-core` for the second). Alternative rejected:
annotating with the removal-weight requirement, which describes acquisition, not
the wheel.

**D5 — No design-level review document.** Both new scenarios are mechanical
properties of the static contract tests; no tone, polish, or fidelity judgment
is required, so the proposal records `Human-reviewed: nothing in this change`
instead of naming a review document.

## Risks / Trade-offs

- **Spec text drifts from `Containerfile` again** → the two static contract
  tests are the executable anchor: any reordering of the builder stage or
  removal of `--refresh-package` fails
  `tests.test_container_contract` independently of the prose.
- **The compact body drops "precede application-source copying"** → the
  ordering is preserved where it is actually observable: the retained scenario
  `Application-only rebuilds reuse model acquisition` and the new map-package
  scenario both state cache reuse, and `app-layout` consumes the builder stage,
  so no scenario claims source copying inside the builder.
- **Body length 496 characters (from 499)** → still under the strict limit, so
  `openspec validate --strict` passes without a length warning.
- **Traceability double-claims the requirement** → allowed and intended: two
  tests already annotate `container-image::multi-stage-containerfile`
  (`test_containerfile_separates_verified_download_build_layout_and_runtime`,
  `test_authored_static_content_is_baked_into_the_runtime_tree`); adding a third
  claim changes no count of uncovered requirements.

## Migration Plan

None. The change alters one requirement body, two appended scenarios, and one
test decorator line; there is no runtime, data, or deployment step. Rollback is
reverting the single commit.

## Acceptance

From the repository root, all four must hold after the remaining tasks:

- `openspec validate container-map-wheel-after-weight --strict` → passes with no
  warnings.
- `uv run --locked python -m unittest tests.test_container_contract` → 21 tests,
  OK.
- `uv run --locked python -m tools.spec_traceability check` → 2759 requirements,
  0 uncovered, 0 errors, with the new association present.
- `uv run --locked python -m tools.contract_gate` → passed.
