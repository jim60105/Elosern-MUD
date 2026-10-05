# External Art Assets and Built-in Silhouette Fallbacks

**Date:** 2026-10-05
**Status:** Design approved in conversation; revised for the user's simpler manual/container deployment requirements; written specification awaiting user review.
**Scope:** A read-only mounted official artwork directory for monsters/player presets/NPCs, native deployment-time asset preparation, independent mutable runtime galleries, and attribute-selected built-in missing-image silhouettes.

## 1. Approved requirements

The code is open source. Official artwork is not secret, but its size and distribution requirements make the code repository and GitHub unsuitable publication locations for it. Distribute official artwork independently, with a separate license notice. Do not assume that code licensing grants rights to the artwork or that a particular hosting provider permits every image.

The user supersedes the earlier custom installation/release-management proposal with a simpler model. Artwork changes are infrequent, server count is small, and manual per-server deployment is acceptable. A deployment uses native tools to prepare one ordinary external artwork directory. Neither server startup nor ordinary gameplay downloads artwork, manages releases, or updates that directory.

Containers are the primary deployment target. Prefer a read-only bind mount of an operator-prepared host directory, following the existing compose mount pattern. A named volume populated before game startup is also supported. Git submodules, S3 synchronization, and archive extraction are alternative ways to prepare the same directory, not backends implemented inside the game.

Official artwork is a read-only shared baseline. Player selections and runtime-generated images remain independent of it. Characters created from the same player preset may share official image bytes, but must not share mutable gallery state.

The six existing fallback images are an explicit exception to external distribution. The user confirms that publishing these images is acceptable. Keep the original files in the code repository and use their alpha boundaries to render dark silhouettes where the stage currently renders a crude human SVG. Do not create replacement silhouette files or move these six originals into an external package.

Monster catalogs, habitat/population configuration, quest target provisioning, and encounter/guild difficulty are separate designs. In particular, this approval does not select a quest-driven, world-driven, or hybrid monster provisioning policy.

## 2. Existing implementation and architectural amendments

Relevant existing seams:

- `world/art/subjects.py`: typed runtime subjects. Monster subjects currently use threat-tier keys; named character subjects use an explicit `portrait_policy`.
- `world/art/gallery.py` and `gallery_match.py`: mutable runtime gallery records and deterministic equipment/default selection.
- `world/art/presenter.py`: portrait resolution and same-origin media payloads.
- `world/art/gallery_seed.py`: additive import of an operator-supplied external image tree into mutable gallery cards.
- `world/art/gallery_fallback.py`: the six-image selection rule, registry declarations, sex/apparent-age bands, and stable hashing for unspecified sex.
- `web/art_media.py`: closed, confined `/art/` serving, including the committed `defaults/` branch.
- `web/webclient-app/components/ReferenceArtwork.vue`: full-body stage artwork and the current missing-image SVG silhouette.
- `server/.art/`: persistent runtime art storage, already separate from tracked source files.
- `ART_SEED_ROOT` and the compose `ART_SEED_DIR` mount: the existing external seed-import configuration.

This design explicitly amends the following approved contracts for its implementation changes:

1. Engine design `2026-07-29-ai-mud-engine-design.md` section 2, D15: official generic-monster artwork is shared by **monster species/content identity**, not by threat tier. The species catalog is a separate prerequisite for actual species-specific monsters; this design does not invent that catalog or treat a display name as a species ID.
2. Gallery design `2026-09-08-character-gallery-art-design.md`, D10: official artwork is resolved read-only from the mounted directory, not copied into mutable seed cards. The existing seed-import facility remains valid for operator artwork intentionally imported as mutable cards.
3. The existing full-color built-in fallback presentation and missing-stage SVG contracts: built-ins are missing-image silhouette resources, not successful/generated portraits. Keep their serving route and attribute selection policy, but change their stage presentation and payload semantics.

Retain the deterministic/generative boundary, existing portrait eligibility checks, character age bounds, gallery ownership, and same-origin browser media contract. Official image presentation must not mutate game mechanics or make a network call.

## 3. Storage and distribution boundaries

