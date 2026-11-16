# Design

## Context

See proposal.md for motivation. This is one single-repository change, bounded to one engineer-day (about seven hours including focused verification). It changes selection and automatic scheduling, not image production.

Observed ownership and failure evidence:

| Evidence | Consequence |
| --- | --- |
| `world/art/gallery_kinds.py:58-151,217-257` | Immutable, import-free declarations already own bindings, age, caps and geometry. Extend this convention. |
| `world/art/gallery_match.py:218-264,471-507,520-568` | Shared selection currently stops after binding/personal/default slots; official references require entity provenance. |
| `world/art/service.py:144-168,183-212,488-512` | Startup passes bare registry subjects while the official guard delegates to the entity-only reference resolver. |
| `world/art/official_refs.py:103-110,225-240,337-364` | Reference vocabulary lacks scene; characters must keep authored preset/NPC provenance. |
| `world/art/official.py:152-158` | The loader already accepts scene/room layout separately from the narrower personal-content vocabulary. |
| `world/art/presenter.py:450-576,894-987,1024-1120` | Portrait and scene presenters independently compose source priority; scene retention uses immutable gallery identities. |
| `web/webclient/actions/gallery_actions.py:389,551-555` | Scene actions currently resolve without an entity and explicitly refuse official preference state. |
| `docs/development/official-artwork-deployment.md:111-162,244-269` | Deployment documentation still describes two source chains and classic scene output URLs. |

The reported fresh-database observation (scene and monster jobs despite official monster artwork, all gallery defaults set) is accepted runtime evidence, not a content-count acceptance fixture.

## Goals / Non-Goals

The shared subject chain owns priority, official identity lookup, fault attribution and automatic satisfaction. Capabilities own every difference between subject kinds. Reusable species and scene identities never become runtime entity identifiers.

Non-goals are classic retirement, queue/storage redesign, new artwork, changing portrait demographics, room metadata writers, browser loading architecture, dream lifecycle, command syntax, hot reload, data migration and compatibility layers. The sibling retirement change removes the temporarily retained classic slot.

## Decisions

### D1. Extend data declarations, not kind branches

Add immutable closed-value fields to `GalleryKindCapabilities`, its `with_values`, representation and declaration validation:

| Field | Character | Monster | Scene |
| --- | --- | --- | --- |
| `official_reference_policy` | `entity_provenance` | `visual_species` | `scene_archetype` |
| `official_preference_scope` | `subject` | `entity` | `subject` |
| `terminal_policy` | `alpha` | `alpha` | `scene` |
| `supports_classic_source` (temporary existing read policy) | `True` | `True` | `False` |

Gallery-less declarations use `none` for the string policies and false for classic support. The temporary classic flag preserves the already-removed scene classic fallback; it introduces no new legacy read. Retirement removes this flag and slot together. Existing support flags continue to gate bindings, ages and geometry. The table imports nothing, contains no registry objects or callables, and remains exhaustive over `ArtSubjectKind`. Runtime adapters dispatch on closed policy values, never comparisons to `ArtSubjectKind` or its literals. Registry producers may validate their own kind; that is subject construction, not a second selection policy.

### D2. One reference resolver serves presentation and suppression

Add `official_content_reference_for_subject(subject, entity=None)` in `official_refs.py`. Revalidate scene/species through existing typed producers, then derive `scene/<key>` or `monster/<key>` from the registered subject key. For `entity_provenance`, delegate to the existing resolver, keeping preset then NPC provenance and its refusal behavior. Never infer a character's reference from a numeric id, display name or stable key.

Add scene to `OFFICIAL_CONTENT_KINDS` in both official modules and `_registry_for`, using `SCENE_ARCHETYPE_REGISTRY`. `OFFICIAL_LAYOUT_KINDS` must contain scene once and keep room separately. Room catalog membership remains authored room-art membership; no room subject kind or generated room job is introduced. Update `_official_default_satisfies`, official selection/default slots, official gallery rows and action admission to use this resolver. Keep one bounded provenance diagnostic per failure and snapshot-only lookup after startup.

