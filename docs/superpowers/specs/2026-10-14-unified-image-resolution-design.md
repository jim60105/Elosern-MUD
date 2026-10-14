# Unified Image Resolution and Missing-Image Presentation

**Date:** 2026-10-14
**Status:** Written specification approved by the user. Fifteen OpenSpec proposals are filed on the primary branch; their inventory and batch implementation order are recorded in section 11.
**Scope:** Shared artwork resolution, complete built-in scene artwork, room-specific official scenes, and consistent expected-missing and unexpected-failure presentation.

This document records the approved design and its filed proposal set. It does not claim that the implementation or new artwork exists. Implementation proceeds change-by-change through the OpenSpec apply workflow in the section 11 order; each apply is a separate user request.

## 1. Goals and architectural amendments

Artwork availability must not change whether the deterministic game is playable. All display surfaces must distinguish an expected absence from an actual failure, including when a later image or terminal fallback displays successfully.

The approved presentation rules are:

- Character and monster figures use the existing deterministic fallback selection rules and transparent-image alpha silhouettes.
- Avatars use the first Unicode grapheme cluster of the trimmed displayed name when no real portrait can be displayed; avatars never load the figure silhouette.
- Every registered scene type has its own built-in official scene image. The town and forest images are members of that same collection and are also the final image fallbacks.
- Unexpected failures retain an in-place, persistent indication. Expected missing images do not receive an error indication.
- Resolution, loading, and rendering each have one implementation owner. Callers do not recreate these responsibilities.

### 1.1 Amendments to the engine design

This design explicitly amends D10 and section 8 of `2026-07-29-ai-mud-engine-design.md`:

- Generated scene assets remain keyed by archetype. There is no per-room image-generation queue, prompt, or generated-art record.
- A room may explicitly declare a stable official-art reference that overrides its archetype's images.
- Scene resolution includes generated art, optional operator-provided official art, and required repository-bundled official scene art.
- A previous successful image may be retained only within the same scene identity. It must not survive a move to a different scene as that scene's background.

The existing single-writer boundaries, read-only presentation, immutable authored registries, integer age bounds, and offline deterministic gameplay remain unchanged.

### 1.2 Amendments to existing artwork contracts

The current official-art catalog describes external, untracked `monster`, `preset`, and `npc` artwork only. This design adds `scene` and `room` content kinds and a tracked built-in scene collection. The tracked scene collection is an explicit exception to the current prohibition on tracked official artwork blobs; it does not move operator artwork into git.

Optional, unconfigured artwork remains optional. A required built-in file, explicit broken reference, known failed generation, or inaccessible configured source must not become an indistinguishable normal absence. Implementation must revise the affected main specifications through OpenSpec, rather than weakening their tests or treating historical specifications as current authority.

## 2. Confirmed decisions and alternatives

The user approved these decisions:

| Decision | Approved policy |
|---|---|
| Scene fallback selection | Authored scene type, never exploration/dialogue/combat mode |
| Unexpected-failure visibility | Persistent indication at the affected image position; no new central error dashboard |
| Scene sources | Generated scenes, archetype official scenes, and per-room official scenes |
| Source precedence | Room official, archetype generated, archetype official, terminal town/forest |
| Shared architecture | Backend resolver, frontend loading state machine, separate figure/avatar/scene renderers |
| Built-in coverage | All ten current archetypes plus the dream scene receive distinct appropriate scene artwork |
| Existing fallback module | May move or split for SRP; its rules remain authoritative and have no duplicate implementation |

A single multi-mode component was considered. The selected layered approach allows editors to reuse load results without inheriting stage rendering or making a substitute image editable. A global asset store, automatic retry service, new telemetry ingestion endpoint, and unrelated UI redesign are outside scope.

## 3. Responsibility boundaries

### 3.1 Backend resolution

`world/art/` owns the canonical artwork description and ordered source resolution. It reads existing generation and catalog state and performs no queue, gallery, room, or character mutation during presentation.