| Source | Storage | Mutability | Included with code/image build |
|---|---|---|---|
| Official artwork | External bind-mounted directory or prepared named volume | Read-only to the game | No |
| Runtime/generated/imported gallery artwork | Existing `ART_STORE_ROOT` | Through existing gallery writers | No |
| Six built-in fallback originals | `web/static/art/defaults/` | Maintained with source, not player-editable | Yes |

Use a dedicated `ART_OFFICIAL_ROOT`, distinct from `ART_STORE_ROOT` and `ART_SEED_ROOT`. Its default is a gitignored `art-official/` directory under the game root; allow an explicit directory-root override. Compose uses `ART_OFFICIAL_DIR` for the host source and mounts it read-only at `/app/art-official`, with the existing SELinux labeling convention. An operator can choose a source outside the working tree. These names describe the planned configuration, not settings already implemented.

The deployed directory contains the current artwork only. Do not create a package registry, release directories, an activation pointer, a rollback command, or a custom downloader. The host deployment tools own writes; the game only reads. Named-volume deployments maintain the same root/layout contract.

Do not copy official artwork into the code repository, public container layers, frontend bundles, Storybook exports, documentation screenshots, or public CI artifacts. Exclude the local artwork directory from both source tracking and container build contexts. Preserve the six built-in originals as the approved publication exception. Behavioral tests use synthetic artwork rather than official directory contents.

The external host is configurable and provider-neutral. Hosting accounts, publication rights, and provider terms are operator responsibilities; no specific provider or authenticated delivery system is required by this design.

## 4. Directory and optional metadata contract

Use a predictable directory layout:

```text
art-official/
  LICENSE
  monster/<species-key>/<image-file>
  preset/<preset-key>/<image-file>
  npc/<npc-or-profile-key>/<image-file>
```

The content kind is `monster`, `preset`, or `npc`. Its directory key identifies registered authored content, not a runtime database row or translated display name. The image's root-relative path is its stable official asset identity. Replacing the bytes at that path updates the same visual choice; renaming/removing it removes that choice without deleting personal preferences.

A content directory may contain several images. An optional per-content `manifest.json` declares a `default` filename, `face_rect`, and `stage` placement. Follow the existing seed-metadata convention: when there is no valid explicit default, use the first valid image in deterministic filename order. A missing metadata file is normal. Invalid metadata emits a bounded diagnostic and uses the standard fitted face rectangle and identity stage placement; invalid metadata must not prevent unrelated artwork from loading.

Use the existing closed image format vocabulary and geometry validators. Decode dimensions locally; they need not be duplicated in metadata. If a declared face rectangle is invalid for any image it applies to, ignore that rectangle and use fitted per-image defaults. No mandatory top-level manifest, package ID, release number, declared checksums, or schema/release compatibility matrix is required.

The loader admits only valid image files confined to the configured root. Reject symlinked/out-of-root paths, unsupported formats, unreadable or undecodable files, and images exceeding the existing bounded image limits. Ignore unsupported content directories and unknown registry references with bounded diagnostics rather than rejecting the entire artwork root. Do not guess a species from its display name or map unknown species to a threat tier.

The artwork directory contains visual data and its license notice, never executable hooks, typeclass/prototype paths, balance values, character ages, or quest objectives.

## 5. Native deployment-time preparation

Prefer a host directory bind mount. The operator prepares it with any ordinary transfer method and mounts it read-only into the game. This requires no Git/S3/archive dependency in the runtime image.

| Preparation method | Contract and trade-off |
|---|---|
| Plain directory plus bind mount | Default. Copy or synchronize files manually, then restart the game. Minimal infrastructure and easy inspection/backup. |
| Separate Git repository/submodule | Checkout artwork from a separately hosted repository; mount its worktree. The parent code repository records only the submodule reference, never the artwork blobs. Artwork history/storage remains the external repository's responsibility. Do not add Git LFS without a demonstrated need. |
| S3/S3-compatible storage | Use the standard provider CLI to synchronize into the host directory or volume before starting the game. Credentials and network access belong to deployment, not gameplay. |
| Local archive | Use native `tar`/`unzip` tooling to prepare the same directory. A one-shot preparation service may automatically extract an explicitly supplied archive during deployment. |

