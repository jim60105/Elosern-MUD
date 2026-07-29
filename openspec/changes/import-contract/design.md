## Context

This is roadmap item #4 (design doc §11), depending on change 3 (`entity-traits`, which provides
`LivingEntity`/`PlayerCharacter`/`NPC`, `race_floor()`/`build_initial_traits()`, and the
`disguised_stats`/seam-attribute storage conventions) and transitively on change 2
(`lore-world-data`, `RACE_REGISTRY`/`SUBRACE_REGISTRY`/`STATIC_TIER_REGISTRY`). No code exists yet
for this change's scope — `world/imports/` is currently an empty stub package from change 1.

Design doc §5.3 gives this change a narrow, high-stakes job: produce `world/imports/schema.py`,
`validate.py`, `loader.py`, and `examples/`, then **freeze** them. The Milestones section states
this is a handoff point — "the import implementer can start" after this change — meaning the
schema, its documentation, the reference example, and the CLI are the actual deliverable, not
scaffolding around the loader. Someone will build the real import pipeline against this contract
without access to this design conversation.

Two problems the task framing calls out by name, because both required more than a straight
transcription of §5.3's table:

1. **Ordering conflict with change 5.** §5.3's table requires "every `skills` key exists in the
   skill registry," but that registry (`SkillDef`, `SkillHandler`) is change 5's
   (`skills-equipment`) output, and design doc §11 runs changes 4, 5, and 6 in parallel after
   change 3 — not change 4 after change 5. See D-5.
2. **`sexual_baseline` vocabulary is undefined at this point in the roadmap.** §5.3 puts
   `sexual_baseline` in the typed part of the record, but the ordered level names
   (平靜→微興奮→中等→高度→極限, etc.) are described in §6.4, which belongs to change 7
   (`sexual-state`) — a change that runs after this one and has not been proposed yet. See D-6.

Both are resolved below without adding a dependency this change cannot afford and without leaving
either concern unowned.

## Goals / Non-Goals

**Goals:**
- `CHARACTER_SCHEMA_V1` and `WORLD_SCHEMA_V1`, frozen JSON Schema documents, each field's intent —
  especially the age gate and the base-value stats convention — documented loudly in the schema
  itself, not only in prose surrounding it.
- A CLI (`validate.py`) implementing design doc §5.3's reject/warn table exactly, all-or-nothing
  across a batch of files, with per-record/per-field/per-reason error reporting, explicit
  `record_type`-based schema dispatch (D-1), and a prominent banner whenever any check is running in
  degraded mode (D-5).
- A loader (`loader.py`) that instantiates entities strictly after validation passes, writes literal
  imported stat values (never re-derived, never skill-multiplied) into `entity.traits`, and stores
  everything this change does not interpret (persona, sexual baseline, skills, equipment, inventory)
  into the placeholder seam attributes change 3 already declared.
- One valid, adult-compliant reference card (`examples/example_character.json`) that exercises every
  schema branch and is kept valid by a permanent test.
- A resolved, documented answer to both named problems (A: skill-registry ordering; B: sexual
  vocabulary ownership) that does not silently assume unbuilt state exists.
- A permanent regression test asserting an age-17 record is rejected, per design doc §10, written so
  it can never be quietly deleted or loosened without the deletion itself being conspicuous.

**Non-Goals:**
- No skill effect resolution, `SkillHandler`, or equipment slot logic — change 5's job. This change
  validates that a `skills` array names *plausible* keys (once a registry exists to check against);
  it does not interpret what any skill does.
- No `SexualState` state machine, no `rulebook/sexual.yaml`, no transitions — change 7's job. This
  change validates that `sexual_baseline` has the right *shape* using vocabulary it authors (D-6);
  it does not simulate arousal, wetness, or climax.
- No account/session binding for `PlayerCharacter` — Evennia login/puppet machinery is unrelated to
  parsing a character card and out of scope here. `loader.py` exposes a `typeclass` parameter so a
  caller can target `PlayerCharacter` or `NPC`; wiring an imported `PlayerCharacter` to a live
  Account is left to whichever later system handles character selection/creation.
- No new mechanical world-truth format. `WORLD_SCHEMA_V1` (D-14) is deliberately minimal and
  narrative-only; `world/lore/`'s frozen dataclasses (change 2, D9) remain the sole source of
  mechanical truth. This change does not let JSON imports override or extend `RACE_REGISTRY` et al.
- No backward-compatibility, migration, or deprecation handling — the project is unreleased with
  zero users, and `world/imports/` currently contains no code beyond change 1's empty stub.

## Decisions

### D-1. Two schemas, dispatched by an explicit, required `record_type` discriminator — not
implicit field-presence sniffing.

**Revised after review.** An earlier version of this decision dispatched by which distinguishing
field was present (`age` for a character, `content` for a world entry), reasoning that design doc
§5.3's own worked example has no wrapping discriminator and that adding one would diverge from the
frozen shape it established. That reasoning traded away exactly the wrong thing: this contract goes
to an implementer who cannot ask the design authors questions, and implicit dispatch is fragile in
precisely the case that matters most — a malformed character record that happens to omit `age`
(the single most important field in the entire schema) gets silently misclassified as a world
entry, validated against the wrong schema entirely, and reported back with an error about a missing
`content` field instead of a missing `age` field. The age gate would never even run against it. A
`content`-less, `age`-less garbage record is the one input this contract most needs to fail loudly
and unambiguously on, and field-sniffing was the one dispatch mechanism guaranteed to fail
ambiguously on it instead.