The existing portrait selection order remains intact. `gallery_fallback.py` supplies the existing declaration, species, sex/apparent-age band, stable-hash, and alpha-image metadata behavior. Its code may be moved or split into focused modules when integrating the common resolver. All callers must migrate together; no old-path re-export, duplicate selector, or compatibility shim remains.

Scene definitions are immutable authored records owned by the art domain. They reference the existing archetype registry and declare their built-in identity and terminal fallback key. Normal archetypes and the explicit dream scene are the complete supported scene-art set. Consumers read those definitions; filename construction and town/forest selection do not recur in presenters or Vue components.

`world/maps/` remains responsible for idempotently applying authored room metadata at startup or room construction. The art resolver only reads that metadata. `world/narrative/` retains ownership of dream lifecycle state; selecting dream artwork does not mutate that lifecycle.

### 3.2 Frontend loading

One shared loading state machine consumes a canonical description, attempts its sources in order, observes actual load/decode results, and retains relevant failures. It has no knowledge of character demographics, map topology, generation scheduling, or game rules.

The state machine receives source changes from the existing panel protocol. It does not create jobs, repair records, fetch a second business-data API, or interpret prose.

### 3.3 Rendering

| Owner | Responsibility |
|---|---|
| Figure renderer | Real portrait, existing placement geometry, alpha silhouette, identity text |
| Avatar renderer | Real portrait face crop or name initial |
| Scene renderer | Background composition, same-scene transition, full-view rendering |
| Shared failure indicator | Persistent local indication and an accessible explanation of unexpected failures |
| Editor | Editing geometry and save eligibility based on successful original-image loading |

A renderer consumes load state. It does not maintain a second failed-URL flag, select another artwork source, or classify generation failures independently.

## 4. Canonical artwork contract

The descriptor carries these independent concepts:

| Concept | Meaning |
|---|---|
| Subject identity | Stable identity of the person, scene, or explicitly requested gallery image |
| Source revision | Identity/version of the ordered source description, including media fingerprints |
| Generation state | Truthful `missing`, `pending`, `done`, `failed`, or no generation state; normalize the existing in-progress wire form as today |
| Ordered source attempts | Admitted real-image candidates and known-fault entries at their original precedence positions |
| Terminal fallback | Figure alpha-mask reference, scene town/forest reference, or no image fallback for an original-image editor |

An image candidate carries its stable identity, same-origin URL, origin, and applicable geometry. A known-fault entry carries a bounded reason code and the failed source identity, without an image URL. Optional sources that were never configured contribute no fault entry.

Known-fault entries preserve precedence. The frontend accumulates a fault only when it reaches that entry. A healthy higher-priority room image therefore hides unrelated lower-priority job failures. If a preferred source is broken and a lower-priority image works, the preferred source's fault remains visible.

The descriptor distinguishes real image origin from generation state. An official image can be visible while a generation job is pending or failed. A silhouette never changes the job to `done`, creates an asset record, or claims to be generated artwork.

### 4.1 Shared references and access control

Roster, party, exploration, dialogue, combat, and drawer surfaces reference canonical entries with the complete descriptor. Remove roster field-copy omissions and the party/exploration rule that emits a reference only when a real image exists.

Build the catalog from subjects already authorized for the current views. Consolidation does not enumerate undiscovered NPCs, unknown locations, or another owner's private records. An unavailable panel is an unexpected availability failure, not a synthetic pending-generation state.

Gallery cards and official gallery entries identify the exact requested image. Their previews may use the subject's silhouette after failure; their editors must not silently switch to a different gallery card or scene image.

### 4.2 Protocol cutover

Update backend serialization, schema versions, active client validators, references, and all production consumers in the same cutover. Do not support the old and new shapes indefinitely. Keep the existing bounded URL and protocol-validation rules; do not bypass validation to accommodate new scene sources.

## 5. Expected absence and unexpected failure