These alternatives share one filesystem interface. Do not implement a provider abstraction, three backend plugins, or automatic source detection inside the game. The default implementation supports the mounted directory; the other methods are deployment procedures, not mandatory platform integrations.

For a named volume, run a one-shot preparation container with write access to that volume, then mount the volume read-only in the game container. A local archive is a read-only input to that preparation container. When archive preparation is selected, supplying the archive and invoking the deployment preparation step causes extraction automatically; the game process never performs extraction itself.

Use a trusted operator-supplied archive, not a player upload or an arbitrary remote archive selected by the game. Native extraction runs in a confined preparation container and an empty temporary directory; refuse unsafe paths/link entries and apply finite resource limits. Prepare the full replacement tree before replacing the destination, rather than extracting or synchronizing over the live prepared tree. A named-volume preparation replaces a content subdirectory within the volume, not the mount point itself; configure `ART_OFFICIAL_ROOT` to that subdirectory. If no input archive is supplied, use the prepared directory/volume as-is; ordinary startup must not erase it or repeatedly re-extract an old archive.

Artwork updates use a maintenance window: stop the game, prepare the replacement content, update the directory/volume, and start the game again. Sync or extraction failure must not overwrite the currently prepared tree with partial output. Retaining a backup and restoring it manually is sufficient; no release registry or automatic rollback is required.

The preparation step is explicitly invoked during deployment, not automatically fetched on every restart. A missing artwork directory is a valid no-art configuration; the operator can start the game with built-in silhouettes without preparing any official artwork. Do not require Git or S3 availability for startup.

## 6. Runtime catalog and stable content references

The existing art service owns the read-only official artwork catalog. It indexes valid files and optional metadata at startup and reads from that snapshot for ordinary resolution. Updating artwork takes effect after a restart; no file watcher or hot activation is required. It never calls Git, S3, an archive extractor, or an external host.

Mounted paths remain internal. Presentation payloads contain a validated same-origin media identity, an origin discriminator, geometry, and the runtime entity's existing name/identity. They do not expose filesystem roots, deployment sources, license text, or prompts.

Update the affected versioned art, roster, gallery, and combat portrait contracts together with their producers, validators, and frontend consumers. An official image, a mutable runtime image, and a silhouette must remain distinguishable in those contracts; do not infer origin or successful generation from the presence of a URL.

Separate two identities:

- The entity's runtime art subject identifies mutable gallery state and its existing generated artwork.
- Its official content reference identifies reusable authored images in the mounted directory.

For preset-born characters, use the existing `creation_preset_key` provenance to resolve the template's reference while retaining the player's own runtime gallery subject. Preset previews can resolve the same official reference without creating a character or gallery record.

For NPCs, establish the stable authored NPC/profile provenance in the owning creation/import path and resolve that registry reference. Do not equate every NPC of one numeric role tier with the same named character. A dynamically generated NPC may explicitly carry an allowed official reference or use its runtime portrait; no display-name inference is permitted.

For monsters, use a validated species/content reference once the separate monster catalog exists. Keep the shared-by-species image behavior independent of where or how many individuals are spawned. Until a species reference exists, use a runtime image if available or the built-in monster silhouette; never substitute a different species' official image by tier.

Two entities may reference identical official image bytes without sharing mutable state. Personal official-image selections and geometry overrides are stored with the runtime entity's art preferences, through the deterministic art writer. They do not modify manifest geometry or create shared template gallery records.

## 7. Resolution and image selection

Preserve the existing runtime gallery precedence: matching equipment-bound cards and explicit gallery defaults are resolved through the current APIs. Preserve valid classic runtime assets as part of that existing runtime-art path. A player may instead explicitly select a read-only official image; that personal selection is an art preference, not an edit of the mounted source.

The presentation chain is:

1. The valid image selected by the existing runtime gallery rules or an explicit personal official-image selection.
2. Existing valid classic runtime artwork, when no personal official selection resolves.
3. The mounted directory's default official image for the entity's content reference.
4. An attribute-selected built-in silhouette.

For the first step, an explicit official selection replaces the personal gallery-default choice; equipment-bound runtime cards retain their existing precedence. A later explicit runtime default selection clears the personal official-default selection, and vice versa. This makes changing the selected default unambiguous without modifying shared artwork.

