## 1. Compose mount surface

- [ ] 1.1 Add the `${ART_OFFICIAL_DIR:-./art-official}:/app/art-official:ro,z}` bind mount and `ART_OFFICIAL_ROOT=/app/art-official` env forward to the `evennia` service in `compose.yaml`, add `ART_OFFICIAL_DIR` to `.env.example`, and verify with a compose-config test (`podman compose config` or the repo's compose contract test) that the mount and variable interpolation match the `ART_SEED_DIR` pattern exactly
- [ ] 1.2 Verify a no-directory start: bring the service up locally with no `./art-official` present and confirm the server starts normally with the empty-catalog diagnostic (acceptance criterion 10's startup half)

## 2. Named-volume preparation

- [ ] 2.1 Add the `evennia-art-official` volume and the profile-gated, non-interactive `artwork-prepare` one-shot service (write to the volume, read-only archive input when supplied) to `compose.yaml`, and verify the config test shows it is profile-gated and absent from the default `up` path
- [ ] 2.2 Write the confined preparation entrypoint script (empty-temp-dir extraction, refuse absolute/traversal/link entries, entry-count and byte caps, complete-then-replace of the volume's content subdirectory, no-archive no-op) and verify with local tests: valid archive populates, corrupt/unsafe archive exits non-zero leaving the prior tree byte-for-byte unchanged, no-archive run changes nothing

## 3. Build-context exclusion

- [ ] 3.1 Add `art-official/` to `.containerignore` and verify a build-context contract test proves the official directory is excluded while `web/static/art/defaults/` (the six built-ins) remains in the image inputs (acceptance criterion 10's publication half)

## 4. Documentation

- [ ] 4.1 Write `docs/development/official-artwork-deployment.md` (linked from `docs/_sidebar.md`): layout contract and LICENSE placement, the four preparation procedures (plain copy/sync default, separate Git repository/submodule, S3 CLI sync, local archive plus the one-shot service), the named-volume subdirectory rule for `ART_OFFICIAL_ROOT`, the stop/replace/start maintenance window, the no-partial-replacement rule, and the restart-only refresh rule — all in English
- [ ] 4.2 Update the README deployment section to link the guide and verify sidebar links resolve

## 5. Verification

- [ ] 5.1 Run the applicable compose/config and build-context contract tests once and confirm the full deployment acceptance set for this change: successful preparation, reuse without archive, failed extraction leaves destination unchanged, absent-directory startup, no runtime Git/S3 dependency