| Condition | Classification | Result |
|---|---|---|
| No generated record yet | Expected | Normal fallback; no error marker |
| Queued or generating | Expected | Normal fallback; an optional factual progress explanation, without error styling |
| Generation explicitly disabled, with no independent asset fault | Expected | Normal fallback; never claim generation is underway |
| Optional official source not declared or provided | Expected | Continue to the next source |
| Ordinary image request still loading | Expected transient state | Show available fallback without prematurely announcing failure |
| Generation job reports failure | Unexpected if reached | Retain job failure while displaying the next source |
| A completed generated record names a missing/invalid output | Unexpected if reached | Retain failure and continue |
| Explicit room binding cannot resolve, or configured artwork is rejected/unreadable | Unexpected if reached | Retain failure and continue |
| Required bundled scene or silhouette cannot be loaded | Unexpected | Retain failure and attempt only a distinct permitted terminal fallback |
| Browser load/decode failure | Unexpected | Retain failure and continue |
| Backend panel/service cannot provide its image data | Unexpected | Retain matching last-known content where safe, or use a safe fallback, with a local availability indication |

A deliberately absent optional official root remains a valid offline configuration. An explicit binding to missing artwork, or a reported I/O/admission error, must remain distinguishable from that absence. The startup snapshot must retain the bounded health/rejection facts needed to make this distinction; a general empty catalog must not erase them.

An absent default optional root without explicit bindings is normal. An explicitly configured unavailable root, an unreadable root, and an unresolved explicit binding contribute a fault when that source layer is reached. Preserve configuration and failure facts at startup rather than guessing from an empty result during resolution.

Attribute catalog faults to the requested source. A missing or rejected manifest-declared default contributes a fault before that directory's deterministic substitute. Malformed manifest data or invalid geometry applicable to the selected source contributes a metadata fault while using safe geometry. Rejected unselected sibling files remain operational diagnostics and do not taint a healthy selected image. A directory-wide refusal count cannot substitute for these source-scoped facts.

Disabling generation does not retroactively reclassify a recorded failed job or a missing required static file as healthy.

### 5.1 Visibility and clearing

Unexpected failures have a persistent, non-modal indication at the image position, including after a successful fallback. A small avatar may use a compact marker, but its explanation must be available to keyboard and assistive-technology users, not only pointer hover. Do not rely on color alone.

Player messages describe the failure category without filesystem roots, credentials, raw exceptions, or internal prose. Do not display normal expected absence as a system error. Exact wording belongs to the renderer's shared message mapping, not each caller.

For a given descriptor version, a successful lower-priority image does not clear earlier faults. New subject/source revisions recompute the applicable attempts; a repaired source can clear its fault after a successful new load. Re-rendering an unchanged descriptor must not reset it. Page reload also starts a fresh attempt. There is no automatic timer-based retry loop or permanent application-wide negative cache.

### 5.2 Diagnostics

Retain backend boundary diagnostics through named imports from `world.observability`, with business identifiers in `context`. Resolution failures and successful fallback use must remain distinguishable. Browser-only failures are visible locally; this design does not add a telemetry transport or claim that a browser event was logged by the backend.

## 6. Scene sources and built-in artwork

### 6.1 Normal scene precedence

The ordered attempts are:

1. Explicit room-specific operator official artwork.
2. Archetype generated artwork, using the existing shared generated subject.
3. Archetype operator official artwork, when provided.
4. That scene type's required built-in official artwork.
5. Its declared town/forest terminal image, if distinct from an already attempted resource.
6. A non-image background with the persistent local failure indication.

Items 3 and 4 together implement the approved archetype-official layer. The built-in source is present without an operator directory or generator. A corrupt optional override is still a fault when reached; a healthy bundled image does not erase it.

### 6.2 Built-in scene inventory

The following keys are required. Terminal fallback choices are explicit authored defaults, subject to written-spec review.

| Scene-art key | Content | Terminal image key |
|---|---|---|
| `forest_path` | Forest path | `forest_path` |
| `tavern_interior` | Tavern interior | `city_street` |
| `dungeon_interior` | Dungeon interior | `forest_path` |
| `city_street` | Town/city street | `city_street` |
| `wilderness_path` | Wilderness path | `forest_path` |
| `mountain_path` | Mountain path | `forest_path` |
| `ruin_interior` | Ruined interior | `forest_path` |
| `coastal_path` | Coastal path | `forest_path` |
| `cave_interior` | Cave interior | `forest_path` |
| `shrine_interior` | Shrine interior | `city_street` |
| `dream_throne` | Dream cloud-throne scene | `city_street` |

