## Context

See proposal.md for motivation. `compose.yaml` already ships two read-only host mounts (prompts, seed art) and profile-gated one-shot services (`bootstrap`), so the mount and preparation surfaces are pattern copies, not new machinery. The source design is §5 and §10. `ART_OFFICIAL_ROOT` and the catalog itself belong to `official-artwork-catalog`; this change is the operator/deployment surface only.

## Goals / Non-Goals

**Goals:**
- Default bind-mount path works out of the box; named-volume path works with an explicitly invoked preparation step; both converge on the identical directory layout contract.
- Zero runtime acquisition surface: the image carries no downloader, sync client, or extraction workflow.

**Non-Goals:**
- No compose secrets, provider credentials, or network configuration for artwork (operator-side responsibility). No in-game admin command for artwork updates (the maintenance window is host tooling). No LFS.

## Decisions

- **Bind mount default `${ART_OFFICIAL_DIR:-./art-official}` with `ro,z`** — byte-for-byte the `ART_SEED_DIR` pattern (design §3); the alternative of baking a named volume into the default path was rejected because the design names bind mount the default and volume an alternative.
- **Volume mode points `ART_OFFICIAL_ROOT` at a content subdirectory of the volume, not the mount point**: preparation replaces a subdirectory atomically, which is impossible safely at a live mount point; the settings env-forward is documented accordingly.
- **Preparation via a second profile-gated service using the same image plus native `tar`/`unzip`** rather than a game-side command: the design forbids the game performing extraction; a one-shot container with write access to the volume and a read-only archive input is the smallest confinement that satisfies "prepare complete tree, then replace." Python stdlib `tarfile`-style guards (unsafe-path refusal, resource limits) are expressed as a small shell entrypoint script; choosing shell over a Python module keeps it clearly outside the game process. (The runtime base image is `python:3.13-slim`; the preparation entrypoint uses only `tar`/`unzip`/`sh` available or installed in that stage.)
- **Submodule/S3 stay documentation, not compose services** — the design says provider abstraction and per-method integrations are forbidden; a `docs/development/official-artwork-deployment.md` guide states each procedure and its trade-off.
- **`.containerignore` exclusion rides the existing gitignored-paths requirement** — `art-official/` is gitignored by `official-artwork-catalog`, and the ignore-file requirement already names gitignored dev-only paths; this change adds the explicit entry and test, not a new requirement.

## Risks / Trade-offs

- [Extraction entrypoint mishandles a hostile archive] → archives are operator-trusted, but the service still refuses traversal/absolute/link entries and enforces size/entry caps, and extracts only into an empty temporary directory; worst case is a failed one-shot, never a corrupted live tree.
- [Operators edit the bind-mounted tree while the game runs, expecting hot effect] → restart-only refresh is the design's contract; the deployment guide states the maintenance window explicitly.
- [Same image for preparation couples game-image churn to deployment tooling] → accepted: one fewer artifact to publish; preparation only needs `sh`+`tar`/`unzip` from that image.

## Migration Plan

Additive compose change: existing deployments update `compose.yaml` and (optionally) `ART_OFFICIAL_DIR` in `.env`; nothing to roll back beyond reverting the file.

## Open Questions

None.
