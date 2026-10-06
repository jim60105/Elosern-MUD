## Context

The approved data model (design §2–§3) wants species and variant content in `world/lore/` as frozen,
keyed, read-only data. The repo already has that shape (`world/lore/monsters.py` tier registry,
`world/lore/wilderness_regions.py`, `world/lore/sync.py` idempotent mirror), so this change adds one
module in the existing idiom rather than a subsystem. The consumers that need species identity — the
`Monster` typeclass, wilderness population, site placement, quest selectors, kill accounting, and
species art identity — are owned by sibling changes; this change deliberately publishes data plus
validation and touches no caller.

## Goals / Non-Goals

**Goals:** stable identity keys; validated species/variant membership; public/private separation;
habitat as compatibility only; approved zh-TW narrative landed; balance slots honestly empty.
**Non-Goals:** no individual construction, no spawning or population reconciliation, no quest
selectors, no portrait resolution change, no skills, no numeric balance, no player command surface.

## Decisions

**D-S1 One module, two registries, no new package.** `world/lore/monster_species.py` holds
`MonsterSpecies`, `MonsterVariant`, both keyed dicts, construction-time validation, and the published
projections. Splitting species and variants into two modules would split one invariant (variant
membership) across files, and a `world/lore/monsters/` package rename would churn every existing
`MONSTER_TIER_REGISTRY` import for no behavioural gain. The existing tier registry stays where it is:
tiers are coarse threat classification (design §3) and remain legitimate; identity is added beside
them, not substituted under existing callers.