Deliver real, scene-appropriate images for all eleven keys. Reusing the town and forest files under different type names does not satisfy coverage. The current town and forest sample images may be retained as the corresponding two official images after checking content, provenance, and format; remove their separate sample-only copies and CSS usage.

Use tracked WebP assets under `web/static/art/scenes/`, with full-bleed landscape composition appropriate to the desktop 16:9 client. Assets must decode within existing image resource limits. Record source/licensing and production provenance with the delivered assets. No art service, external mount, startup download, or runtime generation is required to display this collection.

A future normal archetype must add its scene-art definition and required artwork in the same change. Contract checks reject missing definitions, missing/undecodable required images, invalid terminal references, and attempts to reference an unregistered key. Runtime still degrades visibly if deployment loses one of these validated files.

### 6.3 Official catalog and serving

Extend the existing external official layout with `scene/<scene-key>/<image-file>` and `room/<room-art-key>/<image-file>`. Scene keys and authored room-art keys are registry-validated; no directory key is a database row ID or translated room name. Continue the existing optional per-content manifest and deterministic default selection rules.

Index operator art at startup and retain content fingerprints. Index required bundled scenes through the same art-domain admission and media-serving primitives, with a separate trusted root and a closed built-in identity namespace. Do not route a bundled request through an operator-controlled root or let an operator file replace the terminal built-in image. Bundled and operator identities must not collide.

Serve built-in scene identities from the existing `web/art_media.py` boundary using a closed scene-key allowlist and content fingerprint. Refactor common safe opening/decoding/response primitives where needed; do not copy the media handler. Preserve same-origin URLs, root confinement, no-follow behavior, and per-entry failure isolation. A media request still returns an actual 404 on missing data, not a substitute image with a successful status.

The game never writes `ART_OFFICIAL_ROOT`. No new runtime setting is required for the repository-bundled root. Operator artwork replacement retains the existing restart/snapshot semantics.

### 6.4 Room identities and metadata

A source-authored `room_art_key` is optional metadata, synchronized by the existing map owner for authored grid rooms and permanent interiors. Supported room construction may carry an explicitly authored key for an instance. Dynamically generated rooms without such a declaration simply use their archetype chain.

The key references registered authored artwork content; it is not inferred from a room name, runtime primary key, monster tier, or nearby location. Wilderness room objects are pooled. Obtain current logical-place metadata during preparation and clear a previous place's key when it does not apply. An old object's key must never leak into another coordinate.

Scenes lacking a valid archetype and an explicit supported scene definition use the town terminal image with a configuration-failure indication. Do not quietly classify malformed scene metadata as normal generation absence. Updating authored rooms to valid scene metadata is part of implementation, including permanent interiors that currently use plain `Room`.

### 6.5 Dream scenes

The dream uses the explicit `dream_throne` scene-art definition. Preserve the existing optional official identity `npc/dream_goddess/dream-throne.webp` as its scene-specific preferred source, avoiding an unnecessary operator-file move. Its next normal source is the bundled dream image, then the town terminal image. It does not enqueue a new physical-room or archetype generation job and does not inherit the sleeper's location background.

Replace the dream panel's raw artwork-URL-only presentation with the same canonical descriptor and shared scene loading mechanism. Narrative lifecycle and dialogue ownership remain unchanged.

## 7. Loading and rendering behavior

### 7.1 Shared attempt lifecycle

The state machine processes ordered attempts until an image succeeds. It collects reached backend fault entries and browser load/decode failures. Deduplicate resource attempts by canonical resource identity/version, including a terminal image already attempted as the type image.

A successful image is displayed with all preceding relevant faults. A later candidate that was never reached has no effect. If no real image succeeds, activate the renderer's permitted terminal fallback. Exhaustion ends in text or a non-image background, never a broken `<img>` or a recursive fallback loop.

The scene renderer may request its own bundled/terminal background provisionally while higher-priority sources load. A provisional success cannot stop or win the ordered resolution. Its failure remains latent unless resolution reaches that source's precedence position; it does not mark a subsequently successful higher source as faulty. The shared mechanism reuses the provisional resource result if that position is reached, with no duplicate attempt.

