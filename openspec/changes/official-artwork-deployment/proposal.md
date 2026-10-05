## Batch:

- depends-on: official-artwork-catalog
- conflicts: `official-artwork-catalog` on `.env.example` and its inventory contract test (disjoint variables, merged by this change landing second); no other shared files

## Why

The approved deployment model (source design §5, §10) prepares one external official-artwork directory with native host tools — a read-only bind mount by default, a named volume with an optional one-shot local-archive preparation container as the alternative. Git submodule and S3 synchronization are documented deployment procedures, not new runtime backends. Compose must carry the mount surface so operators can follow the existing `ART_SEED_DIR` pattern.

## What Changes

- Add the read-only official-artwork bind mount to `compose.yaml`: `${ART_OFFICIAL_DIR:-./art-official}:/app/art-official:ro,z`, with the service environment forwarding `ART_OFFICIAL_ROOT=/app/art-official`, following the existing seed-mount/SELinux pattern. An absent host directory remains a valid no-art start.
- Add a profile-gated, non-interactive one-shot `artwork-prepare` service for named-volume deployments: it runs with write access to a dedicated `evennia-art-official` volume and an explicitly supplied operator archive mounted read-only, extracts into a fresh empty temporary directory, refuses unsafe path/link entries under finite resource limits, and atomically replaces the volume's content subdirectory only on full success. With no archive supplied it is a no-op; it is never re-run by game startup and the game process never extracts anything.
- Document the native preparation procedures — plain directory copy/sync, separate Git repository/submodule checkout, S3 CLI sync, local archive with the one-shot preparation service — as operator-side procedures sharing the one mounted-directory interface, including the maintenance-window update flow (stop, replace, start) and the no-partial-replacement rule.
- Exclude the official artwork directory from source tracking and container build contexts (`.containerignore`, build-context contract), while the six committed built-in fallback originals stay in the image.

## Capabilities

### New Capabilities

- None — deployment behavior is owned by the existing container deployment capability.

### Modified Capabilities

- `container-image`: the `evennia` service carries the read-only official-artwork mount (bind default + named-volume alternative with `ART_OFFICIAL_ROOT` pointed at the volume's content subdirectory), a profile-gated one-shot archive-preparation service with its safety contract, and build-context exclusion of official artwork while retaining the built-in defaults.

## Impact

- Files: `compose.yaml`, `.containerignore`, deployment documentation (`docs/development/official-artwork-deployment.md`, new), README deployment section.
- No new Python runtime code: preparation runs in a confined one-shot container using native tooling; the game only reads. No Git/S3/archive dependency in the runtime image; startup never fetches.