**D-S2 Membership is validated at construction, not at lookup.** Validation runs while the module-level
dicts are built and raises a named `MonsterSpeciesRegistryError`, matching the
`_validate_monster_fallback_keys` precedent in `world/lore/monsters.py`: an authored typo fails at
import, so no consumer can ever observe a half-valid registry. The default-variant rule ("must belong
to the species and be an ordinary variant") is checked in the same pass, which is why species
construction is ordered after variant registration in the module's build sequence.

**D-S3 Ordinary-vs-stronger is an authored boolean, never name parsing.** The bestiary names
`啄穗型`/`領群型`-style pairs, and the design forbids inferring counting eligibility or strength from a
name. A single `ordinary_variant: bool` per variant is the whole mechanism; the species-level
`default_variant_key` plus that boolean expresses "the species baseline is an ordinary version" without
a second classification vocabulary. No elite/boss ladder is invented for this batch: the twelve approved
variant directions are exactly what is registered.

**D-S4 Balance-gated slots ship empty (option b of the balance-honesty rule).** `combat_profile` is a
frozen all-or-nothing record and `danger_grade` is optional. Empty is a legal, meaningful value that
downstream code reads as "no approved per-variant profile exists" — never a zero, never a per-species
number invented from flavour, and not itself tier-band truth; the one sanctioned fallback while a
profile is empty is the named interim tier-band rule owned by `monster-identity-construction` (recorded
with its numeric source), and no consumer may read the registry slot as if it carried that fallback —
the alternative (gating the whole registry
behind a feature flag until balance lands) would block identity, placement, quest, and artwork work on
numbers nobody has approved. Partial profiles are construction errors so nobody can smuggle an invented
HP into one field. The zeroed MP/SP/`magic_power` of today's low/mid tier construction is a tier-build
detail, and the spec forbids reading it as species truth in either direction.

**D-S5 Special abilities are a named external prerequisite, not a guarded field.** Design §1 states
this work registers no new skills, and today's monster behaviour only selects damage skills, so the six
abilities have no executable form. Rather than a dormant field or a fake behaviour key, the prerequisite
is named in the proposal and spec: an independent skill/behaviour-mechanics change must land the
mechanics (including the mana-drain interaction with `mp_flow` and the fog/rock terrain dependencies)
before any variant can carry an executable effect; narrative prose remains the only carrier. This is the
reasoned-exemption placement for the ability seam: the seam is documented and guarded by a spec
requirement plus a negative test, which is stronger than a code seam that nothing can implement
correctly yet.

**D-S6 Published projections are built by a function, not a `to_dict()`.** `published_species_view()` /
`published_variant_view()` return explicitly enumerated public fields, so serialization can never grow
a private field by accident when a field is added — the projection is an allowlist, and the public/private
split is one test with distinctive private text rather than a denylist that has to be re-audited per
field.

**D-S7 Startup mirror reuses `world/lore/sync.py`.** Species/variant content mirrors into the existing
Script mirror through a new named synchronization step (`sync_monster_species`) that emits one boundary
info event (`monster_species_sync`) carrying the registry identifiers and their counts; no new Script,
no new sync entry point, so idempotency discipline is inherited. The event is deliberately not
`startup_step`: that reserved name belongs to the composition-root catalog's `_startup_step` wrapper
(exactly one per catalog step, in catalog order), and this mirror is not a catalog step — the
`world/art/gallery_seed.py` boundary event is the precedent. `sync_all()` delegates the species/variant
categories to that step, so every entry is still mirrored exactly once per startup.

## Risks / Trade-offs

- Two vocabularies coexist (tier + species) until the sibling changes re-point their callers. Mitigated
  by the design's own framing — tier stays a coarse band — and by this change making zero caller edits,
  so drift is impossible: the only truth is that both registries exist.
- Empty balance slots tempt consumers to substitute tier bands as if they were per-species truth.
  Mitigated by spec language ("`None` means no approved per-variant profile exists") and by the single
  sanctioned fallback being the named interim tier-band rule owned by the construction change —
  recorded per individual with its numeric source and replaced, not branched, when approved profiles
  land; no other consumer may read the empty slot as any number at all.
- Registry-content tests are data-echo-shaped by nature. Mitigated per `tools/test_data_lint`: behavior
  tests use synthetic species fixtures only; the approved bestiary strings are asserted exclusively in a
  tagged data-contract test registered in `tools/test_data_freeze.json`.

## Open Issues

None blocking. The balance-approval change and the ability-mechanics change are external prerequisites
tracked in the proposal; the artwork wave's official-package content for `monster/<species-key>/`
follows from this registry's keys.

## Review Dispositions (2026-10-06)

Two rubber-duck reviews ran over this change: one over the plan before implementation, one over the
finished diff. Every finding from either round is folded into the implementation or explicitly
dispositioned here.

### Pre-implementation review

It raised blocking findings (four on the plan itself, plus the stable-key import-boundary
adjudication) and several non-blocking ones.

- **Boundary event name (blocking).** The single boundary info event is `monster_species_sync`, not
  `startup_step`: `startup_step` is reserved to the composition-root catalog's `_startup_step` wrapper
  (exactly one per catalog step, in catalog order, per `observability-logging`), and a second one for a
  step outside `STARTUP_STEP_ORDER` would widen the event vocabulary silently.
  `world/art/gallery_seed.py`'s boundary event is the precedent. D-S7 and tasks 4.1 are reworded to
  match; the delta spec only requires "one boundary info event ... with registry-scoped context keys".
- **Shard registration (blocking).** No `.github/evennia-shards.json` edit: the existing `world.lore`
  package label already owns every `world/lore/**/test*.py` module after Tasks 1.1's tree walk, and an
  explicit module label would overlap it and fail the shard-ownership contract. Confirmed by running
  that contract through the contract gate; tasks 5.1 records the confirmation.
- **Synthetic-kit parity (blocking).** Adding the two categories to `sync.py::_ALL_REGISTRIES` requires
  the kit's category-for-category mirror: `world/tests/synthetic_data/targets.py` gains
  `monster_species`/`monster_variants` backed by a new `data_monster_species.py` slice, and
  `world/tests/test_synthetic_data.py`'s real-definition-object table gains both catalogs.
  `world.tests.test_synthetic_data` passes.
- **Profile completeness (blocking).** `MonsterCombatProfile` gives every field a private completeness
  sentinel default, so an omitted field raises the named `MonsterSpeciesRegistryError` rather than the
  constructor's `TypeError`, exactly as R3's scenario requires; `None`, non-integer, boolean, and
  negative values are rejected by the same named error.
- **Key grammar without a forbidden import (blocking).** `world/lore/` may not import `world.art`
  (`world/art/fallback_keys.py` documents the boundary and `world/art/subjects.py` imports `world.lore`
  back). The shared stable-key predicate is therefore applied through
  `validate_monster_species_registry`'s injectable `key_violation_face`: shipped construction passes
  none, and the registered data-contract test re-runs the same validation with
  `subject_key_violation`, so every shipped key is checked by the one shared implementation and no rule
  text is duplicated. A boundary test pins the module's import set to the standard library plus
  `world.lore.*`.
- **Validated vocabularies.** `habitat_tags` are `WILDERNESS_REGION_REGISTRY` keys — the only existing
  habitat/region vocabulary, and the one `monster-site-placement` compares a site's habitat against —
  while `threat_tier` is a `MONSTER_TIER_REGISTRY` key and `danger_grade` a `GUILD_RANK_REGISTRY` key.
  All three are validated at construction through injectable faces, so an authored typo fails at import
  while behavior tests stay on invented keys. These are this change's chosen validated faces; a later
  change that needs a wider vocabulary extends the face, not the rule.
- **`MonsterSpecies.ordinary_variant`.** Kept because R1 mandates the field: it is the species-level
  twin of the variant flag (the baseline registered here is an ordinary version). R2 already forces
  every registered default variant to be ordinary, so what construction rejects is drift: the field
  must be a boolean and must agree with its default variant's authored classification. The
  data-contract test pins the shipped pairs.
- **R4's behaviour scenario.** "Narrative does not unlock a behaviour" has no subject in this change —
  no variant is reachable from the behaviour-selection path, which is owned by the sibling
  identity/mechanics changes. Rather than fake it, a guard test pins that
  `world/rules/monster_behaviour.py` reads no species/variant identity, and the ability seam stays the
  named external prerequisite recorded in the proposal.
- **Traceability.** No `covers_requirement` annotation is added for this change's new capability ids:
  `tools.spec_traceability` indexes only `openspec/specs/`, so the ids enter the index at archive sync
  (the preceding lore-registry change's precedent).

### Post-implementation review

It found no blocking issues and confirmed the shipped prose, the mirror trace, the artifact edits, and
the import boundary against the worktree sources. Its non-blocking findings and suggestions were
folded in:

- **Identity stress-test made discriminating.** The rename/re-tier test now asserts through a
  read-only registry view that the key set and every row's own key are unchanged and that neither the
  renamed display name nor the changed tier resolves as a key, so a name-derived identity could not
  pass it.
- **Prose fidelity pinned to the approved text.** The registered data-contract test now requires every
  published sentence of all six species (description, appearance, ecology) and all twelve variants to
  appear, in order, in `docs/lore/bestiary.md`'s own text (compared with whitespace and markdown
  emphasis removed), so the published strings cannot silently drift or be invented. The derived
  appearance field is the approved prototype sentence's head clause, as the module comment records.
  One cosmetic divergence was removed to keep the pin exact: the crocodile's `magic_power` clause no
  longer appends 值 and matches the bestiary sentence.
- **Conjecture test made discriminating.** It now also asserts the published view does not return a
  marker-stripped rendering of its input, so a projecting/normalising view fails.
- **Runtime-touch test strengthened.** The before/after comparison now digests every object, art, and
  non-lore script row's persisted attribute payload (not just counts and keys) and covers the first
  run as well as the repeat, so an in-place modification would be caught.
- **Single declaration for the mirror categories.** `sync.py` declares the species registries once
  (`MONSTER_SPECIES_REGISTRIES`); the mirror table composes from it and the step and the skip set both
  derive from it, so the two can no longer drift.
- **Species classification validated.** `MonsterSpecies.ordinary_variant` must be a boolean and must
  agree with its default variant's authored classification, so the mandated field cannot drift from
  the baseline it describes.
- **Read-only and purity pinned.** Tests assert both published registries are `MappingProxyType`
  instances that refuse mutation, and that a rejected candidate leaves its inputs and the published
  registries untouched.
- **Behaviour guard parsed, not textual.** The R4 guard now walks the behaviour-selection module's AST
  for identity reads instead of scanning its source text, so a comment mentioning a species key can
  never trip it while a real identity read would.