Associate callbacks with the active subject, descriptor revision, and attempt. Ignore load/error callbacks from superseded attempts. Dispose component listeners and temporary resources on replacement/unmount. The browser's normal image cache remains available; this design adds no global loading cache or duplicate framework.

The silhouette's resource must also report success or failure through the shared mechanism. An absent alpha image must not become an opaque rectangular fill. Rendering a mask and observing its resource must share the same canonical URL and result.

### 7.2 Figures and avatars

Stage figures, drawer figures, dialogue actors, exploration focus, companions, and monsters all use the same figure renderer. The existing stage-versus-cover split may control layout but must not disable the required silhouette policy for a figure surface.

Preserve the existing fallback key vocabulary and selection semantics, including the monster fallback and stable demographic selection. Preserve true portrait geometry separately from silhouette geometry.

An avatar first tries the real-image attempts applicable to its subject, with face geometry from the actual successful image. Otherwise it displays the first Unicode grapheme cluster of the trimmed name, with a neutral text symbol for an empty name. The common text-initial helper must not expose an isolated Unicode surrogate or split a combining sequence. It does not attempt alpha silhouettes or change generation state.

### 7.3 Scenes and full-view behavior

A new scene identity immediately invalidates the old scene's retained background. During loading, show the new scene's own built-in/terminal background. Mode changes alone do not change the selected artwork.

Retained display content is separate from the current attempt chain. During regeneration of the same scene and generation subject, retain the previous successfully loaded image until a replacement at the same or a higher source priority succeeds. A lower-priority official/bundled fallback does not displace that retained good generated image merely because it loads first. Continue resolving the new descriptor and processing its reached fault entries while retained content is visible. Pending regeneration has no error marker, and failed regeneration retains its error marker even when a bundled fallback is healthy.

Retention does not override an explicit binding removal, revoked access, or a different subject/scene identity. Those changes invalidate the retained source and use the new applicable chain. Do not retain an image already known to have failed. A fresh page has no retained in-memory success and follows normal precedence.

Full-view rendering consumes the same successful source and failure state. It must not create a second error-handling implementation or open a view containing only a broken image. The scene renderer no longer relies on sample-background pseudo-elements in `app-shell.css`.

### 7.4 Gallery and editing surfaces

Migrate gallery card thumbnails, official rows, detail rails, binding references, generation references, face-rectangle editing, and stage-transform editing to the shared load mechanism. Waiting/failed card status remains truthful and separate from whether a display fallback is available.

Only a successfully decoded original image with usable dimensions can enable crop or placement saving. A silhouette, a different card, a scene fallback, or the fixed adult-size reference must never become the edit target. The fixed adult reference remains an editing ruler, not subject artwork, and its resource failure is also explicit.

Loading and failed-original states have distinct explanations. Remove broken original `<img>` elements on failure. A successful new original source can restore eligibility; a harmless re-render cannot manufacture successful dimensions.

## 8. Consumer cutover and excluded work

The cutover covers player/party/focus/dialogue/combat figures; roster, presence, party, and participant avatars; ordinary and dream backgrounds; scene full view; and gallery/editor previews.

Keep active protocol validators and update them for the new contract. Remove obsolete per-component failure caches, duplicated source selection, CSS sample backgrounds, and code made dead by the cutover. Remove unused legacy artwork code only after establishing that no production consumer remains; do not remove unrelated protocol modules merely because their directory also contains old renderers.

The GM artwork pages currently provide links/status rather than image previews. Do not add a new preview feature. Text clients remain text-only. Static favicons, unrelated SVG icons, gameplay rules, player commands, generation scheduling, and an operator hot-reload mechanism are outside scope.

No player command syntax, alias, or availability changes are planned. Command documentation remains unchanged unless an implementation proposal explicitly introduces a command-surface change.

## 9. Verification and acceptance