A missing/stale official selection is ignored for image resolution while retaining the preference; continue to the remaining sources. Updating the directory does not switch a player-selected generated image to an official default. A selected root-relative official image identity resolves its updated bytes after restart. If that identity disappears, use the normal fallback chain rather than deleting the preference or another image.

Suppress automatic initial portrait generation when eligible official artwork already satisfies the content reference. Manual generation remains available through the existing generation path. Preserve the creation-time skip flag: the flag prevents automatic generation, not access to safe prebuilt artwork. A silhouette never counts as a generated card or a completed generation request.

Keep portrait age/eligibility validation before presenting official or runtime character artwork. Neither directory metadata nor a direct image URL can bypass the existing checks. Safe built-in placeholder selection can use validated entity attributes even when there is no named portrait policy; lack of a generated portrait identity must not force every NPC into the same human shape.

For an entity without a named portrait subject, use its stable runtime entity identity only as the deterministic placeholder selector's hash input. Do not install a `portrait_policy`, create a gallery record, or enqueue generation to obtain that input.

## 8. Read-only official images and personal overrides

Gallery/read models identify official entries as `official` and runtime cards as their existing sources. Official entries are selectable and previewable but are not appended to `GalleryRecord.cards` as seed cards.

Backend mutation APIs reject attempts to delete, replace, or regenerate-overwrite official entries. The frontend hides/disables inappropriate operations, but the backend remains authoritative. Manual generation creates runtime artwork, never writes into the mounted official directory, and never replaces an official asset file.

A character's face-rectangle or stage-placement adjustment for an official image is a personal override keyed by its stable root-relative image identity. Validate it using the existing geometry rules against the current image dimensions. If an artwork update makes a personal rectangle invalid, use valid directory metadata or fitted default geometry for rendering, retain the preference, and emit a bounded diagnostic. No other character's display changes.

Replacing the official directory never deletes runtime cards, clears player image selections, or imports new copies into every character's gallery.

## 9. Built-in silhouettes

Keep these original files and the existing closed `/art/defaults/` identities:

| Fallback key | Attribute-selected purpose |
|---|---|
| `man` | Adult male |
| `woman` | Adult female |
| `boy` | Male child |
| `girl` | Female child |
| `elder` | Elderly character; the current set has one shared elder image |
| `monster_anon` | Generic hooded monster |

Reuse `fallback_key_for` instead of duplicating selection in JavaScript. Preserve explicit valid registry fallback declarations as intentional authored overrides. Otherwise select using the entity's stored `sex` and **`apparent_age`**, not its true age or display name.

Retain the existing band boundaries: apparent age at or below 12 uses the child band, at or above 60 uses the elder band, and the interval between them uses the adult band. Unknown/invalid age follows the current adult-band fallback. Sex outside the male/female pair follows the current stable subject-key hash within the selected band's pool. A monster without an explicit override selects `monster_anon`.

The backend provides the resolved fallback key/media identity separately from the absent official/runtime portrait. The browser uses the original image's alpha channel as a CSS mask, filled with the existing dark silhouette styling. Set alpha mask semantics explicitly, preserve aspect ratio, and align to the stage floor. Do not show RGB texture, convert the originals, or stretch the figure as the current SVG does.

Replace the current stage SVG in `ReferenceArtwork.vue` with this attribute-selected mask. Keep the actor's name, targeting/focus behavior, and accessible missing/pending/failed labels outside the decorative mask. Retain reduced-motion behavior. Other portrait consumers must not treat the fallback as a full-color completed portrait; compact views may retain their existing text/glyph placeholder while the stage uses the silhouette.

The portrait's actual missing/pending/failed/unavailable state remains intact. Do not return `DONE` or label the silhouette as generated. If a real image fails in the browser after server resolution, use the already-provided silhouette reference and the load-failure label without another state mutation or remote request.

Built-in resources are present without a database gallery row, an official artwork directory, or a generation service. If even the bundled resource fails to load, retain the actor name and truthful text placeholder; do not leave the interaction surface unusable.

## 10. Serving and deployment