Only a presentable admitted operator catalog default satisfies automatic generation. Required bundled scene art is a terminal source, not an operator catalog default. A broken manifest default with a valid deterministic substitute satisfies the guard, while its attributed fault remains visible when reached. Empty/refused content without a valid substitute does not satisfy it.

### D3. Move priority into one subject enumeration

Extend `gallery_match.resolve_display_chain(subject, entity=None)` into the one ordered subject-slot enumerator. Move classic lookup/attempt construction out of the portrait-specific selector into the shared slot owner without adding a classic writer. Its slot order is binding, personal official selection, default card, temporary classic source only where declared, official default and declared terminal. Preserve existing specificity/newest tie-break and unbound-card eligibility. Scenes never regain a classic source.

The common enumeration emits ordered candidates/faults from one snapshot of cards/preferences. `resolve_display` remains a first-presentable projection. Canonical presenters project the same ordering into existing descriptor shapes, preserving source ids/ranks for existing positions. Faults remain at their own position; the shared browser loader reaches lower faults only if higher images fail. Extend bounded source budgets if the existing canonical validator requires it, without widening URLs or admitting a second wire shape.

`presenter._enumerate_portrait` and `describe_scene` become projections of these slots, with declared geometry/terminal adapters. Remove `_scene_gallery_card` as an independent default selector; retain shared card validation. Scene projection keeps the authored room override before the shared archetype chain and required bundled/terminal deduplication after operator defaults. This is an outer authored-room envelope, not a different subject policy. No scene-specific selector remains in the gallery read model.

### D4. Preserve ownership and deliberate choices

Characters retain subject-record preferences. Monster selections stay entity-local and never change the species gallery. Scene official selection lives in the archetype's gallery record and applies to rooms sharing that archetype; no per-room or per-account preference store is added.

Generation append, including first-card and capped replacement, never clears an explicit official selection. Only an explicit runtime-default action clears that same owner's selection. For a character, selecting official may clear the runtime default as today; clearing official does not manufacture a default. For shared scene/monster galleries, selecting official does not erase the shared generated card/default. Scene geometry operations remain refused because its declaration permits neither face rectangle nor stage.

Route existing official select/clear and gallery presentation through capability scope in `gallery.py`, `web/webclient/actions/gallery_actions.py` and `web/webclient/presentation/gallery.py`. Keep the existing authorization decision for which scene/portrait subjects the actor may manage. Direct unadmitted requests remain rejected.

### D5. Scheduling stays a guarded workflow

Keep `_guarded_gallery_request` as the shared automatic guard. Check declared eligibility before official satisfaction; check cards/in-flight state and intentional scene deletion through existing guard state. Both startup and room-entry paths consume the same declared reference policy. Manual `request_gallery_image` and staff force requeue bypass only automatic satisfaction, never age, capability, authorization or typed-key validation.

Automatic suppression creates no gallery state, image id, prompt or job. Preserve `transaction.on_commit` and failure isolation at creation/import/spawn boundaries. There is no retroactive rewrite of existing defaults or generated cards and no automatic cancellation of jobs already queued.

### D6. Operational events

Retain `official_art_catalog_loaded`, `gallery_generate`, `gallery_settle`, `sd_job_claim`, `sd_job_settled` and `gallery_fallback_used` through named imports from `world.observability`. Add one `art_auto_generation_suppressed` info boundary event with `subject`, `kind`, `reference` and bounded `reason=official_default` when the new registry path suppresses a request. It records no root, prompt or credentials. Do not add per-render success logging or a second fallback event.

## Policy review

This named review section is human-reviewed for policy consistency, not an executable tone or artwork-fidelity requirement. The explicit user request supersedes the separate-subject selection implementation while retaining the approved authored room override and offline scene terminals. During implementation amend `docs/superpowers/specs/2026-10-14-unified-image-resolution-design.md` sections 3.1, 6.1 and 6.3 and the D10 amendment reference in the engine design to describe the shared archetype chain and scene preference ownership. Dream's separate exact NPC image remains outside archetype generation. No visual review or shipped copy pinning is needed.

