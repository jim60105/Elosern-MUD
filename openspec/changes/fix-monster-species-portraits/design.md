# Design

## Context

See proposal.md for motivation. Planning inspected the engine design, main art/species/gallery contracts and five active changes. `resolve_entity` dispatches from `threat_tier`; `monster_subject_for` only admits `MONSTER_TIER_REGISTRY`. Personal cards, personal official selection and classic tier assets precede the official species default. `gallery_subjects` reserves rail capacity for all tiers. Startup requests one card for each tier. `test_species_portrait_identity.py` explicitly documents shared personal records for individuals in the same tier. These are conflicting contracts to replace.

The baseline wilderness model selects a translated example by coordinate hash and `_spawn` writes only the tier. The current complete combat-species registry contains no goblin. Ambient species population already constructs registered species individuals separately. The reported live goblin's attributes and the OOB envelopes were not inspected. The companion publication proposal records the confirmed missing `art` affected-panel declaration without claiming it is the only live timing cause.

## Goals / Non-Goals

**Goals:** Preserve species-specific runtime and official image workflows with deterministic offline degradation. Keep every presentation read pure, all gallery/preferences writes in the art owner, all population writes in its current owner, and combat stats unchanged.

**Non-Goals:** No new combat species/profile, gameplay mechanic, content migration, tier compatibility aliases or redesigned gallery layout. Character art and scene reuse retain their current behavior.

## Decisions

### D1. A visual species registry is the art membership authority

Add a dependency-light `world/lore/monster_visuals.py` holding frozen visual declarations. Adapt each existing combat-species row's stable key, public display label and `published_appearance_zh` through a pure adapter. The visual projection reads no hidden truth, ecology, numeric profile, skills or variant name. Add art-only base-population declarations with explicit stable keys and the existing example labels. Their prompt appearance is the existing generic creature category, without invented biology. Declare the following ordered keys beside the existing ordered examples, preserving selection order:

| Balance band used by population | Ordered visual keys | Existing labels retained |
| --- | --- | --- |
| low | slime, goblin, giant_rat | the existing three low-tier examples |
| mid | wolf_beast, ogre, earth_dragon | the existing three mid-tier examples |
| high | two_headed_dragon, magical_creature, troll | the existing three high-tier examples |
| calamity | ancient_dragon, demon_god, calamity_beast | the existing three calamity examples |

These are explicit authored visual identities. The population selects an authored row by its existing hash; it never takes a name and looks up a species. A band controls spawning/balance only and cannot itself address artwork. No threat-tier string is a visual key. Validate stable-key grammar, duplicate visual keys and reference closure with the existing pure registry-validation and synthetic-registry patterns. A key collision between an art-only row and a complete species is an authoring error, not precedence-based guessing. Compose the projection at the consumer seam so scoped test registries and resource-skill data changes are observed; do not cache imported species objects into a frozen merged snapshot.

`MonsterPopulation` gains `art_species_key`, selected with the label from the same authored row. `_spawn` persists it through an explicit monster visual-identity writer in the existing population transaction. The monster has a separate `art_species_key` attribute; it gains no combat `species_key` or `variant_key`. The matching predicate includes declared art provenance so normal existing marker-owned reconciliation can replace an identity-drifted base monster; no startup backfill or data migration is added. Foreign monsters remain untouched. All old density, tier, label ordering, hashing, ownership, innate readiness and numeric initialization remain byte-equivalent in behavior.

For a complete species individual, `species_key` is authoritative. Only when it is absent may a declared `art_species_key` resolve from the art-only rows. An invalid declared complete species is rejected without falling back to another identity. Neither field is derived from display name, tier, variant, coordinate or catalog contents. Missing, malformed or unknown provenance yields no art subject and the server-authored `monster_anon` fallback, without writes. This small art-only projection avoids fabricating profiles and skills merely to show an image.

### D2. Replace the tier subject vocabulary across every seam

`monster_subject_for` accepts a registered visual species key and returns `portrait:monster:<visual-key>`. Replace both `world/rules/art_view.py::_classify_subject` and `presenter.resolve_entity` tier-based dispatch with the existing explicit `Monster` typeclass check, using local imports to preserve current module boundaries, then derive visual provenance. Neither classifier uses tier validity or a display-name heuristic. This matters for malformed tiers and missing species, which still require a monster silhouette.

The same membership check governs service resolution, startup, prompt rendering, queue ensure/requeue/claim, gallery reads and writes, seed admission, presenter identity validation and media admission. Parsing remains grammar-only; parsed subjects still undergo visual membership revalidation at semantic entry points. A directly constructed forged tier subject is refused too. Retired tier jobs cannot drain into new cards. Retired tier gallery files and classic records are never read, served, selected, retried or applied, even when they remain on an unreleased developer filesystem. Reject them using current membership, with no tier-specific alias or silent conversion. Keep secure store confinement and no-follow checks unchanged. Do not delete unrelated local files or change save formats.

Keep monster capabilities, the one-card cap, no bindings, no age prerequisite, no free text and no selectable character fields. Startup iterates visual declarations and requests only a missing species card with no in-flight job and no valid official default for that visual species. It must resolve official defaults from the declared species subject even without a live entity. Existing card guards and queue serialization remain. Manual generate/requeue, seed sync and successful worker publication retain their existing workflow under the species key. Missing/pending/failed generation carries a monster silhouette and truthful status; a silhouette never counts as generated art.

Update `art.monster_description` in `prompts/art.yaml` and its degradation contract to take the selected species' public physical appearance only. Delete tier rank and multi-creature example placeholders and their tests. The prompt-library unavailable path uses the same selected public appearance. Baseline category text is an authored generic creature description, not an individual's proper name. Keep character prompt composition unchanged.