Extend the existing `/art/` media route with a closed official identity addressing an indexed root-relative image. Only catalog-admitted images can be served. Never expose an arbitrary directory or accept a user-provided filesystem path. Preserve extension/MIME validation and root confinement.

Include a file-content fingerprint in official URLs to invalidate browser caches after replacement. Compute it once when the startup catalog loads, not on every resolution/request. This is a cache token, not a package version or another maintained metadata file. Requests for outdated fingerprints after a maintenance restart may return 404 and use the ordinary silhouette fallback until the client receives the refreshed state. Do not retain historical asset directories just to serve old URLs. Personal gallery URLs and built-in `defaults/` URLs retain their existing ownership and confinement rules.

The frontend continues receiving only same-origin URLs. Official serving is a read-only catalog lookup; missing files return 404 and image resolution degrades rather than triggering download or extraction. Character eligibility remains a presentation/generation rule, not an assertion that publicly distributable artwork is secret.

Keep the runtime art volume. Add the separate read-only official bind mount, following the existing `ART_SEED_DIR` mount pattern, and document the named-volume alternative with optional one-shot preparation. Ensure public container builds exclude the official source directory. Keep existing seed-import mounts for operators who use that separate mutable-import feature. Game startup must not copy official artwork into the runtime store or recreate official images as seed cards.

## 11. Failure behavior and observability

| Failure | Required behavior |
|---|---|
| No mounted artwork/empty directory | Resolve runtime art or built-in silhouettes; remain playable |
| Deployment sync/extraction fails | Report failure in preparation; do not replace the prepared tree with partial output |
| A mounted file/metadata entry is unreadable or corrupt | Emit a bounded diagnostic; skip that entry and continue with valid image sources; never fetch on startup |
| Content has no official entry | Select the appropriate built-in silhouette when runtime artwork is absent |
| Runtime or official image fails browser loading | Show the provided silhouette and load-failure label |
| Player attempts official-file mutation | Named rejection; no file or shared preference changes |
| SD/LLM/external asset host is offline | No effect on local official images or silhouettes; retain existing manual-generation error behavior |

All new game-code logging uses `world.observability` named imports with stable English event identifiers and context. Record the startup catalog-load boundary and bounded invalid-file/metadata diagnostics. Include available asset, content kind/key, and entity identifiers in context; never place player-facing prose or credentials in logs. Native deployment tools retain their ordinary output; do not introduce a game-side transfer workflow just to log them. Image reads must not create art jobs or persistent game state.

## 12. Verification and acceptance

Implementation acceptance must establish observable behavior, not merely manifest or wiring assertions:

1. Bind-mount a synthetic official tree read-only, resolve an image, and fetch its actual same-origin bytes without copying it into the runtime gallery store.
2. Exercise the named-volume alternative and a native one-shot local-archive preparation container. Verify successful preparation, reuse without archive input, and a failed extraction that leaves the prepared destination unchanged. No live Git/S3 host is required.
3. Unknown content directories, unsupported images, bad metadata, out-of-root/symlink paths, and oversized images are refused or skipped as specified without preventing valid unrelated artwork from resolving. Prove files outside the configured root are not served.
4. Two preset-born characters share official image bytes but can choose different images and geometry. One character's changes cannot affect the other or the mounted source.
5. NPC provenance and monster species references resolve their own images. A different subject, name, or matching threat tier cannot select another content reference's image accidentally.
6. Official deletion/overwrite requests fail without changing files; manual generation remains isolated in the runtime store. A maintenance update/restart preserves generated cards and personal selections.
7. With no official directory and no generated artwork, adult male/female, boy/girl, elder, and monster actors show the corresponding built-in silhouette. Verify apparent-age boundaries and stable unknown-sex behavior using synthetic entities.
8. Exercise the actual stage in a focused browser test: silhouettes replace the old SVG, maintain geometry/labels, and transition to a real image when available. Image-load failure returns to the correct silhouette without claiming generation success.
9. Replacing an image at the same path and restarting produces a changed cache fingerprint while retaining personal selection identity. Invalid personal geometry uses valid metadata/default geometry without affecting other characters.
10. Verify builds/publication inputs contain no official artwork while retaining the six original built-ins. Missing-directory startup and gameplay perform no artwork acquisition.