## Sequencing and conflict matrix

| Change | Dependency | Shared specification blocks | Code conflicts | Apply / archive order |
| --- | --- | --- | --- | --- |
| unify-artwork-selection | none | Defines shared chain, terminals, references, preference preservation | gallery_match, presenter, service, gallery, related tests | first / first |
| retire-classic-art-assets | unify-artwork-selection | Replaces shared-chain requirement and automatic-default requirement; modifies common model/generation/fault/official/fallback blocks | presenter, service, queue consumers and overlapping tests | second / second |

Retirement's deltas are composed with the new scenarios here. After this change synchronizes, retirement must resolve its full blocks against the new main specs and retain every non-classic scenario. Never archive retirement first. Neither plan depends on a sibling's implementation files before its authorized apply.

The exact shared requirement blocks are:

| Capability | Requirement | Retirement operation |
| --- | --- | --- |
| art-gallery-autogen | Automatic character portraits produce exactly one unbound default card | remove and replace with gallery-only publication |
| art-gallery-resolution | Display resolution is one deterministic chain from equipment to fallback | remove and replace without classic slot |
| art-gallery-resolution | Monster subjects resolve through the chain without the binding steps | remove and replace without classic scenario |
| art-gallery-kind-capabilities | One closed declaration states what every subject kind's gallery may do | remove temporary classic policy field |
| official-art-resolution | The extended chain stays deterministic, offline, and side-effect-free | remove classic examples, preserve preference ownership |
| art-gallery-model | One gallery record per art subject carries an ordered card list and a default | remove classic reference, preserve scene lazy creation |
| art-gallery-fallback | The fallback seam supplies a URL and a face rectangle and reports its use | replace classic-free terminal contract |
| art-gallery-generation | One validated service seam requests every gallery image | remove classic enqueue analogy |
| art-source-fault-facts | Faults are attributed to requested sources | exclude retired sources |
| art-asset-lifecycle | Startup recovery rescans explicit unique portrait policies | relocate guarded recovery to gallery-autogen |
| art-asset-lifecycle | Successful player creation and validated import schedule an eligible unique portrait through transaction.on_commit | relocate guarded scheduling to gallery-autogen |
| art-asset-lifecycle | Every player-activation path finalizes the portrait lifecycle | relocate guarded transport parity to gallery-autogen |

## Risks / Trade-offs

Changing scene preferences is shared-archetype behavior, so action admission and UI state must say which subject is affected. Retention must authorize the selected shared source and revoke it when a selection/default changes, while preserving a prior generated card during pending/failed replacement. A catalog default that cannot produce an admitted bounded URL must not suppress generation. Keeping portrait and scene projections without a shared enumerator would preserve the defect and is rejected. Inferring provenance or generating a card as an official-art proxy is also rejected.

## Test strategy and acceptance

Use synthetic scene/species registries, synthetic preset/NPC provenance, temporary catalog/store roots, tiny decoded fixture images and the fake image client. No shipped registry rosters, artwork counts, names, copy or markup are assertions.

Extend existing `test_gallery_kinds.py`, `test_official_refs_provenance.py`, `test_official_catalog.py`, `test_gallery_match.py`, `test_scene_resolution.py`, service request/autogen tests, gallery action/presentation tests and observability tests. Redeclare a kind's policies to prove behavior follows declarations without code edits. Exercise bare startup subjects, valid and refused official defaults, manual generation, explicit selection surviving successful/failed replacement, no writes during reads and scene/monster one-card cleanup.

Focused commands and traceability ownership are in tasks.md. Expected completion is the same source selection and fault order across kinds, zero new state for official-satisfied automatic requests, and one immutable replacement card for capped subjects. No open scope questions remain.
