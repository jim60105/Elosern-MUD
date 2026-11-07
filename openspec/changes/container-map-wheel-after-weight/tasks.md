# Tasks

## 1. Already landed builder-stage ordering (commit `c1aa25f6`)

- [x] 1.1 `Containerfile`, `builder` stage: copy `pyproject.toml` + `uv.lock`, then `packages/map-core/pyproject.toml` only, run `uv sync --locked --no-dev --no-install-project --no-editable --no-install-package elosern-map-core`, run `U2NET_HOME=/rembg REMBG_HOME=/rembg /venv/bin/python -c "from rembg.sessions.bria_rmbg import BriaRmBgSession; BriaRmBgSession.download_models()" && test -s /rembg/models/bria-rmbg/bria-rmbg.onnx`, then copy `packages/map-core/` source. Verified at `c1aa25f6` by `tests/test_container_contract.py::ContainerContractTests.test_the_default_removal_weight_is_acquired_during_the_image_build`, which asserts the only `COPY` after the fetch is `COPY --chown=root:0 packages/map-core/ packages/map-core/`.
- [x] 1.2 `Containerfile` builder stage: the post-fetch sync carries `--refresh-package elosern-map-core`, so uv rebuilds the local-directory wheel instead of reinstalling the cached one. Verified at `c1aa25f6` by `tests/test_container_contract.py::ContainerContractTests.test_the_map_package_wheel_is_rebuilt_after_the_weight_is_acquired` (asserts fetch precedes the source copy and `--refresh-package elosern-map-core` follows it).
- [x] 1.3 Measured with podman 5.8.9 against the real `Containerfile` at `c1aa25f6`: cold `--target builder` build 98 s (74 packages + 1.02 GB weight); rebuild after a `packages/map-core/` source edit 13-16 s with the weight layer served from cache and exactly one package rebuilt and installed. Recorded in the `c1aa25f6` builder-stage comments.

## 2. Spec alignment artifacts (this change)

- [x] 2.1 Write `openspec/changes/container-map-wheel-after-weight/specs/container-image/spec.md` as a `## MODIFIED Requirements` delta for `### Requirement: Multi-stage Containerfile`, keeping all nine existing scenarios verbatim, appending `Map-package source edits reuse model acquisition` and `A rebuilt image carries the current map-package code`, and keeping the requirement body at 496 characters. Verify with `openspec validate container-map-wheel-after-weight --strict` reporting no warnings.
- [x] 2.2 Write `proposal.md` (no new capability, `container-image` modified) and `design.md` (D1-D5, acceptance commands) so they name the same requirement title, the same two scenarios, and the same canonical ID `container-image::multi-stage-containerfile`. Verify with `openspec status --change container-map-wheel-after-weight --json` reporting `proposal`, `specs`, `design`, and `tasks` at their resolved paths.

## 3. Remaining traceability and gates

- [ ] 3.1 In `tests/test_container_contract.py`, add `@covers_requirement("container-image::multi-stage-containerfile")` (already imported at line 10) directly above `ContainerContractTests.test_the_map_package_wheel_is_rebuilt_after_the_weight_is_acquired` (currently unannotated, method body at the `def` that follows `test_the_default_removal_weight_is_acquired_during_the_image_build`). Change no assertion. Verify with `grep -n "multi-stage-containerfile" tests/test_container_contract.py` showing the decorator above that method's `def` line.
- [ ] 3.2 Verify the container contract still passes: `uv run --locked python -m unittest tests.test_container_contract` → `Ran 21 tests` and `OK`.
- [ ] 3.3 Verify traceability: `uv run --locked python -m tools.spec_traceability check` → `2759 requirements, 12680 associations, 2759 covered, 0 uncovered, 0 errors` (one association more than the 12679 baseline measured before the annotation; no requirement is added, removed, or renamed).
- [ ] 3.4 Verify the aggregate gate: `uv run --locked python -m tools.contract_gate` → passed (traceability, observability and test-data lints, shard manifests).

## Workflow follow-up

- Archive this change after review: sync the delta into `openspec/specs/container-image/spec.md`, then run `openspec validate --all --strict`.
- Do not rebuild the image for this change; the behavior it records is already committed at `c1aa25f6`.