**Decision**: both `CHARACTER_SCHEMA_V1` and `WORLD_SCHEMA_V1` require a `record_type` property —
`{"const": "character"}` and `{"const": "world_entry"}` respectively. `validate.py` reads
`record_type` first, before attempting any other validation, and dispatches explicitly:

```python
def classify_record(raw: dict) -> Literal["character", "world_entry"]:
    record_type = raw.get("record_type")
    if record_type == "character":
        return "character"
    if record_type == "world_entry":
        return "world_entry"
    raise RecordClassificationError(
        f"record {raw.get('key', '<unknown>')!r} has record_type={record_type!r}; "
        f"expected one of 'character', 'world_entry'"
    )
```

A record with a missing, misspelled, or otherwise unrecognized `record_type` is rejected
immediately, naming the valid values — this never falls through to a wrong schema, and it never
depends on which other fields happen to be present or absent. This costs the card author one field
per record; in exchange, a whole class of "validated against the wrong schema, error message points
at the wrong problem" failures cannot happen at all. The reference example (D-15) sets
`"record_type": "character"` accordingly.

**Alternative considered (previous decision, superseded)**: dispatch by presence of a
distinguishing field (`age` vs. `content`), with no schema-level discriminator, on the reasoning
that it keeps the frozen shape minimal and matches design doc §5.3's example exactly. Rejected on
review — the failure mode above (an incomplete character record silently routed to the wrong
schema, hiding the age-gate failure behind an unrelated error) is worse than the one field of
friction an explicit discriminator costs, and design doc §5.3's example is illustrative of the
record's *content* fields, not a claim that no envelope field may ever be added by the change
authorized to freeze this exact contract.

### D-2. Schemas are JSON Schema (draft 2020-12) dicts, validated via the `jsonschema` package.

