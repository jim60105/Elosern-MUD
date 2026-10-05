# External Art Assets and Built-in Silhouette Fallbacks

**Date:** 2026-10-05
**Status:** Design approved in conversation; written specification awaiting user review.
**Scope:** Explicit installation of external official artwork, read-only official image resolution for monsters/player presets/NPCs, independent mutable runtime galleries, and attribute-selected built-in missing-image silhouettes.

## 1. Approved requirements

The code is open source. Official artwork is not secret, but its size and distribution requirements make the code repository and GitHub unsuitable publication locations for it. Distribute official artwork independently, with a separate license notice. Do not assume that code licensing grants rights to the artwork or that a particular hosting provider permits every image.

The approved acquisition model is an explicit asset installation command, with both an external download source and a local package input. Neither server startup nor ordinary gameplay downloads artwork.

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
2. Gallery design `2026-09-08-character-gallery-art-design.md`, D10: official packages are resolved read-only, not copied into mutable seed cards. The existing seed-import facility remains valid for operator artwork intentionally imported as mutable cards.
3. The existing full-color built-in fallback presentation and missing-stage SVG contracts: built-ins are missing-image silhouette resources, not successful/generated portraits. Keep their serving route and attribute selection policy, but change their stage presentation and payload semantics.

Retain the deterministic/generative boundary, existing portrait eligibility checks, character age bounds, gallery ownership, and same-origin browser media contract. Official image presentation must not mutate game mechanics or make a network call.

## 3. Storage and distribution boundaries

| Source | Storage | Mutability | Included with code/image build |
|---|---|---|---|
| Official artwork | Installed external package directory | Read-only to the game | No |
| Runtime/generated/imported gallery artwork | Existing `ART_STORE_ROOT` | Through existing gallery writers | No |
| Six built-in fallback originals | `web/static/art/defaults/` | Maintained with source, not player-editable | Yes |

Use a dedicated `ART_PACK_ROOT`, distinct from `ART_STORE_ROOT` and `ART_SEED_ROOT`. Its default is a gitignored `server/.art-packs/` directory; allow an explicit directory-root override for an operator-owned location outside the working tree. Container deployments mount it on a separate persistent volume. The installer needs write access; the ordinary game process only needs read access to installed releases and the activation record.

Do not copy official packages into the code repository, public container layers, frontend bundles, Storybook exports, documentation screenshots, or public CI artifacts. Preserve the six built-in originals as the approved publication exception. Behavioral tests use synthetic artwork rather than official package contents.

The external host is configurable and provider-neutral. Hosting accounts, publication rights, and provider terms are operator responsibilities; no specific provider or authenticated delivery system is required by this design.

## 4. Asset package contract

Use a ZIP package containing one root `manifest.json` and its declared image files. The manifest has a schema version independent of the package release version. Version 1 declares:

- `pack_id` and `release`: stable package identity and an immutable release identifier.
- `license_file`: a confined relative path to the artwork license notice bundled with the package.
- `entries`: official image entries, each with a stable `asset_id`, `content_kind`, `content_key`, relative image path, SHA-256, format, decoded dimensions, `face_rect`, and `stage` placement.
- `defaults`: one default `asset_id` per content reference represented in the package.

`content_kind` is `monster`, `preset`, or `npc`. `content_key` identifies authored content, not a runtime database row or a translated display name. `asset_id` distinguishes selectable official images and remains stable across releases when the image is the same conceptual choice. Updating that image's bytes requires a new package release, not editing an installed release in place.

A content reference may have several selectable images. Asset IDs and file paths must be unique within a release. Each default must reference an entry with the same content reference. Absence of a default for an included content reference, duplicate identities, incompatible schema versions, missing declared files, digest mismatches, or invalid geometry reject the package before activation.

Reuse the existing closed image format vocabulary and face-rectangle/stage validators. Verify decoded dimensions against the manifest. A package contains image data and license/manifest metadata only: no Python modules, prototype paths, executable hooks, balance values, or character ages.

