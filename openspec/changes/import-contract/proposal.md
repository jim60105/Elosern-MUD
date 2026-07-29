## Why

This is roadmap item #4 (design doc §11), depending on change 3 (`entity-traits`) for the
`LivingEntity`/`PlayerCharacter`/`NPC` typeclasses and the race-driven trait-construction helpers
it declared. Design doc §5.3 assigns this change one job: freeze `world/imports/` — schema,
validation CLI, loader, and one reference example — and hand it to a different person who
implements the actual import pipeline without access to this design conversation. The Milestones
section is explicit that this handoff point matters: **"After change 4 — the import contract is
frozen; the import implementer can start."** Nothing downstream of this change may still be
guessing at field names, reject-vs-warn behavior, or what a "base stat" means.

Two things make this more than a mechanical schema write-up. First, design doc §1 makes
`age >= 18 AND apparent_age >= 18` a **code-level invariant**, not a documentation convention — the
sample cards this project's own author has been using in `tmp/story_settings/character/` do not
satisfy it (confirmed: 悠花·玄夜 is age 16), so the contract must reject them outright and a
regression test must never let that rejection erode. Second, §5.3's own `skills` check ("every key
exists in the skill registry") points at a registry that change 5 (`skills-equipment`) builds in
parallel with this change, not before it — freezing a hard dependency on unbuilt data would either
block the freeze milestone or silently invent a registry. This proposal resolves that ordering
conflict explicitly (see design.md D-5) rather than leaving it for the implementer to discover.

## What Changes