| Boundary | Required observable result |
|---|---|
| Fresh data, external services deliberately disabled | Every figure has the correct silhouette, every missing avatar has a name initial, and every supported scene has appropriate bundled art without an error marker |
| Room, generated, operator-type, and built-in images coexist | The approved precedence selects the correct image; unused lower faults are invisible |
| Catalog default/reference faults and unrelated rejections | A broken explicit default remains visible through deterministic substitution; an unselected rejected sibling does not taint the selected image |
| Optional and unavailable roots | An absent default optional root is normal; a reached explicitly configured unavailable/unreadable root remains a fault |
| A selected completed file disappears | The next source displays with a persistent failure indication; generation state remains unchanged |
| Browser 404 or decode error | The shared state machine advances and retains the reason; no broken image remains |
| Higher source fails and a lower image succeeds | The local error remains until a relevant new successful version, subject change, or fresh-page attempt |
| Required type image fails | A distinct town/forest image is tried once; if the terminal is the same failed resource, skip it immediately; exhaustion ends in a non-image background with explicit failure |
| Alpha fallback fails | Identity text remains; no rectangular substitute or unhandled broken image |
| Rapid subject/source changes | Stale completion and error events cannot overwrite the active subject |
| Scene movement and pooled wilderness objects | Neither a prior background nor a prior room-art key leaks to the new logical place |
| Same-scene pending and failed regeneration | An existing good generated image remains despite a healthy lower bundled image; pending has no error, failure is visible, and a successful same/higher-priority replacement can take over |
| Provisional background fails while a room image is delayed | Room-image resolution continues; a healthy room image wins without an unrelated lower-priority error, and a later reached provisional result is reused |
| Original editor image fails | Saving stays disabled and substitute content is never persisted as original geometry |
| Built-in coverage changes | Missing/invalid assets and metadata identify the affected scene type in the contract check |
| Read-only resolution | No queue, gallery, room, or generation-status mutation occurs |

Use focused pure-logic tests for classification, source order, state transitions, duplicate attempts, and stale events. Use Evennia integration tests for canonical descriptor references, authored room metadata, catalog rejection facts, and read-only resolution. Use real browser error interception/invalid media to exercise the shared runtime paths.

Asset checks must validate decodability, resource bounds, required key coverage, and declared references. Visually inspect all eleven scene images for scene identity and composition; metadata checks alone cannot establish artwork appropriateness. Do not replace the required artwork with placeholder files or use balance/data-echo tests as acceptance evidence.

Run a representative live-client smoke covering exploration, dialogue, combat, avatars, a room-specific override, dream, full-view behavior, and a failed-original editor. Include a same-scene update, a different-scene move, and source failure after server resolution. Run only focused local browser batches; CI owns the complete browser suite and aggregate evidence verification.

Update test shard ownership, traceability claims, active specifications, and affected development documentation in each owning implementation change. Keep branch-coverage and observability gates intact. Main specification changes go through the normal OpenSpec proposal/apply/archive workflow.

## 10. Delivery boundaries

This is one cross-surface policy design. The implementation plan may split dependent OpenSpec changes into the complete scene assets and scene catalog extension, canonical backend descriptions, shared frontend loading/rendering, and final consumer cutover with evidence. Shared interfaces and integration order must be set before parallel implementation.

The feature is complete only when the eleven actual scene artworks, per-room official resolution, all production consumers, fault visibility, and the acceptance evidence are delivered. A shared component without migrated callers, a type registry without artwork, or a silent fallback that hides failures is not completion.

The written specification was reviewed and approved by the user. The user explicitly requested OpenSpec proposals, each strictly below eight engineer-hours, with focused test commands in tasks.md. The repository `openspec-propose` workflow replaces the unavailable `writing-plans` step for this handoff. The proposals contain planning artifacts only; implementation requires a separate OpenSpec apply request.

## 11. Filed proposal inventory and batch implementation order

Fifteen OpenSpec proposals implementing this design are filed on the primary branch under `openspec/changes/<id>/` (planning artifacts only; none is applied). Every estimate includes implementation, assets, tests, smoke, docs, and gates, and stays strictly below eight engineer-hours. `tasks.md` in each change names the exact focused test commands, actual-surface smoke steps, registration/doc obligations, and objective success conditions for its work.