Content references use known registry keys. A package compatible with the installed content may only use registered preset/NPC keys and, once available, registered monster species keys. Unknown references reject installation with a diagnostic naming the unresolved reference. Do not guess a species from a monster's name or silently map it to its threat tier.

The package describes visual choices only. It never creates NPCs or monsters, changes their attributes, or supplies quest objectives.

## 5. Explicit installation and activation

The planned CLI is `uv run --locked python -m tools.art_assets`, with these operations:

- `install --source <https-url-or-local-zip>`: acquire, validate, install, and activate the selected release.
- `activate --pack <pack-id> --release <release>`: explicitly select an already-installed valid release, including a rollback.
- `check`: report the active release, invalid references/files, and missing official images for the registered supported content.

These are design interfaces, not commands implemented by this document.

Version 1 has one active official package release. A release may cover all supported content kinds; unrepresented content uses built-in silhouettes. Do not add package merging, mirror selection, automatic latest-version discovery, or background updates.

Installation follows this sequence:

1. Acquire the explicitly selected ZIP into a staging directory under the package root. A remote source uses HTTPS and finite download/time/resource limits. A local source needs no network access.
2. Validate the manifest, content references, license path, archive entries, decoded image metadata, checksums, and geometry before making the release visible.
3. Install the completed release under its immutable package/release directory.
4. Atomically replace the activation record only after validation and installation succeed.

Reject absolute paths, parent traversal, symlinks, hard-link aliases, special files, executable entries, and archive entries outside the declared package layout. Bound both compressed download size and total extracted bytes/image dimensions. SHA-256 provides byte-integrity checking against the selected manifest; it is not a claim of publisher authentication.

An existing release with matching verified content is an idempotent installation. Reusing the same pack/release identity for different bytes is an error. Never overwrite an installed release. Serialize activation writes and retain previous releases; removal is not part of the initial CLI.

A failed acquisition or validation leaves the previous activation record unchanged. An interrupted staging/install operation never becomes active and does not prevent the current release from being used. The game sees either the previous valid release or the completed new release, never a mixture.

## 6. Runtime catalog and stable content references

The existing art service owns the runtime read-only package catalog. It reads and validates the local activation record/manifest, refreshes its catalog when activation changes, and exposes the selected release as one immutable snapshot for each resolution. It never calls the installer or an external host.

Installed paths remain internal. Presentation payloads contain a validated same-origin media identity, an origin discriminator, geometry, and the runtime entity's existing name/identity. They do not expose package filesystem roots, download URLs, license text, or prompts.

Update the affected versioned art, roster, gallery, and combat portrait contracts together with their producers, validators, and frontend consumers. An official image, a mutable runtime image, and a silhouette must remain distinguishable in those contracts; do not infer origin or successful generation from the presence of a URL.

Separate two identities:

- The entity's runtime art subject identifies mutable gallery state and its existing generated artwork.
- Its official content reference identifies reusable authored images in the installed package.

For preset-born characters, use the existing `creation_preset_key` provenance to resolve the template's reference while retaining the player's own runtime gallery subject. Preset previews can resolve the same official reference without creating a character or gallery record.

For NPCs, establish the stable authored NPC/profile provenance in the owning creation/import path and resolve that registry reference. Do not equate every NPC of one numeric role tier with the same named character. A dynamically generated NPC may explicitly carry an allowed official reference or use its runtime portrait; no display-name inference is permitted.

For monsters, use a validated species/content reference once the separate monster catalog exists. Keep the shared-by-species image behavior independent of where or how many individuals are spawned. Until a species reference exists, use a runtime image if available or the built-in monster silhouette; never substitute a different species' official image by tier.

Two entities may reference identical official image bytes without sharing mutable state. Personal official-image selections and geometry overrides are stored with the runtime entity's art preferences, through the deterministic art writer. They do not modify manifest geometry or create shared template gallery records.