Use package-adjacent tests and the existing shard manifest for new non-browser test modules. Follow the synthetic-data rules, focused-run limits, observability lint when logging changes, contract gate, and player-command documentation requirements for any added administrative command surface. Browser acceptance uses one focused local file/class; complete browser/evidence coverage remains CI-owned.

## 13. Delivery boundaries

This design is decomposed into six independently verifiable OpenSpec changes under `openspec/changes/`:

| Change | Scope (source sections) | Proposal |
|---|---|---|
| `official-artwork-catalog` | `ART_OFFICIAL_ROOT`, the read-only startup catalog: layout/admission/manifest contract, per-file fingerprint, `/art/official/...` media branch (sections 3, 4, 10) | [proposal](../../../openspec/changes/official-artwork-catalog/proposal.md) |
| `official-artwork-deployment` | Read-only bind mount + named-volume alternative + one-shot native archive preparation service, build-context exclusion, operator deployment guide (sections 5, 10) | [proposal](../../../openspec/changes/official-artwork-deployment/proposal.md) |
| `official-content-provenance` | Typed official content references: preset provenance with gallery independence, authored NPC/profile provenance, dynamic-NPC explicit-only rule, entity-identity-hash-only rule, monster species-catalog prerequisite with anti-tier-substitution (section 6) | [proposal](../../../openspec/changes/official-content-provenance/proposal.md) |
| `official-art-resolution-contracts` | Extended deterministic chain with the official-default step, payload origin discriminator, eligibility ordering, auto-generation suppression (sections 6, 7) | [proposal](../../../openspec/changes/official-art-resolution-contracts/proposal.md) |
| `official-art-personalization` | Personal official-image selections and geometry overrides, mutual default clearing, stale-selection retention, read-only official gallery entries and mutation rejection (sections 7, 8) | [proposal](../../../openspec/changes/official-art-personalization/proposal.md) |
| `builtin-silhouette-stage-fallback` | Silhouette payload semantics and attribute-selected alpha-mask stage rendering replacing the inline SVG (section 9) | [proposal](../../../openspec/changes/builtin-silhouette-stage-fallback/proposal.md) |

### Coverage mapping