| ID | Change | Scope | Est. h | Depends on |
|---|---|---|---:|---|
| A | `unified-scenes-outdoor-art` | Three outdoor scene images; owns the tracked built-in artwork contract exception and the reusable image gate | 7.00 | none |
| B | `unified-scenes-interior-art` | Tavern, dungeon, ruin images and provenance | 6.50 | A |
| C | `unified-scenes-sacred-art` | Cave, shrine, dream images and provenance | 6.50 | A |
| D | `unified-scenes-terminal-art` | Town and forest canonical terminal images plus provenance | 4.75 | A |
| E | `unified-scene-catalog` | Eleven scene definitions, registry contract, operator scene/room catalog, bundled media, sample retirement | 7.25 | A, B, C, D |
| F | `unified-art-source-faults` | Attributed source faults, catalog health facts, malformed-metadata facts, safe geometry | 5.75 | E |
| G | `unified-image-loading-core` | Shared ordered-attempt state machine; first integration in the face-rect editor | 7.50 | none |
| H | `unified-gallery-image-contract` | Canonical descriptor, gallery wire migration, card/detail previews | 6.50 | F, G |
| I | `unified-gallery-original-editors` | Original-only edit eligibility, transform editor, reference-ruler fault | 5.50 | G, H |
| J | `unified-portrait-source-resolution` | Backend portrait source enumeration, silhouette integration, faults | 6.50 | H |
| K | `unified-portrait-image-contract` | Portrait wire, authorized full references, all figure cutovers | 7.50 | J |
| L | `unified-avatar-rendering` | Shared avatar, grapheme initial, localized unexpected-failure indication | 5.25 | K |
| M | `unified-room-art-metadata` | Room-art identity contract, permanent interiors, pooled-wilderness clearing | 6.25 | E |
| N | `unified-scene-rendering` | Scene selection, retention, provisional background, full view, mode CSS removal | 7.50 | K, M |
| O | `unified-dream-rendering` | Dream wire and shared scene presentation | 4.75 | N |

### 11.1 Batch implementation order

Apply wave by wave; a change may start once every dependency is archived with synced main specs. Within a wave, changes are independent and may run in parallel, subject to the shared-file conflicts below.

```text
Wave 1:  A  G            (no dependencies; parallel-safe: disjoint files)
Wave 2:  B  C  D         (all follow A; parallel-safe with each other)
Wave 3:  E               (needs the full eleven-image inventory)
Wave 4:  F  M            (both follow E; parallel-safe: disjoint files)
Wave 5:  H               (joins backend faults and the frontend core)
Wave 6:  I  J            (both follow H; parallel-safe: disjoint files)
Wave 7:  K               (portrait wire and figure cutovers)
Wave 8:  L  N            (L follows K; N follows K and M; parallel-safe: disjoint tests)
Wave 9:  O               (dream cutover after the scene renderer)
```

Total planned effort is 92 engineer-hours. The design is complete only after all fifteen changes are applied and archived; no change may be skipped as "optional polish".

### 11.2 Shared-file integration conflicts

Parallel waves assume disjoint files only when stated. These paths are shared integration surfaces, coordinated by the change that owns them:

| Path | Owners (in order) |
|---|---|
| Image asset/data tests and `.github/evennia-shards.json` | A introduces; B, C, D, E extend |
| `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md` | A records the tracked exception; E records the operator scene layout |
| Official catalog and `web/art_media.py` | E owns layout/serving extensions; F adds health/reference facts |
| `web/webclient-app/components/image-loading.js` | G owns the state machine; K and N extend the contract |
| Gallery wire modules, `GalleryPanel.vue`, Node gate | H owns the gallery contract migration |
| Portrait wire and `web/webclient/presentation` | J prepares backend sources; K cuts the wire over |
| Shared failure indicator | L owns the compact indicator component |
| `tests/test_webclient_frozen_contract.py` | Each active wire migration updates it; G and H already touch it |
| Development docs | E, H, J, K, L, M record their respective boundaries |

When two same-wave changes must touch the same registration file, serialize them in the listed owner order rather than merging concurrent edits.