## 7. Resolution and image selection

Preserve the existing runtime gallery precedence: matching equipment-bound cards and explicit gallery defaults are resolved through the current APIs. Preserve valid classic runtime assets as part of that existing runtime-art path. A player may instead explicitly select a read-only official image; that personal selection is an art preference, not an edit of the official package.

The presentation chain is:

1. The valid image selected by the existing runtime gallery rules or an explicit personal official-image selection.
2. Existing valid classic runtime artwork, when no personal official selection resolves.
3. The current package's default official image for the entity's content reference.
4. An attribute-selected built-in silhouette.

For the first step, an explicit official selection replaces the personal gallery-default choice; equipment-bound runtime cards retain their existing precedence. A later explicit runtime default selection clears the personal official-default selection, and vice versa. This makes changing the selected default unambiguous without modifying shared artwork.

A missing/stale official selection is ignored for image resolution while retaining the preference; continue to the remaining sources. Updating a package does not switch a player-selected generated image to an official default. A stable selected official asset ID resolves its new revision when the explicitly installed release changes. If that ID disappears, use the normal fallback chain rather than deleting the preference or another image.

Suppress automatic initial portrait generation when eligible official artwork already satisfies the content reference. Manual generation remains available through the existing generation path. Preserve the creation-time skip flag: the flag prevents automatic generation, not access to safe prebuilt artwork. A silhouette never counts as a generated card or a completed generation request.

Keep portrait age/eligibility validation before presenting official or runtime character artwork. Neither package metadata nor a direct image URL can bypass the existing checks. Safe built-in placeholder selection can use validated entity attributes even when there is no named portrait policy; lack of a generated portrait identity must not force every NPC into the same human shape.

For an entity without a named portrait subject, use its stable runtime entity identity only as the deterministic placeholder selector's hash input. Do not install a `portrait_policy`, create a gallery record, or enqueue generation to obtain that input.

## 8. Read-only official images and personal overrides

Gallery/read models identify official entries as `official` and runtime cards as their existing sources. Official entries are selectable and previewable but are not appended to `GalleryRecord.cards` as seed cards.

Backend mutation APIs reject attempts to delete, replace, or regenerate-overwrite official entries. The frontend hides/disables inappropriate operations, but the backend remains authoritative. Manual generation creates runtime artwork, never writes into the package directory, and never replaces an official asset file.

A character's face-rectangle or stage-placement adjustment for an official image is a personal override keyed by the selected asset ID. Validate it using the existing geometry rules against the current image dimensions. If a package revision makes a personal rectangle invalid, use the new manifest geometry for rendering, retain the preference, and emit a bounded diagnostic. No other character's display changes.

Official package activation never deletes runtime cards, clears player image selections, or imports new copies into every character's gallery.

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

Built-in resources are present without a database gallery row, an installed package, or a generation service. If even the bundled resource fails to load, retain the actor name and truthful text placeholder; do not leave the interaction surface unusable.

## 10. Serving and deployment

Extend the existing `/art/` media route with a closed official identity containing the package/release and asset identity. Only manifest-listed files from the addressed installed release can be served. Never expose an arbitrary directory or accept a user-provided filesystem path. Preserve extension/MIME validation and root confinement.

Include the release identity in official URLs so a package update cannot reuse a cached URL for different bytes. Retain the installed previous release directories so in-flight old URLs remain valid across an activation switch. Personal gallery URLs and built-in `defaults/` URLs retain their existing ownership and confinement rules.

The frontend continues receiving only same-origin URLs. Official serving is a read-only catalog lookup; missing files return 404 and image resolution degrades rather than triggering installation. Character eligibility remains a presentation/generation rule, not an assertion that publicly distributable artwork is secret.

Keep the runtime art volume. Add the separate persistent official-package mount and ensure the public container build does not copy package files. Keep existing seed-import mounts for operators who use that separate mutable-import feature. Startup must not copy official packages into the runtime store or recreate official images as seed cards.