Design doc §7.5 (the Generative Layer's Guardrail) already names "local jsonschema validation" as
step 2 of its own pipeline — this change reuses the same representation and library rather than
inventing a second, hand-rolled validation style for a different part of the codebase. JSON Schema
expresses every *static* shape/type/range/enum constraint the reject table needs directly (`age`'s
`minimum: 18`, `sexual_baseline.arousal`'s enum membership, `persona`'s bare `type: object`); checks
that require a runtime Python-registry lookup (race/subrace/skill existence, stats-band plausibility)
cannot be expressed in static JSON Schema and are layered on top in `validate.py` as a semantic
pass, run only after the structural pass succeeds.

**New dependency**: the `jsonschema` package is not present in the project's dependency file as of
changes 1–3. Flagged for the implementer to add and pin — the same "verify before trusting"
discipline changes 1–3 already established for their own Evennia-version and Evennia-hook
assumptions.

**Alternative considered**: hand-rolled Python validator functions only, no JSON Schema library.
Rejected — it would diverge from §7.5's already-established pattern for no benefit, and JSON Schema
gives the frozen contract itself (not just prose around it) a machine-checkable form, which matters
more here than anywhere else in the project since this artifact is handed to someone without access
to this conversation.

### D-3. The age gate is encoded structurally (`"minimum": 18`) on both `age` and `apparent_age`,
not left to a semantic-layer check.

```python
"age": {
    "type": "integer",
    "minimum": 18,
    "description": (
        "HARD GATE. Every character entering the game -- player, NPC, or "
        "imported -- must be an adult (design doc S1). This minimum is a "
        "code-level invariant, never downgraded to a warning, and there is "
        "no import path that bypasses it."
    ),
},
"apparent_age": {
    "type": "integer",
    "minimum": 18,
    "description": (
        "Same hard gate as age, checked INDEPENDENTLY. A character who IS "
        "an adult but LOOKS underage is still rejected -- both fields must "
        "independently satisfy the minimum."
    ),
},
```

Putting the constraint in the schema itself (not only in a Python `if age < 18: reject` function
somewhere in `validate.py`) means the invariant is visible to anyone who opens `schema.py` and
cannot be silently bypassed by a semantic-layer code path that forgets to call the right function —
the structural pass runs unconditionally before anything else. `validate.py`'s reject-message
formatting still surfaces which of `age`/`apparent_age` (or both) failed and their actual values,
since a bare JSON Schema validation error is not always reader-friendly on its own.

A **permanent regression test** (`test_age_gate_rejects_minor`) constructs a record identical to
the valid reference example except `age: 17`, asserts rejection, and is marked in a code comment as
non-removable per design doc §10 ("An age-17 record **must** be rejected — a permanent regression
test"). A second test does the same for `apparent_age: 17` with `age: 22`, proving the two checks
are independent, not redundant.

### D-4. The base-value stats convention is documented in the schema's `stats` `description`, not
only in prose.

```python
"stats": {
    "type": "object",
    "description": (
        "BASE values only, pre-skill-multiplier. Source-card notation like "
        "'88*1000' means a base value of 88 with a x1000 SKILL multiplier "
        "applied at combat-resolution time (design doc S5.1/S5.3, change 3 "
        "D-7) -- it is NEVER a stored value of 88000. If a value here looks "
        "implausibly large for the declared race (e.g. thousands for a "
        "human, whose static_baseline tops out at 22), the most likely "
        "cause is a skill multiplier baked in by mistake, and the record "
        "should be corrected before import, not accepted as a very strong "
        "individual."
    ),
    "properties": { ... },  # hp/mp/sp/atk_phys/agility/defense/magic_level/guild_merit
    "additionalProperties": False,
},
```

This mirrors change 3's D-7 boundary (`entity.traits` never holds a skill-multiplied value) onto
the import contract's own frozen artifact, in the same place an implementer reading `schema.py` in
isolation — without this design doc, without change 3's design doc — would look first. The
reference example (D-15) demonstrates the correct encoding directly: `stats.atk_phys: 88`, with a
sibling non-schema comment field in the example file (not part of the schema itself) spelling out
that a ×1000 身體超強化 skill is what makes this character's *effective* combat power far higher at
resolution time.

**Alternative considered**: relying on the stats-band WARN check (§5.3's plausibility check) alone
to catch multiplier mistakes. Rejected as the sole safeguard — a warning is easy to miss in a large
batch import, and the goal here is to prevent the mistake at the point someone is writing the card,
not only to flag it after the fact. The loud schema description and the WARN check are
complementary, not substitutes for each other.

### D-5. Resolving the change-5 ordering conflict: `skills`-key validation is pluggable via natural
Python import resolution, degrading to a WARNING until the registry exists. **No dependency on
change 5 is added.**

**The conflict.** §5.3's table says "every `skills` key exists in the skill registry → Reject," but
that registry (`SkillDef`, `world.skills.registry.SKILL_REGISTRY` or wherever change 5 places it)
does not exist when this change is built — design doc §11 places changes 4, 5, and 6 in parallel
after change 3, not change 4 after change 5, and the Milestones section explicitly wants the import
contract frozen and handed off *before* waiting on change 5's completion.

**Two options considered**:
1. Declare `import-contract` depends on `skills-equipment` (change 5). Rejected — this breaks the
   roadmap's stated parallel-track intent for changes 4–6, delays the "contract frozen, implementer
   can start" milestone by an entire change, and change 4 does not otherwise need anything change 5
   builds (`SkillHandler`, equipment slots) — only the *existence* of a key name.
2. **Make skill-key validation pluggable, degrading to a warning until the registry exists.**
   Chosen.

```python
def _resolve_skill_registry() -> Mapping[str, Any] | None:
    """Change 5 (skills-equipment) is expected to expose SKILL_REGISTRY at
    world.skills.registry. Until that module exists, this returns None and
    every skill-key check below degrades from REJECT to WARNING (see D-5).
    No code change is needed here once change 5 lands -- the import for a
    card with a bad skill key starts failing automatically, with no edit to
    this file, the moment world/skills/registry.py exists and exports
    SKILL_REGISTRY."""
    try:
        from world.skills.registry import SKILL_REGISTRY
    except ImportError:
        return None
    return SKILL_REGISTRY

def _check_skills(record: dict) -> tuple[list[Issue], list[Issue]]:
    rejections: list[Issue] = []
    warnings: list[Issue] = []
    registry = _resolve_skill_registry()
    for key in (*record["skills"], *record["passives"]):
        if registry is None:
            warnings.append(Issue(
                "skills", f"cannot verify {key!r} -- skill registry "
                "(change 5, skills-equipment) is not available yet"))
        elif key not in registry:
            rejections.append(Issue("skills", f"{key!r} not found in skill registry"))
    return rejections, warnings
```

This is a genuine, self-upgrading pluggability mechanism, not a permanent softening: the check
promotes itself from WARNING to REJECT the moment `world/skills/registry.py::SKILL_REGISTRY`
exists on the Python path, with zero edits to this file. A test simulates both states with the
import mocked — one run mocked to fail (asserts WARNING), one mocked to succeed and contain a
known-bad key (asserts REJECT) — so the degrade/promote *logic* itself is covered in isolation, not
just one branch of it. This mocked test is necessary but not sufficient — see the two additions
below, both added on review because a mock proves the logic works, not that anyone will ever notice
if the real world stays in the degraded state forever.

**Degraded-mode banner (added on review).** A silent WARNING is exactly the kind of thing an
importer author will not notice: they run the CLI, see every record reported as valid (warnings and
all, since warnings never fail the batch — D-11), and ship the batch. If change 5 then lands and
the same cards are re-validated, cards that were never actually checked against a real skill list
start rejecting for the first time, with nothing in what the author wrote having changed — a
confusing, delayed failure with no visible cause at the time it appears. **Decision**: `validate.py`
tracks every check currently running in degraded mode as a small, generic list (not hardcoded to
skills specifically, so a future pluggable check reuses the same path with no new banner code):

```python
@dataclass(frozen=True)
class DegradedCheck:
    name: str        # e.g. "skill-registry"
    reason: str       # e.g. "world.skills.registry.SKILL_REGISTRY is not importable"

def collect_degraded_checks() -> list[DegradedCheck]:
    checks: list[DegradedCheck] = []
    if _resolve_skill_registry() is None:
        checks.append(DegradedCheck(
            "skill-registry",
            "world.skills.registry.SKILL_REGISTRY is not importable -- skill-key "
            "checks are WARNINGS only and will not catch a typo'd or invalid "
            "skill key. This is expected before change 5 (skills-equipment) "
            "lands, and stops happening automatically once it does.",
        ))
    return checks
```

The CLI prints this list as a **prominent banner at the top of its output**, before any per-record
report — not folded into `--verbose` output, not a single line easy to scroll past — every single
time it runs while any check is degraded, whether the batch is otherwise clean or not:

```
================================================================================
 DEGRADED VALIDATION -- the following checks are NOT being enforced:
   * skill-registry: world.skills.registry.SKILL_REGISTRY is not importable --
     skill-key checks are WARNINGS only and will not catch a typo'd or invalid
     skill key. This is expected before change 5 (skills-equipment) lands, and
     stops happening automatically once it does.
================================================================================
```

**Self-arming landing test (added on review).** The mocked test above proves the degrade/promote
*logic* is correct, but a mock can pass forever even if change 5 lands with a `SKILL_REGISTRY` that
is empty, mistyped, or otherwise broken in a way that still leaves every real skill key unverified
— the real risk the pluggable approach carries, and the reason a hard dependency on change 5 was
rejected only after weighing this risk explicitly. **Decision**: a second, separate test checks the
*real* import, not a mock:

```python
def test_skill_registry_rejects_unknown_key_once_available():
    pytest.importorskip("world.skills.registry")  # skip -- change 5 not landed yet
    from world.skills.registry import SKILL_REGISTRY
    assert "definitely_not_a_real_skill_xyz" not in SKILL_REGISTRY
    rejections, _ = _check_skills({"skills": ["definitely_not_a_real_skill_xyz"], "passives": []})
    assert rejections  # must reject, not warn, once the registry genuinely exists
```

This test is a no-op (skipped) for the entire lifetime of this change's own review and everything
up to the moment change 5 lands — the same "no-op today, tripwire tomorrow" pattern change 3's D-9
already used for its disguise-boundary source scan. Once `world/skills/registry.py` exists on the
Python path with real content, this test stops skipping and starts asserting the promotion actually
happened. **Change 5 physically cannot land in CI while leaving skill validation permanently
lenient** without this test failing — which is the property that lets this design accept the
pluggable approach (D-5's chosen option) instead of forcing a hard dependency on change 5, per the
coordinator's explicit reasoning for accepting this trade-off.

**Coordination contract with change 5**: this design forward-declares the exact module path and
symbol name (`world.skills.registry.SKILL_REGISTRY`, a `Mapping[str, Any]` keyed by skill key) that
change 5 is expected to satisfy. This is the same forward-declaration pattern change 2's design.md
used for `Subrace` (flagged for change 4 to complete) — recorded here so whoever proposes change 5
sees the expectation rather than inventing an incompatible path independently.

**Does design doc §11 need to change?** **No.** Change 4's dependency stays exactly what the
roadmap already lists (change 3 only). The skill-key check's behavior — warning today, rejecting
once change 5 lands — is a property of `validate.py`'s implementation, not of the change's
dependency graph.

### D-6. Resolving the `sexual_baseline` vocabulary problem: a new, change-4-authored
`world/lore/sexual_vocab.py` module — one-directional, no cycle, explicit handoff to change 7.

**The problem.** §5.3 requires `sexual_baseline` to be typed and validated now, but the ordered
level names it must validate against (design doc §6.4: arousal 平靜→微興奮→中等→高度→極限, plus
wetness/shame/exposure/climax_phase/sensitivity ladders) are described only in the context of
change 7's (`sexual-state`) state machine, which has not been proposed and does not exist. A frozen
contract cannot reference an undefined vocabulary — but the vocabulary itself (an ordered list of
Chinese level names) is pure data, not behavior, and does not require the state machine, the
`Trait` subclass, or `rulebook/sexual.yaml` to exist first.

**Decision**: this change adds `world/lore/sexual_vocab.py` — six plain, frozen tuples, zero
behavior, zero dependency on anything except being plain Python data:

```python
# world/lore/sexual_vocab.py
"""Ordered level-name vocabularies for design doc S6.4's sexual-state fields.
Pure data, authored once here (import-contract, change 4) because
CHARACTER_SCHEMA_V1 needs it now to validate sexual_baseline shape. Change 7
(sexual-state) is expected to import these same tuples for its ordered-level
Trait subclass rather than redefining the ladder -- see design.md D-6."""

AROUSAL_LEVELS = ("平靜", "微興奮", "中等", "高度", "極限")
WETNESS_LEVELS = ("乾燥", "微濕", "濕潤", "大量", "泛濫")
SHAME_LEVELS = ("無", "輕微", "中等", "強烈", "成癮")
EXPOSURE_LEVELS = ("極低", "低", "中等", "高", "極高")
CLIMAX_PHASE_LEVELS = ("未達", "接近", "進行中", "餘韻")
SENSITIVITY_LEVELS = ("普通", "高", "極高", "敏感異常")
```

This lives in `world/lore/`, alongside change 2's other frozen-dataclass registries, not in
`world/imports/` — it is world data (design doc D9: lore is Python), not an import-specific
concept, and `world/lore/` is already the project's established "any consumer reads from here, no
one hardcodes magic values" location (design doc §5.1). `CHARACTER_SCHEMA_V1` imports these tuples
to build `sexual_baseline`'s enum constraints; change 7, when proposed, is expected to import the
same tuples for its `Trait` subclass's `descs` mapping (§4's own precedent: `CounterTrait`'s
numeric-bucket-to-label pattern) instead of re-typing the ladder from `world_info.md` a second time
and risking drift between the two.

**No circular dependency**: `world/imports/schema.py` → `world/lore/sexual_vocab.py` (one
direction); `world/rules/sexual_state.py` (change 7, later) → `world/lore/sexual_vocab.py` (same
one direction, independently). Neither `world/lore/` module depends back on `world/imports/` or
`world/rules/` — this is the identical read direction change 3's `world/rules/traits.py` already
uses against `world/lore/races.py`, so it introduces no new architectural pattern, only reuses the
established lore→rules/imports read direction.

**Who owns this vocabulary going forward?** `world/lore/sexual_vocab.py`, authored by this change.
Flagged explicitly (Risks, below) for whoever proposes change 7 to reuse rather than reinvent — the
same handoff discipline change 2's design.md used when it flagged `Subrace` forward to this change.

**Alternative considered**: defining the vocabulary inline in `world/imports/schema.py` only, with
no separate lore module. Rejected — it would leave change 7 no clean import path other than
reaching into `world/imports/` (the wrong read direction: rules code depending on the import
contract module) or redefining the ladder from scratch, reintroducing exactly the drift risk this
decision exists to prevent.

### D-7. `sexual_baseline` shape violations are a REJECT, not a WARN.

Design doc §5.3's table does not list `sexual_baseline` at all — its six-row table covers age,
race/subrace, skills, disguised_stats, stats-plausibility, and persona-type-only. `sexual_baseline`
being "typed" (§5.3's prose, ahead of the table) means it needs its own explicit rule, and the
existing WARN row is a poor fit: the stats WARN exists specifically because *prodigies legitimately
exceed the plausible band* — a warning models a genuine, expected edge case. There is no analogous
"legitimately exceeds the vocabulary" case for an enum field — a `sexual_baseline.arousal` value
that isn't one of the five documented levels is not an edge case, it is malformed data (a typo, a
stale value from before the vocabulary was fixed, or a different game's terminology). **Decision**:
malformed `sexual_baseline` shape (wrong type, missing `arousal`/`virgin`/`sensitivity`, or any
level value outside its vocabulary) is a REJECT, following the same reasoning as the `race`/
`subrace` registry-membership REJECT, not the stats-band WARN.

`wetness`, `shame`, `exposure`, and `climax_phase` are optional in `CHARACTER_SCHEMA_V1` — the
design doc's own reference example only sets `arousal`, `sensitivity`, and `virgin` — but where
present, each is validated against its vocabulary the same as `arousal`. `sensitivity` is a
`dict[str, str]` with free-form keys (body-part names, not enumerated anywhere) and vocabulary-
constrained values. Absent optional fields are left absent by `loader.py` (D-13) — defaulting them
to a specific level is change 7's job, not this change's, since that default is itself a design
decision about the state machine's initial condition.

### D-8. `disguised_stats ⊆ stats` keys is a semantic-layer check, not a JSON Schema constraint.

JSON Schema draft 2020-12 can express cross-field dependencies (`dependentSchemas` et al.), but
"every key of object A must appear as a key of object B" is awkward and hard to read in that form.
**Decision**: `CHARACTER_SCHEMA_V1` types `disguised_stats` structurally
(`{"type": "object", "additionalProperties": {"type": "integer"}}`) only; the subset check runs as
a plain Python comparison in `validate.py`'s semantic pass, rejecting with the specific offending
key(s) named. This keeps the JSON Schema document itself simple and keeps the more readable,
better-error-message form for a check that is inherently about relating two fields to each other,
consistent with how the race/subrace/skill/stats-band checks are already semantic-layer, not
schema-layer.

### D-9. `stats`-band plausibility (WARN) reads `RaceProfile`/`Subrace` directly — no hardcoded
numbers, mirroring change 3's discipline.

```python
def _check_stats_band(record: dict, race: RaceProfile, subrace: Subrace | None) -> list[Issue]:
    warnings: list[Issue] = []
    vitals = race.vital_baseline
    if subrace and subrace.vital_overrides:
        vitals = _apply_vital_overrides(vitals, subrace.vital_overrides)  # replace, not blend -- same rule as change 3 D-5
    for key, band in (("hp", vitals.hp), ("mp", vitals.mp), ("sp", vitals.sp)):
        value = record["stats"].get(key)
        if value is not None and not (band[0] <= value <= band[1]):
            warnings.append(Issue("stats." + key, f"{value} outside {race.key}'s {key} band {band}"))
    static = race.static_baseline
    for key, band in (("atk_phys", static.atk_phys), ("agility", static.agility), ("defense", static.defense)):
        value = record["stats"].get(key)
        if value is not None and not (band[0] <= value <= band[1]):
            warnings.append(Issue("stats." + key, f"{value} outside {race.key}'s {key} band {band}"))
    magic_level = record["stats"].get("magic_level")
    if magic_level is not None and not (0 <= magic_level <= race.magic_cap):
        warnings.append(Issue("stats.magic_level", f"{magic_level} exceeds {race.key}'s magic_cap {race.magic_cap}"))
    return warnings
```

Every band comes from `world.lore.races.RACE_REGISTRY`/`Subrace.vital_overrides` — no literal
number is written in `validate.py`. `guild_merit` has no lore-defined band (change 3: starts at 0
with no maximum) and is not band-checked. This is a **warning only** per §5.3: "prodigies
legitimately exceed it" — an elf with `atk_phys: 120` (above the documented 70–95 `elf_common`
band) is flagged, not rejected, consistent with `STATIC_TIER_REGISTRY["elf_prodigy"]`'s
open-ended top band (change 2, D-2c).

### D-10. `race`/`subrace` existence and cross-reference — completing change 2's flagged open item.

Change 2's design.md explicitly left this as "a task for whichever change consumes it (change 4)":
`race` must resolve in `RACE_REGISTRY`; if `subrace` is present, it must resolve in
`SUBRACE_REGISTRY` **and** `SUBRACE_REGISTRY[subrace].race_key == record["race"]`. Both failures are
REJECT, per §5.3's table row for race/subrace. `subrace` remains optional at the import layer
(change 2's own judgment call): a human or beastfolk record may omit it entirely, and the reference
example (D-15) is the one case that supplies it (`elf` / `ciaran`).

### D-11. All-or-nothing is enforced at two layers: the CLI's exit behavior, and `loader.py`'s
refusal to construct anything if any record in the batch rejected.

"All-or-nothing" (§5.3) means two things that must both hold:
1. **Within one CLI invocation covering multiple files**, if any single file rejects, the CLI's
   report says so for every file and exits non-zero — a human running `validate.py` sees the whole
   picture, not just the first failure.
2. **At the loader level**, `load_batch()` must not construct even the individually-valid entities
   in a batch that contains any rejection anywhere — "no partial import" means zero entities enter
   the world from a batch that had one bad record, not "all but the bad one."

```python
def load_batch(paths: list[Path], typeclass: type = NPC) -> list[LivingEntity]:
    report = validate_batch(paths)          # runs schema.py + validate.py's checks over every file
    if not report.all_valid:                # any rejection anywhere in the batch
        raise ImportRejected(report)        # nothing is instantiated -- not even the clean records
    return [
        instantiate_character(record, typeclass)
        for record in report.character_records
    ]
```

`ImportRejected` carries the full `BatchReport` (every record's rejections and warnings), so a
caller can print the same "which record, which field, why" detail the CLI does, without re-running
validation.

### D-12. `loader.py` writes literal imported stat values into `entity.traits`, merged onto
`race_floor()` for any keys the card omits — never re-derived, never skill-multiplied.

The design doc's own reference example does not set every one of the eight trait keys (`mp`, `sp`,
and `guild_merit` are absent from the §5.3 example). `loader.py` cannot leave those keys unset, so
it starts from change 3's `race_floor(RACE_REGISTRY[record["race"]])` (reused, not reimplemented —
the exact function change 3 built for this purpose) and overlays every key the imported `stats`
object actually provides, which always wins over the floor:

```python
def _resolve_trait_values(record: dict) -> dict[str, int]:
    race = RACE_REGISTRY[record["race"]]
    values = race_floor(race)          # change 3's function -- floor for any omitted key
    values.update(record["stats"])     # literal imported values always win
    return values
```

This is the one place this change writes to `entity.traits`, and it never applies a ×10/×100/×1000
skill multiplier — the same boundary change 3's D-7 established is carried forward unchanged. A
test (task 6.4) asserts that for every valid record, `entity.traits.<key>.value` after loading
equals exactly the imported `stats[<key>]` when present, and the race floor otherwise — never a
scaled or multiplied value.

### D-13. `loader.py` populates change 5/6/7's declared seam attributes with raw, uninterpreted,
already-shape-validated data — and adds one new raw attribute, `entity.db.inventory`, with no
change-3 edit required.

**The loader writes raw payload to `entity.db.*`, never to the bare attribute names.** Design doc
§5.2 reserves `persona`, `sexual`, `skills`, `equipment`, `buffs`, and `relations` on
`LivingEntity` for the *handlers* that later changes mount there (`PersonaStore`, `SexualState`,
`SkillHandler`, `EquipmentHandler`, `BuffHandler`, `RelationHandler`). Assigning raw dicts to those
names would collide with every one of those changes and leave two representations of the same data.

The loader therefore follows the storage convention change 3 established for `disguised_stats`:
validated-but-uninterpreted payload goes to the private `entity.db.*` backing store, and each
owning change mounts its handler on the public name to read from there.

```python
entity.db.persona = record["persona"]                      # opaque; stored, never interpreted
entity.db.sexual = record["sexual_baseline"]               # raw dict; change 7 builds SexualState from it
entity.db.skills = {"active": record["skills"], "passive": record["passives"]}
entity.db.equipment = record["equipment"]
entity.db.disguised_stats = record["disguised_stats"] or None
entity.db.inventory = record["inventory"]
```

Note that "frozen" applies to `CHARACTER_SCHEMA_V1` — the on-disk record shape handed to the
external importer author — not to where `loader.py` privately stashes the data afterwards. No
external party observes or depends on these attribute names.

`inventory` was not declared as a seam attribute by change 3 (§5.2's handler list is `traits` /
`sexual` / `buffs` / `equipment` / `skills` / `relations` / `persona` — no separate inventory
handler; change 5's roadmap content explicitly covers "equipment slots, inventory" together). This
needs **no edit to change 3's typeclass** — `entity.db.inventory` uses Evennia's always-available
free-form attribute store, the identical mechanism change 3 itself used for `disguised_stats`. No
cross-change file modification is required to add this.

None of these five lines does anything beyond storing data — no skill-effect resolution, no
equipment-slot validation, no `SexualState` construction. That behavior belongs to changes 5, 6/7,
and 7 respectively, per this change's Non-Goals.

### D-14. `WORLD_SCHEMA_V1` scope: a minimal, opaque "world-info entry" shape — a judgment call.

Design doc §5.3 names `WORLD_SCHEMA_V1` in the file tree but gives it no field list, no example, and
no reject/warn rows — every other piece of specificity in §5.3 is about the character schema only.
This is a genuine gap this change must resolve without inventing unbounded scope.

**Reasoning**: design doc §1 states the developer's existing raw material is "SillyTavern-style
world **and character** data" — `tmp/story_settings/` mirrors this exactly: `world_info.md`
(prose world lore) alongside `character/*.md` (character cards). Change 2 (`lore-world-data`, D9)
already established that *mechanical* world truth (`RaceProfile`, `GuildRank`, etc.) is
Python-authored, not imported — so `WORLD_SCHEMA_V1` cannot legitimately be "a JSON way to define
races" without contradicting D9. What plausibly remains is *narrative* world content: supplementary
lore/flavor entries (à la a SillyTavern "World Info"/lorebook entry) consumed by the generative
layer (§7) as prompt material, structurally opaque the same way `persona` is.

**Decision**: `WORLD_SCHEMA_V1` validates a minimal, opaque entry:

```python
WORLD_SCHEMA_V1 = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "WORLD_SCHEMA_V1",
    "type": "object",
    "required": ["record_type", "schema_version", "key", "content"],
    "properties": {
        "record_type": {
            "const": "world_entry",
            "description": (
                "Required discriminator (see D-1). Must be the literal "
                "string 'world_entry' -- this is what tells validate.py to "
                "apply WORLD_SCHEMA_V1 instead of CHARACTER_SCHEMA_V1, "
                "explicitly, rather than by guessing from which other "
                "fields happen to be present."
            ),
        },
        "schema_version": {"const": 1},
        "key": {"type": "string", "minLength": 1},
        "display_name": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "content": {
            "type": "string",
            "minLength": 1,
            "description": (
                "Opaque narrative flavor text for the generative layer "
                "(design doc S7) only. Never a source of mechanical truth "
                "-- world/lore/ (change 2, D9) is the sole authority for "
                "anything the rules engine reads. This field is never "
                "parsed or interpreted, only stored and later injected "
                "into a prompt, the same treatment CHARACTER_SCHEMA_V1 "
                "gives 'persona'."
            ),
        },
    },
    "additionalProperties": False,
}
```

No age gate (no age concept applies), no registry cross-checks — `key` uniqueness across a batch is
the only semantic-layer check `validate.py` performs for this schema, REJECT on collision.
`schema_version` being present on both schemas (matching the character example's own top-level
field) leaves room for a future `WORLD_SCHEMA_V2` without breaking existing V1 entries, should a
later change need a richer lorebook format — that expansion is explicitly not this change's job.

**Why not build more now**: the task framing caps this change at one working day; building a real
lorebook subsystem (trigger keywords, activation conditions, priority ordering — the kind of
machinery a full SillyTavern World Info implementation would need) would both blow that budget and
risk duplicating whatever change 20/21 (`scenario-director`/`scene-builder`) eventually need from
generative-layer content, which have not been designed yet either. Keeping `WORLD_SCHEMA_V1` this
narrow means it can be extended later without this change having guessed wrong about a large
surface.

### D-15. The reference example: one valid, adult, fully-typed elf card.

`world/imports/examples/example_character.json` — `record_type: "character"` (per D-1's
discriminator), age 22, apparent_age 22 (comfortably adult, not boundary-testing 18, so the example
itself never looks like it's probing the edge), `race: "elf"`,
`subrace: "ciaran"` (exercising the subrace cross-check, D-10), `stats` with all eight keys set
(exercising both the literal-value path and the "every key present" case for `loader.py`'s merge
logic, D-12), `disguised_stats` a proper subset of `stats`' keys, `skills`/`passives` non-empty
(exercising the pluggable check, D-5, in its degraded/warning state as authored — no
`world/skills/registry.py` exists yet), a fully-typed `sexual_baseline` with `arousal`, `virgin`,
and `sensitivity` set (matching §5.3's own example shape) plus `wetness` set to demonstrate an
optional field passing validation, and an opaque `persona` with the six sub-keys §5.2's
`PersonaStore` description implies (`identity`, `personality`, `life_story`, `habit`, `appearance`,
`social_connection`) populated with placeholder-but-non-empty content, never inspected by any test
beyond "is this a dict."

A permanent test (`test_reference_example_is_valid`) loads this file and asserts zero rejections and
zero warnings — the example is not just illustrative, it is itself a fixture the schema's own test
suite depends on, so a future schema edit that accidentally breaks the example is caught
immediately rather than discovered by the import implementer.

## Risks / Trade-offs

- **[Risk] The pluggable skill-check (D-5) could stay a WARNING forever if change 5's implementer
  places `SKILL_REGISTRY` at a different module path than the one this change forward-declares, or
  if it lands with a broken/empty registry that still leaves every key unverified.** → Mitigation:
  the exact path (`world.skills.registry.SKILL_REGISTRY`) is recorded in this design doc and in
  `validate.py`'s own docstring; the self-arming landing test (D-5) skips today and actively asserts
  REJECT-on-unknown-key the moment the real module exists, so a change 5 that lands without genuine
  skill-key enforcement fails that test in CI rather than silently shipping as "done."
- **[Risk] An importer author could run the CLI while the skill-registry check is degraded, see a
  clean report, and ship a batch that starts failing later with no visible cause once change 5
  lands.** → Mitigation: the CLI's degraded-mode banner (D-5) prints prominently, every run, whenever
  any check — currently only skill-registry — is not being enforced, naming which check and why,
  so "clean report" and "fully enforced" are never confused with each other.
- **[Risk] `world/lore/sexual_vocab.py`'s ownership could be missed by whoever proposes change 7,
  who might redefine the ladder inline instead of importing this module, causing drift between two
  copies of the same five-level list.** → Mitigation: flagged explicitly here (D-6) and in this
  change's proposal.md; the module's own docstring states the expectation directly, so a change-7
  author reading the codebase (not just this design doc) still sees the pointer.
- **[Risk] `WORLD_SCHEMA_V1`'s scope (D-14) is a judgment call the design doc does not specify —
  a future change needing richer world-info content (trigger keywords, activation priority) will
  find this schema too thin.** → Accepted trade-off, documented explicitly rather than guessed past
  silently; `schema_version` leaves room for a `WORLD_SCHEMA_V2` without breaking V1 entries.
- **[Risk] The `jsonschema` package is a new dependency not yet present in the project.** →
  Mitigation: flagged in proposal.md's Impact section and here; a task requires the implementer to
  add and pin it before this change's tests can run, mirroring change 1/2/3's own "verify before
  trusting" discipline for their respective new-dependency or new-hook assumptions.
- **[Risk] A future edit to `loader.py` could apply a skill multiplier "for convenience" when
  populating `entity.traits`, reintroducing the exact `88000`-instead-of-`88` error change 3's D-7
  already fixed once.** → Mitigation: D-12's test (task 6.4) asserts every loaded trait value
  equals the literal imported number or the race floor, never a scaled value; `loader.py` contains
  no multiplication of a stat value anywhere, matching change 3's own regression-test pattern for
  the identical boundary.
- **[Risk] All-or-nothing at the loader level (D-11) means a single malformed record in a large
  batch blocks every other, individually-valid record in that same batch, which could be operator-
  unfriendly for a big import run.** → Accepted: this is §5.3's explicit requirement ("Import is
  all-or-nothing... No partial import"), not an implementation choice this change is free to relax.
  An operator who wants partial progress can invoke `validate.py`/`loader.py` per-file or in smaller
  batches; that is a workflow choice, not a contract change.
- **[Risk] `entity.db.inventory` (D-13) is an ad hoc raw attribute with no formal seam declaration
  anywhere, unlike `equipment`/`skills`/`persona`/`sexual`, which could make it easy for change 5 to
  overlook when it builds the real inventory system.** → Accepted and documented explicitly (D-13);
  no change-3 file edit is required or made by this change, and change 5's own roadmap content line
  ("equipment slots, inventory") already names inventory as its concern, so the naming is not novel
  to this change, only the raw storage location during the gap before change 5 lands.

## Migration Plan

Not applicable in the backward-compatibility sense — the project is unreleased with zero users, and
`world/imports/` currently contains no code beyond change 1's empty stub. The only sequencing
concern is operational: this change must land after change 3 (needs `LivingEntity`/`PlayerCharacter`
/`NPC`, `race_floor()`, and the seam-attribute conventions importable) and should land before or
alongside changes 5/6/7, whose registries/modules this change forward-declares expectations for
(D-5, D-6) without requiring their code to exist yet.

## Open Questions

- **Should `WORLD_SCHEMA_V1` eventually grow trigger-keyword/activation-priority fields, matching a
  fuller SillyTavern-style World Info entry?** Left as an open question for whoever next touches
  world-info import — this change deliberately keeps the schema minimal (D-14) rather than guessing
  at a shape no roadmap change has designed yet.
- **Exact `jsonschema` version pin and any draft-2020-12 support caveats** are left to the
  implementer to confirm against whatever Python/dependency toolchain change 1 established, the same
  verification discipline changes 1–3 already apply to their own new-dependency assumptions.
- **Who owns defaulting `wetness`/`shame`/`exposure`/`climax_phase` when a card omits them?** This
  change deliberately leaves them absent-if-absent in `entity.sexual`'s stored raw dict (D-7) rather
  than inventing a default level; change 7 (`sexual-state`) is the natural owner of that decision
  since it is the same change that decides `SexualState`'s initial-condition semantics generally.