### D3. Species cards are reusable; personal preferences remain individual

Reusable generated/seeded cards, the species record default and its one-card replacement semantics are species-scoped. Explicit card default selection in a species rail intentionally changes that species' shared runtime default only. It never affects another species, even one in the same tier. The existing runtime-card-before-official-default order remains for valid images of the same visual species.

Personal official selection and official geometry use entity-local serialized preferences, keyed by stable root-relative official identity, through the existing gallery/preference sole writer and lock. Extend preference read/write entry points with the actual entity context for monsters; character storage stays unchanged. The presenter always supplies that context. Resolve a selection only inside the entity's current declared visual reference. Two individuals of one species can choose different official images/geometry while sharing source bytes. A stale preference remains stored but ignored. A shared species runtime default is distinct from an individual's personal default. Changing the shared species default does not clear an individual's explicit official selection; that selection retains precedence. Character personal-default mutual clearing remains unchanged. Generation itself does not clear an explicit personal official choice.

The world species gallery still has one unique rail row per visual key. It lists admitted visual species in deterministic key order, with the puppet first and companions prioritized within the existing 24-row bound. Once the visual catalog grows past capacity, truncate deterministically; never reserve an impossible unbounded species count or exceed the payload cap. Subject selection validates actual rail membership, and a retired selection reverts to the puppet. Official species rows are previewable from a declaration-derived reference even without a live monster. Bare species rows have no individual personal-preference target; hide personal official controls there and reject direct personal preference requests with the stable `entity_required` code and no write. Add a server-authored `supports_personal_official_preferences` capability flag, mirrored in both validators and the Vue UI, with a gallery schema version bump to 2 and no v1 shim. Characters retain their existing personal official editing workflow. Entity-context preference APIs remain available to callers with a real monster; adding a separate monster-instance picker is outside this fix.

### D4. Amend conflicting design and requirements explicitly

For avoidance of ambiguity, D3's overflow order reserves up to 23 stable-key visual species after the puppet; remaining character slots are companion-first, and the final emitted rail order is puppet, admitted characters, admitted species. Every authored baseline population row has a required visual key; downstream missing-provenance handling covers malformed or non-baseline entities, not an optional authored field.

Implementation amends D15 and the portrait extension in §8 of `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md` to say that reusable monster art is keyed by declared visual species, never threat tier; personal choices remain entity-local. Keep D10 scene archetypes and all combat tier contracts. Add the two-change cutover to its Phase 6 art roadmap notes. Amend §§2, 3 and 5 of `docs/superpowers/specs/2026-08-02-webclient-art-portrait-ui-design.md`, and §7 of `docs/superpowers/specs/2026-10-05-monster-data-model-design.md` to distinguish art-only base population metadata from complete combat species and to remove the remaining generic tier gallery assumption. Historical archived changes remain historical.

Delta specs replace the conflicting requirements and scenarios in their entirety. Unchanged gallery capabilities/card caps, image encoding and cutout guarantees remain unchanged; tier-specific examples in those contracts are updated to valid visual species where necessary. Deployment and seed guides document `monster/goblin/` official content and `monster/<visual-key>/` seed/runtime subjects, plus unknown provenance and no-image behavior. No tier art path is advertised as usable.

## Cutover and test ownership

`cutover-matrix.md` lists the affected test assertion families before apply. Extend existing subject, species portrait, service monster gallery, prompt, seed, staff, media, gallery actions/panel and fallback suites; rewrite assertions that require species rejection or tier sharing. Use synthetic independent visual species and same-tier monsters for mechanism tests. Registry-contract tests validate current declaration closure without pinning the production roster. Reuse the actual baseline goblin boundary as a representative smoke, without turning every species into a cloned smoke suite. Existing green frontend lineup tests establish their own contracts only.

For all modified/retired requirement IDs, use `tools.spec_traceability list` over the equivalent merged spec tree and reattach each justified assertion individually. Register any genuinely new test module in `.github/evennia-shards.json` and the owning collection mechanism. No traceability aliases, blanket decorators, skipped tests or allowlists. Existing test modules are preferred. The publication companion owns the managed-browser first-engage/round acceptance journey.

## Review disposition

One blocking rubber-duck review covered both complete changes. Its confirmed schema-mirroring conflict was fixed by modifying the full version-mirroring requirement to version 2. The claimed omitted dialogue-host scenario and legacy worker-push scenario were not present at the cited locations in the current main specs; the actual old-treatment scenario was already replaced. An explicit no-fallback dialogue-host scenario was added to remove any ambiguity. Clarified rail overflow precedence and total baseline visual keys. Retired-tier startup isolation remains owned by lifecycle/queue requirements and the cutover matrix, avoiding duplicate tests. No runtime checks were performed during this review.

## Risks / Trade-offs

- Art-only metadata may drift from selected population names. Bind both fields to one declaration and add registry closure plus producer tests.
- Existing local tier artifacts can remain physically present. Membership rejection at every producer, reader and route makes them unreachable without destructive cleanup or migration.
- A one-card species replacement can change valid same-species presentation. This retains the supported cap; it cannot affect another species and explicit personal official selections keep precedence.
- Entity-local preferences need real context. Bare species gallery rows expose only shared-card management and official previews; server capability flags and stable rejection prevent a false personal-edit promise.
- Identity and publication span different owners. Apply this one-day backend/gallery cutover before the one-day publication/renderer change, then run the complete end-to-end acceptance. Scope estimates assume reuse of current generation, validators and test harnesses, with no new image engine.

## Deployment

Clean pre-release cutover with no data migration or compatibility layer. No existing tier record is renamed into a species record. Existing valid official files remain mounted and immutable. Rollback uses the prior code revision and its own development data snapshot; the new code must never run a reverse migration or infer old tier selections.