## 11. Failure behavior and observability

| Failure | Required behavior |
|---|---|
| No active package | Report missing official artwork; resolve runtime art or built-in silhouettes; remain playable |
| Download, extraction, or manifest validation fails | Refuse activation; retain previous release |
| Active manifest/file is unreadable or corrupt | Emit a bounded diagnostic; continue using other valid image sources; never fetch on startup |
| Content has no official entry | Select the appropriate built-in silhouette when runtime artwork is absent |
| Runtime or official image fails browser loading | Show the provided silhouette and load-failure label |
| Player attempts official-file mutation | Named rejection; no file or shared preference changes |
| SD/LLM/external asset host is offline | No effect on local official images or silhouettes; retain existing manual-generation error behavior |

All new production logging uses `world.observability` named imports with stable English event identifiers and context. Record package install/activation boundaries and bounded invalid-package/image diagnostics. Include available pack, release, asset, content kind/key, and entity identifiers in context; never place player-facing prose or credentials in logs. Image reads must not create art jobs or persistent game state.

## 12. Verification and acceptance

Implementation acceptance must establish observable behavior, not merely manifest or wiring assertions:

1. Install a synthetic local package, resolve an official image, and fetch its actual same-origin bytes. Reinstalling the same release is idempotent.
2. Install from a controlled local HTTPS test endpoint; interrupted/corrupt acquisition leaves the previous release active. No external production host is required for tests.
3. Reject unknown content references, malformed defaults, wrong hashes/dimensions/geometry, archive traversal/link entries, and oversized input before activation. Prove that files outside the package root remain untouched.
4. Two preset-born characters share official image bytes but can choose different images and geometry. One character's changes cannot affect the other or the package manifest.
5. NPC provenance and monster species references resolve their own images. A different subject, name, or matching threat tier cannot select another content reference's image accidentally.
6. Official deletion/overwrite requests fail without changing files; manual generation remains isolated in the runtime store. Activation preserves generated cards and personal selections.
7. With no package and no generated artwork, adult male/female, boy/girl, elder, and monster actors show the corresponding built-in silhouette. Verify apparent-age boundaries and stable unknown-sex behavior using synthetic entities.
8. Exercise the actual stage in a focused browser test: silhouettes replace the old SVG, maintain geometry/labels, and transition to a real image when available. Image-load failure returns to the correct silhouette without claiming generation success.
9. A package switch produces release-specific URLs; old in-flight URLs continue serving retained releases. A missing or incompatible personal geometry override uses valid manifest geometry without affecting other characters.
10. Verify builds/publication inputs contain no official packages while retaining the six original built-ins. No-package startup and gameplay perform no artwork acquisition.

Use package-adjacent tests and the existing shard manifest for new non-browser test modules. Follow the synthetic-data rules, focused-run limits, observability lint when logging changes, contract gate, and player-command documentation requirements for any added administrative command surface. Browser acceptance uses one focused local file/class; complete browser/evidence coverage remains CI-owned.

## 13. Delivery boundaries

The design can be decomposed into independently verifiable OpenSpec changes:

1. Package schema, explicit installer, immutable releases, activation, and deployment root.
2. Read-only official catalog, stable preset/NPC content references, media serving, and resolver integration.
3. Personal official-image selections/geometry and gallery read-only presentation.
4. Built-in silhouette payload semantics and the stage SVG replacement; this does not depend on an installed official package and can be implemented independently of package acquisition.

Species-specific monster integration follows the separate monster catalog design. The official package kind is defined here, but a threat-tier alias is not a substitute for that prerequisite. Monster habitat placement, target quantities, guild difficulty, city safety, and quest provisioning are outside this document and remain subject to their own brainstorming and approvals.

No runtime implementation is included in this design-document change. After the user reviews this written specification, use the repository's specification-driven workflow for proposal and implementation planning.