- Add `world/imports/schema.py`: `CHARACTER_SCHEMA_V1` and `WORLD_SCHEMA_V1` as JSON Schema (draft
  2020-12) documents, validated via the `jsonschema` package — consistent with design doc §7.5's
  own guardrail pipeline, which already names "local jsonschema validation" as a step. Both schemas
  require a `record_type` discriminator (`"character"` / `"world_entry"`) that `validate.py`
  dispatches on explicitly; a record with a missing or unrecognized `record_type` is rejected
  outright, naming the valid values — this is deliberate for an implementer who cannot ask us
  questions: an inferred dispatch (e.g. "has an `age` field") would misclassify a malformed
  character record that happens to omit `age`, routing it away from the age gate entirely. The age
  gate is encoded structurally (`"minimum": 18` on both `age` and `apparent_age`, loudly documented
  in each field's own `description`), not left to a semantic-layer check that could be forgotten.
  `stats`'s `description` states, in the schema itself, that every value is a **base**,
  pre-skill-multiplier number — the `88*1000` source-card notation is base `88` with a separate
  ×1000 skill multiplier, never a stored `88000`.
- Add `world/lore/sexual_vocab.py`: the ordered level-name vocabularies design doc §6.4 names
  (`arousal`, `wetness`, `shame`, `exposure`, `climax_phase`, `sensitivity`) as plain, behaviorless
  tuples — pure lore data, not a state machine. `CHARACTER_SCHEMA_V1` imports these tuples to build
  its `sexual_baseline` enum constraints now; change 7 (`sexual-state`) is expected to import the
  same tuples for its ordered-level `Trait` subclass rather than redefining the ladder — see design
  doc D-6 for why this avoids a circular dependency between change 4 and change 7.
- Add `world/imports/validate.py`: a CLI (`python -m world.imports.validate cards/*.json`)
  implementing the design doc §5.3 reject/warn table exactly — `age`/`apparent_age`, `race`/
  `subrace` registry existence (including the `subrace.race_key == race` cross-check change 2's
  design.md flagged as an open item for this change), `skills` registry existence (pluggable —
  see below), `disguised_stats ⊆ stats` keys, `sexual_baseline` shape (reject, not warn — it is
  typed per §5.3, unlike the plausibility-only `stats` check), `stats` inside the race's
  plausible band (warn), and `persona` type-only. Import is **all-or-nothing** across every file
  given on one CLI invocation: any single rejection anywhere in the batch fails the whole batch,
  and the report names which record, which field, and why. Whenever any check is running in
  degraded mode (currently: skill-key validation when the skill registry is unavailable — see
  below), the CLI prints a **prominent banner** at the top of its output naming exactly which
  checks are not being enforced and why, so an importer author cannot mistake a degraded pass for
  a clean one.
- Add `world/imports/loader.py`: instantiates `PlayerCharacter`/`NPC` instances **only after**
  `validate.py`'s batch validation reports zero rejections. Populates `entity.traits` from the
  literal imported `stats` values (merged onto `race_floor()` for any keys the card omits) — never
  re-derived from the race baseline, never skill-multiplied. Populates the seam attributes change 3
  already declared (`persona`, `sexual`, `skills`, `equipment`) and `entity.db.inventory` verbatim,
  unvalidated beyond the shape checks `validate.py` already performed — this change does not
  implement skill effects, equipment slots, or the sexual state machine.
- Add `world/imports/examples/example_character.json`: one valid, schema-compliant reference card
  — an adult (age 22, apparent_age 22) elf with a subrace, base-value stats using the `×1000`
  notation correctly (base value stored, multiplier documented in a sibling comment field, never
  baked in), a disguised-stats subset, and a fully-typed `sexual_baseline`. Covered by a permanent
  test asserting it always validates cleanly.
- **Resolves the change-5 ordering conflict** (design doc D-5): `skills`-key validation resolves
  the registry via a plain Python import of a forward-declared module path
  (`world.skills.registry.SKILL_REGISTRY`) that change 5 is expected to create. Until that module
  exists, the import fails and the check degrades to a **warning**; once change 5 lands, the same
  code starts rejecting unknown skill keys automatically, with no code change here. **No dependency
  on change 5 is added; design doc §11's dependency graph is unchanged.** A self-arming test
  (skipped while the registry is absent, active the moment it is importable) asserts an unknown
  skill key is REJECTED once change 5 lands — change 5 cannot land while leaving skill validation
  permanently lenient without that test failing.
- **Resolves the `sexual_baseline` vocabulary ownership question** (design doc D-6): the ordered
  level names live in `world/lore/sexual_vocab.py` (this change), a one-directional dependency both
  this change and change 7 read from — no circular dependency, and change 7 does not need to exist
  for this change to validate `sexual_baseline` shape correctly today.
- Add a permanent regression test asserting an age-17 record is rejected (never deleted, never
  relaxed, per design doc §10) plus the full reject/warn matrix, the all-or-nothing batch behavior,
  the `record_type` discriminator's reject-on-missing/unrecognized behavior, the degraded-mode
  banner's presence whenever a pluggable check is degraded, and the self-arming skill-registry test
  described above.

## Capabilities

### New Capabilities
- `import-schema`: `CHARACTER_SCHEMA_V1` and `WORLD_SCHEMA_V1` — the frozen JSON Schema documents,
  the age gate, the base-value stats documentation, the `persona` opacity contract, and the
  `sexual_baseline` typed shape built from `sexual-vocabulary`.
- `sexual-vocabulary`: the ordered level-name tuples for `arousal`/`wetness`/`shame`/`exposure`/
  `climax_phase`/`sensitivity`, authored once and read by both this change and (later) change 7.
- `import-validation`: the CLI, the full reject/warn enforcement matrix, all-or-nothing batch
  semantics, per-record/per-field error reporting, and the pluggable skill-registry check.
- `import-loader`: instantiate-only-after-validation, literal-stats trait population, and
  seam-attribute population for handlers not yet built.
- `import-reference-example`: the one valid, adult-compliant reference card and the permanent test
  keeping it valid against the frozen schema.

### Modified Capabilities
- None. `openspec/specs/` is currently empty (changes 1–3 have not been archived yet).

## Impact

- **New files**: `world/imports/__init__.py`, `world/imports/schema.py`, `world/imports/validate.py`,
  `world/imports/loader.py`, `world/imports/examples/example_character.json`,
  `world/imports/tests/` (package), `world/lore/sexual_vocab.py`.
- **Modified files**: `world/lore/__init__.py` gains a re-export of `sexual_vocab`'s public tuples,
  once that file exists per change 2's scope — a one-line addition, not a redesign of change 2.
- **New dependency**: the `jsonschema` package (not yet present in the project's dependency file as
  of change 1/2/3) — flagged for the implementer to add and pin, same "verify before trusting"
  discipline changes 1–3 already established for their own assumptions.
- **Depends on**: change 3 (`entity-traits`) for `LivingEntity`/`PlayerCharacter`/`NPC`,
  `race_floor()`, and the `disguised_stats`/seam-attribute storage conventions; transitively on
  change 2 (`lore-world-data`) for `RACE_REGISTRY`/`SUBRACE_REGISTRY`/`STATIC_TIER_REGISTRY`.
  **No dependency on change 5** (see design doc D-5) — the roadmap's parallel-track intent for
  changes 4/5/6 after change 3 is preserved unchanged.
- **Consumers deferred to later changes**: change 5 (`skills-equipment`) is expected to create
  `world/skills/registry.py::SKILL_REGISTRY` at the forward-declared path this change reads;
  change 7 (`sexual-state`) is expected to import `world/lore/sexual_vocab.py` rather than
  redefine the ordered levels. This change validates the *shape* of `skills`/`sexual_baseline`
  data only — it implements neither skill effects nor the sexual state machine.