Design section → owning change: sections 1 and 2 (boundaries/amendments) are contracts every change references; 3 → catalog + deployment; 4 → catalog; 5 → deployment; 6 → provenance (references) + resolution-contracts (chain/payload separation); 7 → resolution-contracts (chain, eligibility, suppression) + personalization (selection precedence/clearing); 8 → personalization; 9 → builtin-silhouette-stage-fallback; 10 → catalog (serving/fingerprint) + deployment (mounts/build exclusion); 11 → catalog (diagnostics/observability) + deployment (preparation reporting), each change carrying its own logging clauses; 12 → acceptance criterion 1 = catalog, 2 = deployment, 3 = catalog, 4 = personalization (with resolution-contracts' resolution half), 5 = provenance (synthetic-reference form until the species prerequisite lands), 6 = personalization + deployment, 7 = builtin-silhouette-stage-fallback, 8 = builtin-silhouette-stage-fallback (focused browser file), 9 = catalog + personalization, 10 = deployment (+ catalog startup invariants). No acceptance criterion is left unmapped; the species-dependent half of criterion 5 is explicitly deferred with its prerequisite rather than narrowed.

### Dependencies, external prerequisites, and shared-file conflicts

Machine-readable `## Batch:` sections in each proposal are authoritative; the matrix:

| Change | depends-on | Hard external prerequisite |
|---|---|---|
| `official-artwork-catalog` | — | — |
| `official-artwork-deployment` | `official-artwork-catalog` | — (live Git/S3 hosts explicitly not required) |
| `official-content-provenance` | `official-artwork-catalog` (single origin of the closed content-kind vocabulary) | Species-specific monster references require the separate, still-in-brainstorming monster species catalog design; until it lands, monsters resolve no official reference (guarded seams preserved) |
| `official-art-resolution-contracts` | `official-artwork-catalog`, `official-content-provenance`, `builtin-silhouette-stage-fallback` (declared so the origin vocabulary it extends is serialized ahead of it) | — |
| `official-art-personalization` | `official-artwork-catalog`, `official-content-provenance`, `official-art-resolution-contracts` | — |
| `builtin-silhouette-stage-fallback` | — | — |

Shared-file conflicts (files multiple changes edit):

- `world/art/presenter.py` payload branch + the portrait origin wire vocabulary (`protocol.js` + Python validators): `official-art-resolution-contracts` ↔ `builtin-silhouette-stage-fallback`. Dependency-free but NOT mergeable in parallel: `builtin-silhouette-stage-fallback` establishes the closed origin vocabulary (`runtime | silhouette | placeholder`) and the decorative `fallback` field; `official-art-resolution-contracts` extends that shipped vocabulary with `official`. Recommended order is silhouette-first; the reverse requires the silhouette change to rebase.
- `world/art/gallery_match.py` chain + payloads: `official-art-resolution-contracts` ↔ `official-art-personalization` (declared dependency; personalization MODIFIEDs the exact chain to place the personal official selection at the default-card slot and qualifies the classic step).
- `webclient-art-panel` portrait-catalog requirement: `builtin-silhouette-stage-fallback` (decorative fallback fields) ↔ `official-art-resolution-contracts` (`official` discriminator extension) ↔ `official-art-personalization` (official-backed entries) — one requirement, three sequential editors, per the wave order.
- `compose.yaml`/`.env.example`/inventory test: `official-artwork-catalog` ↔ `official-artwork-deployment` (declared dependency; disjoint variables).
- `world/art/gallery.py` (record lifecycle + preference fields vs. read-model projections), gallery-panel validators, management adapters: `official-art-resolution-contracts` ↔ `official-art-personalization` (declared dependency, sequential).
- `world/art/gallery_fallback.py` comments: `official-content-provenance` ↔ `builtin-silhouette-stage-fallback` (comment-only overlap; provenance first).
- `ReferenceArtwork.vue`: `builtin-silhouette-stage-fallback` (stage placeholder region) ↔ `official-art-personalization` (personal-override affordances; disjoint regions, serialize anyway).

Genuinely independent (no dependency and no shared file with each other): `builtin-silhouette-stage-fallback` from `official-artwork-deployment` and from `official-content-provenance` (comment overlap aside). `builtin-silhouette-stage-fallback` needs no official directory at runtime; the dependency `official-art-resolution-contracts` declares on it exists solely to serialize the shared presenter/protocol vocabulary (it establishes `runtime | silhouette | placeholder` + the decorative `fallback` field; the resolution change extends it with `official`) — dependency-free-in-substance but strictly non-parallel in integration, and integration of `presenter.py`, `protocol.js`, and the management/gallery surfaces must run under one integrator, never as a parallel merge.

### Suggested parallel implementation waves

One engineer-day per change; each wave's changes touch disjoint files except where serialized below:

1. **Wave 1 (parallel):** `official-artwork-catalog` ∥ `builtin-silhouette-stage-fallback` (independent of the official mount per section 9; it establishes the origin/fallback wire vocabulary that wave 3 extends).
2. **Wave 2 (parallel after wave 1):** `official-artwork-deployment` ∥ `official-content-provenance` (after catalog).
3. **Wave 3:** `official-art-resolution-contracts` — single integrator pass over `presenter.py`/`gallery_match.py`/`protocol.js`, extending the origin vocabulary shipped by wave 1's silhouette change (exactly once) with `official`.
4. **Wave 4:** `official-art-personalization` — last, after the resolution payloads and stage component settle.

If the landing order ever reverses (resolution contracts before silhouettes), the silhouette change rebases its vocabulary onto the already-shipped discriminator. Monster species-specific integration follows the separate monster catalog design when its owner lands the species catalog; a threat-tier alias is not a substitute for that prerequisite. Monster habitat placement, target quantities, guild difficulty, city safety, and quest provisioning are outside this document and remain subject to their own brainstorming and approvals.

No runtime implementation is included in this design-document change; the six proposals are planning artifacts. Use the repository's specification-driven workflow (`/opsx:apply`) for implementation.
