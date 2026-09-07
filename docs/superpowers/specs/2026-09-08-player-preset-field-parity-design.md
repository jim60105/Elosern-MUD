# Player Preset Field Parity Design

Date: 2026-09-08
Status: approved by the project owner in a brainstorming session
Change split: twelve OpenSpec changes, listed with dependencies and batch order
in §10. Each is scoped to at most one engineer-workday.

## 1. Problem and current state

`world/lore/player_presets.py` predates the persona system, the sexual-state
model, the equipment-effect rulebook, and the use-driven skill lineage. Its
`PlayerPreset` dataclass carries thirteen fields:

```
key, display_name, age, apparent_age, race, subrace, allocations,
emphasis, background, active_skills, passive_skills, affinity_elements,
starting_items
```

The import card (`CHARACTER_SCHEMA_V1` in `world/imports/schema.py`) is the
project's most complete character-authoring format. Everything a preset cannot
express is a capability a hand-authored NPC has and a shipped playable
character does not.

Three concrete defects follow from the gap.

**Every preset-created character is persisted with `sex = "other"`.** The
`sex` channel is collected only on the custom path: the version-3 custom draft
requires the key, and the WebClient custom form renders the options. A preset
request never carries one — `commands/character_creation.py:164` builds
`CharacterCreationRequest(mode="preset", preset_key=...)`, and
`creation_wizard.py::_request_from_draft` does the same for a saved preset
draft. `character_creation.py:419` then normalizes the absent value through
`_validate_sex(None)`, which returns `DEFAULT_SEX`, and `world/lore/sex.py`
defines that as `"other"`. All eight shipped presets are written as women —
their `background` prose and every `affinity.yaml` stage `look_flavor` use 她 —
so the persisted value contradicts the authored identity for the whole roster.

**A preset-created character has no persona record at all.**
`preflight_character_creation` validates `background` only when
`request.mode == "custom"` and hard-writes `None` otherwise
(`character_creation.py:414-418`). In `activate_player_character`, the
`persona_record` builder has exactly two branches — a supplied persona block,
or a non-null `validated.background` — so neither fires for a preset, and
`character.attributes.add("persona", ...)` never runs. The preset's authored
`background` prose survives only as display text in
`creation_wizard.py::build_preset_cards()` (line 266) and is discarded at
activation. Consequently a preset character is invisible to the persona layer:
`world/ai/npc_dialogue.py::PLAYER_PERSONA_FIELDS` (`identity`, `appearance`,
`social_connection`) resolves to nothing, so NPCs converse with a blank slate.
A custom character is richer than a shipped signature character.

**Preset activation skips the lineage normalization the import path applies.**
`world/imports/validate.py` runs `normalize_lineage_record`
(`world/rules/progression.py:870`) before the semantic phase, closing the skill
lists over their prerequisite chain and seeding `skill_proficiency` with exact
edge values. Preset activation writes `preset.skill_lists()` verbatim and
hard-writes `skill_proficiency` as `{}`, so an imported NPC and a preset player
holding the same skill keys are not in the same state.

## 2. Decision summary

| # | Decision |
|---|---|
| D1 | `PlayerPreset` reaches field parity with the import card, minus three deliberate exclusions (§8). |
| D2 | Persona is modeled as typed frozen dataclasses whose shape mirrors `world/rules/persona.py`'s `_SUBKEY_ORDER`, not an opaque dict. |
| D3 | The preset's top-level `background` field is absorbed into `PresetPersona.background`; `PresetCardView`'s wire shape is unchanged. |
| D4 | Preset-mode `sex` is resolved from the preset in the same preflight branch that resolves name/age/race. Custom mode is untouched. |
| D5 | Declared equipment is applied through `world/rules/equipment.py::toggle_equipment` (line 531), never by writing `db.equipment` directly. |
| D6 | Preset activation adopts the import path's lineage closure and proficiency seed. |
| D7 | Lore validates identity, vocabulary, and shape. Bounds derived from rules constants are validated at rules-module import time, so `world/lore/` never imports `world/rules/`. |
| D8 | All new fields default to empty. Except for `sex` and the existence of a persona record, the field-parity changes alter no observable starting state. |
| D9 | The eight shipped cards receive only mechanical edits across the field-parity changes: `sex="female"`, and the existing `background` string moved into `PresetPersona`. Persona prose is authored later by the project owner as pure data. |
| D10 | A docsify authoring guide ships as its own change, `preset-authoring-guide` (§6, §10). |
| D11 | `sex` is a required keyword argument on `PlayerPreset`, so omitting it on a new card fails at construction rather than silently defaulting (§3.2). |

## 3. Data model (lore layer)

`world/lore/player_presets.py` gains four frozen dataclasses whose shapes are
exactly what `PersonaStore` and the sexual-state builder already read.

```python
@dataclass(frozen=True)
class PresetIdentity:
    """The two identity layers PersonaStore renders (公開身分／隱秘身分)."""
    public: str
    hidden: str = ""          # omitted from the record when empty


@dataclass(frozen=True)
class PresetAppearance:
    """The seven appearance sub-keys declared in persona.py::_SUBKEY_ORDER."""
    height: str = ""
    weight: str = ""
    measurement: str = ""
    style: str = ""
    overview: str = ""
    attire: str = ""
    feature: str = ""


@dataclass(frozen=True)
class PresetPersona:
    """One preset's authored persona, in import-card record shape."""
    identity: PresetIdentity = PresetIdentity(public="")
    personality: str = ""
    life_story: str = ""
    habit: str = ""
    appearance: PresetAppearance = PresetAppearance()
    social_connection: tuple[tuple[str, str], ...] = ()   # name -> relationship
    background: str = ""

    def to_record(self) -> dict[str, Any]:
        """Return the storage shape written to ``character.db.persona``.

        All six ``PERSONA_IMPORT_CARD_KEYS`` are always present (``""`` for
        unauthored prose, ``{}`` for unauthored structured keys), matching what
        custom activation and ``persona_edit`` already produce; an empty
        ``identity.hidden`` is dropped, and ``background`` appears only when
        non-empty.
        """


@dataclass(frozen=True)
class PresetSexualBaseline:
    """One preset's authored sexual baseline, in import-card record shape."""
    arousal: str
    virgin: bool
    sensitivity: tuple[tuple[str, str], ...]
    wetness: str = ""
    shame: str = ""
    exposure: str = ""
    climax_phase: str = ""

    def to_record(self) -> dict[str, Any]: ...
```

Every mutable container is expressed as a tuple of pairs so the registry stays
hashable and immutable; `to_record()` is the single place that expands them.

`PlayerPreset` gains five fields and loses one:

```python
sex: str                                             # a SEX_VALUES member
persona: PresetPersona = PresetPersona()
sexual_baseline: PresetSexualBaseline | None = None  # None keeps today's lazy default
starting_equipment: tuple[str, ...] = ()             # subset of starting_items
disguised_stats: tuple[tuple[str, int], ...] = ()
skill_proficiency: tuple[tuple[str, float], ...] = ()
# removed: background  (absorbed into persona.background)
```

`emphasis` stays a top-level field: it describes the allocation shape for the
selection card and has no persona counterpart.

### 3.1 Validation split (D7)

`world/lore/player_presets.py` already imports `world/lore/*` and
`world/skills/registry.py` and imports nothing from `world/rules/`;
`world/rules/character_creation.py` imports the preset registry. That direction
must not be reversed, so validation is split by which constant a rule needs.

Lore-side, in the style of the four validators that already run at module
import:

- `sex` is a `SEX_VALUES` member (`world/lore/sex.py`).
- Every `sexual_baseline` level is a member of its tuple in
  `world/lore/sexual_vocab.py`; `sensitivity` body-part keys come from
  `BODY_PARTS` plus `GENERIC_BODY_PART`.
- Every `skill_proficiency` key resolves in `SKILL_REGISTRY` and its value is a
  non-negative real number.
- Every `disguised_stats` key is a string and its value an `int`. No axis
  whitelist: `CHARACTER_SCHEMA_V1` constrains this field the same way
  (`additionalProperties: {"type": "integer"}`), and parity is the point.
- Every `starting_equipment` key appears in `starting_items` and its
  `ItemDefinition.equipment_slot` is not `None` (`world/lore/items.py`).

Rules-side, as a load-time sweep over `PLAYER_PRESET_REGISTRY` in the module
that owns the constant:

- Every persona prose string is at most `MAX_PERSONA_FIELD_LENGTH`
  (`character_creation.py:143`, 600). The sweep lives in
  `world/rules/character_creation.py` and raises at import, so an over-long
  field fails the server start exactly as a bad skill kit does today.

`preset-companion-model` adds two more entries to the rules-side sweep for the
same reason.

### 3.2 Field ordering

`PlayerPreset` uses `dataclasses.KW_ONLY` from the first new field onward:
`sex` is a **required keyword argument**, so a new card that omits it fails at
construction instead of silently inheriting `DEFAULT_SEX` — the exact defect
`preset-sex-field` exists to close. Removing the positional `background` slot in
`preset-persona-model` also
means the eight cards must pass `active_skills`, `passive_skills`,
`affinity_elements`, and every new field by keyword. All eight are edited in
those two changes, so the transition is mechanical and the tests catch a miss.

## 4. Activation writes (rules layer)

`activate_player_character` changes in six places.

| Attribute | Today | After |
|---|---|---|
| `sex` | `_validate_sex(request.sex)`; always `"other"` for a preset | preflight's preset branch resolves `preset.sex` alongside name/age/race; both branches still flow through `_validate_sex` |
| `persona` | never written for a preset | one `_persona_record_for(...)` helper: preset uses `preset.persona.to_record()`, custom keeps today's prose-plus-background logic |
| `skills` / `skill_proficiency` | `preset.skill_lists()`; `{}` | `lineage_ownership_closure()` then `seed_lineage_proficiency()` (`progression.py:809`, `762` — the same two functions `normalize_lineage_record` composes), with the preset's declared `skill_proficiency` winning over a seeded value |
| `disguised_stats` | not written | `dict(preset.disguised_stats) or None`, mirroring the loader's `record["disguised_stats"] or None` |
| `sexual` | not written | written only when the preset declares a baseline; otherwise absent, so `SexualState` keeps applying `_generic_default_baseline()` lazily |
| `equipment` | hard-written four-slot all-`None` shape | the same shape is still written as the base, then — after `inventory` is written — each `starting_equipment` key is applied through `toggle_equipment(character, key)` inside the same transaction |

### 4.1 Rollback surface

This is the change's sharpest edge. `toggle_equipment` mutates traits (through
`sync_equipment_gauge_limits`) and the `buffs` attribute; its own
snapshot/restore protects only its own nested transaction. When the outer
activation fails, the idmapper attribute cache is not transaction-aware, so a
rolled-back write is still readable in-process.

`_CREATION_ATTRIBUTE_KEYS` (`character_creation.py:25`) must therefore gain
`disguised_stats`, `sexual`, and `buffs`. Traits are already covered by the
existing `trait_snapshot` / `restore_traits` pair. A dedicated test drives a
failure after the equipment toggles and asserts every one of these surfaces is
restored.

### 4.2 Unchanged

`finalize_player_portrait` (`character_creation.py:431`) and its post-commit
portrait ensure are untouched: they already run unconditionally for both modes.
Custom-mode creation, the WebClient creation actions, the Telnet wizard, and
the import path are all untouched.

## 5. Minimal content and default semantics (D8, D9)

The eight shipped cards receive two mechanical edits each — `sex="female"`, and
the existing `background` string moved into `PresetPersona(background=...)`.
Everything else takes its default:

| Default | Resulting behavior |
|---|---|
| persona keys empty | `to_record()` omits them; a valid but sparse record is written |
| `sexual_baseline=None` | `db.sexual` absent; `SexualState` applies `_generic_default_baseline()` exactly as today |
| `starting_equipment=()` | nothing is toggled; every starting item stays in the pack, as today |
| `disguised_stats=()` | `None` is written, which every reader already treats as absent |
| `skill_proficiency=()` | only the lineage seed is written |

So the whole observable delta of the field-parity changes is: preset characters are `female`
instead of `other`, and they now own a persona record. Every validator accepts
empty values, so the owner can fill fields later as pure data edits with no
code change.

## 6. Documentation deliverable (D10)

New page `docs/development/adding-player-presets.md`, titled 新增角色模板指南,
registered in `docs/_sidebar.md` under 開發者指南 after 新增物品指南. Traditional
Chinese, structured after `docs/development/adding-items.md`:

1. Where a preset's data lives — the field-group table, and how the preset,
   custom-creation, and JSON-import paths differ (in particular: presets
   declare *allocations*, the import card declares *absolute stats*, and that
   difference is deliberate).
2. Decisions to make first — race/subrace, allocation budget, whether the skill
   kit touches a lineage prerequisite, whether the card needs a hidden identity
   layer.
3. Step by step — read the bounds from `resolve_starting_profile()`; write the
   registry entry; author the seven persona keys; declare the skill kit and
   what the lineage closure adds for you; declare starting items and the
   equipped subset; declare the sexual baseline and disguised stats; read the
   load-time validator messages; add tests.
4. Common mistakes — an elf card must declare an empty `affinity_elements`; the
   divine-arts race gate; exceeding the allocation budget; a
   `starting_equipment` key absent from `starting_items`; a persona field over
   600 characters; a duplicate `starting_items` key.
5. When this guide is not enough — pointers to 新增物品指南, 新增魔法指南, and
   `docs/gm/characters.md` for the JSON import path.

The guide lives under `development/` rather than `gm/` because adding a preset
is a code change; `docs/gm/characters.md` documents the JSON path that is not.

## 7. Testing

- `world/lore/tests/test_player_presets.py` — five lore-side validator groups
  (sex vocabulary, sexual vocabulary, `starting_equipment` subset and slot
  rule, `skill_proficiency` keys and sign, `disguised_stats` types), in the
  style of the existing `_validate_preset_*` tests, plus a construction test
  asserting a card omitting `sex` raises (D11).
- `world/rules/tests/test_character_creation.py` — the rules-side load-time
  sweep rejects a preset whose persona prose exceeds
  `MAX_PERSONA_FIELD_LENGTH` (§3.1); a preset activation writes the right
  `sex`; a persona record exists and is import-card shaped; the lineage closure
  and proficiency seed are applied; declared equipment is worn and gauge limits
  synced; **a failure after the equipment toggles restores `equipment`,
  `buffs`, traits, `disguised_stats`, and `sexual`**.
- `world/rules/tests/test_persona.py` — `PresetPersona.to_record()` output
  flattens correctly through `PersonaStore.flatten()` and `public_view()`,
  including pruning of `identity.hidden`.
- `world/rules/tests/test_creation_wizard.py` — `build_preset_cards()` reading
  `persona.background` produces an unchanged `PresetCardView`, protecting the
  WebClient wire contract.

The field-parity changes add no new test module, so `.github/evennia-shards.json`
is untouched by them. `preset-companion-model` adds
`world/rules/tests/test_starting_companions.py` and `preset-authoring-guide` may
add a contract module; each registers its module in exactly one shard in its own
change (§10.5).
`tests/test_creation_parity_contract.py::test_sex_values_and_default_mirror_across_python_and_js`
must stay green: no change here adds to or alters
`SEX_VALUES` or `DEFAULT_SEX`.

## 8. Non-goals

Three import-card fields are deliberately not mirrored.

**Absolute `stats`.** Presets declare allocations so they stay bound by
`resolve_starting_profile()`'s per-race bounds and budget. Absolute values would
let a preset bypass creation balance. This is a deliberate difference, not debt.

**`title`.** `npc_title` is an `AttributeProperty` on `NPC` alone, and
`world/imports/loader.py` states the field "takes effect only for NPC imports".
Player titles are earned through `world/lore/titles.py` with basis quotes.
Seeding a starting title is a separate feature with its own rules.

**`profession` / `components` / `anchor_room`.** These assemble NPC service
hosts (shops, guild windows). A player character has no sink for them.

Also out of scope: authoring the persona prose for the eight cards (D9), any
change to custom creation, any change to the import path, and any change to the
portrait prompt (`portrait-prompt-appearance`, §10).

## 9. Incidental observations

Recorded, not fixed by any of the twelve changes:

- `PERSONA_IMPORT_CARD_KEYS` is defined twice, at
  `world/rules/character_creation.py:136` and
  `world/rules/persona_edit.py:28`. One should import the other.
- `world/art/subjects.py::character_description` (line 212) deliberately
  excludes persona text from the portrait prompt (design D6), so enriching
  `appearance` has no effect on generated art until `portrait-prompt-appearance`
  lands. This is a
  boundary, not an oversight.

## 10. Change decomposition, dependencies, and batch order

The design ships as twelve OpenSpec changes under `openspec/changes/`, each
scoped to at most one engineer-workday. All twelve validate `--strict`. The
decomposition was revised after a rubber-duck review; §10.6 records what that
review caught.

### 10.1 The changes

| # | Change | Layer | Est. | Delta specs |
|---|---|---|---|---|
| 1 | `preset-sex-field` | lore + preflight | ~4h | `player-character-creation` (A+M), `entity-sex-vocabulary` (M) |
| 2 | `preset-persona-model` | lore + card/screen sources | ~6h | `player-character-creation` (A) |
| 3 | `preset-persona-activation` | rules | ~4h | `player-character-creation` (A), `creation-persona-persistence` (M) |
| 4 | `preset-value-resolver` | rules refactor | ~2h | `player-stat-allocation` (M) |
| 5 | `preset-lineage-and-proficiency` | lore + rules | ~5h | `player-character-creation` (M), `skill-lineage` (M) |
| 6 | `preset-starting-equipment` | lore + rules | ~7h | `player-character-creation` (M) |
| 7 | `preset-disguise-and-sexual-baseline` | lore + rules | ~5h | `player-character-creation` (A), `disguised-stats-boundary` (M), `sexual-state-handler` (M) |
| 8 | `affinity-seed-writer` | rules | ~3h | `affinity-system` (M) |
| 9 | `preset-companion-model` | lore + new rules module | ~6h | `starting-companions` (new) |
| 10 | `preset-companion-activation` | rules | ~5h | `starting-companions` (A), `party-system` (M) |
| 11 | `preset-authoring-guide` | docs | ~4h | `preset-authoring-docs` (new) |
| 12 | `portrait-prompt-appearance` | art + prompts | ~5h | `art-subject-model` (M) |

(A) = ADDED requirements, (M) = MODIFIED requirements.

Change 6 carries a `design.md` because widening the activation rollback surface
is the riskiest single step; the others record their decisions in `proposal.md`.

Changes 4 and 8 exist only because the review found changes 9 and 10 over a
workday. Change 4 pulls the `resolve_preset_values` extraction out of the
companion work so a behavior difference in that refactor is attributable on its
own; change 8 pulls the affinity seed writer out so a change to the affinity
capability's sole-writer contract is reviewed and tested in isolation rather
than buried inside a companion feature.

### 10.2 Logical dependencies

```
 1 ──▶ 2 ──▶ 3 ──▶ 12
 1 ──▶ 5
 1 ──▶ 6
 1 ──▶ 7
 2 ──▶ 9 ──▶ 10
 4 ──▶ 9
 8 ──▶ 10
 1,2,5,6,7,9 ──▶ 11
```

- **2 → 1**: change 1 introduces the `KW_ONLY` marker change 2 builds on, and
  both edit every card literal.
- **3 → 2**: activation cannot write a persona the registry cannot express.
- **9 → 2, 4**: the companion's persona is the partner preset's `PresetPersona`,
  and its trait values come from the extracted resolver.
- **10 → 9, 8**: the binding needs the builder and the seed writer.
- **12 → 3**: the portrait prompt reads `entity.db.persona`, which for a preset
  character only exists once change 3 lands.
- **11 → the field changes**: the guide documents the final field set, so writing
  it earlier guarantees it ships stale.

Changes 4, 5, 6, and 7 have **no logical dependency on each other**; their order
among themselves is free. Change 10 has no logical dependency on change 3 —
the companion's persona comes from `to_record()`, not the player-side record
builder — but the two edit the same function (§10.3).

### 10.3 Code conflicts

Two files are the serialization points. Changes sharing a cell cannot run in
parallel regardless of their logical independence.

| File | Touched by |
|---|---|
| `world/lore/player_presets.py` | 1, 2, 5, 6, 7, 9 |
| `world/rules/character_creation.py` | 1, 2, 3, 4, 5, 6, 7, 10 |
| `world/rules/creation_wizard.py`, `commands/character_creation.py` | 2 |
| `world/rules/starting_companions.py` (new) | 9, 10 |
| `world/rules/affinity.py` | 8 |
| `world/art/subjects.py`, `prompts/art.yaml`, `world/prompts/registry.py` | 12 |
| `docs/`, contract tests | 11 |
| `.github/evennia-shards.json` | 9, possibly 11 |

Changes 8, 11, and 12 touch neither serialization point and are the only ones
freely schedulable.

### 10.4 Recommended batch order

| Batch | Changes | Rationale |
|---|---|---|
| 1 | **1 ‖ 8** | Foundation plus the fully independent affinity primitive |
| 2 | 2 | Persona model; the largest card edit, and the one with the most consumers |
| 3 | 3 | Activation writes the persona — unblocks 12 |
| 4 | **4 ‖ 12** | Disjoint files (`character_creation.py` vs `art/subjects.py`) |
| 5 | 5 | Lineage closure and proficiency |
| 6 | 6 | Rollback-surface widening; the riskiest step, run alone |
| 7 | 7 | Disguise and sexual baseline |
| 8 | 9 | Companion model and builder |
| 9 | **10 ‖ 11** | Disjoint files (rules vs docs) |

Three batches admit a second engineer. The critical path is
1 → 2 → 3 → 4 → 5 → 6 → 7 → 9 → 10, about 44 hours (roughly five and a half
engineer-days) with 8, 11, and 12 absorbed into the parallel slots.

Changes 4, 5, 6, and 7 may be reordered freely among batches 4-7; they are
serialized only by `world/rules/character_creation.py`. Splitting that file
first would collapse four batches into one.

### 10.5 Cross-cutting obligations

Every change carries these in its own `tasks.md`; they are listed here so a
reviewer can check them at a glance.

- Each new main-spec requirement needs a `covers_requirement` annotation on a
  real behavior test, with IDs from
  `uv run --locked python -m tools.spec_traceability list` — never
  hand-constructed.
- Change 9 adds `world/rules/tests/test_starting_companions.py` and change 11
  may add a contract module; each MUST be registered in exactly one shard of
  `.github/evennia-shards.json` **in the same change**, or
  `tests.test_evennia_test_optimization_contract` fails on every later branch.
- Changes 8, 9, and 10 add observability events and must pass
  `uv run --locked python -m tools.observability_lint check`.
- `tests/test_creation_parity_contract.py` must stay green throughout; no change
  here adds to or alters `SEX_VALUES` or `DEFAULT_SEX`.
- Every `## MODIFIED Requirements` block reproduces its source requirement in
  full, scenarios included — see §10.6.
- No change adds a backward-compatibility layer or data migration: the project
  has no released users.

### 10.6 What the rubber-duck review caught

Recorded because three of the defects were the same mistake, and the pattern is
easy to repeat.

- **A removed field had an unaccounted-for consumer.** Change 2 deletes
  `PlayerPreset.background`, and `commands/character_creation.py::creation_start_screen()`
  reads it directly — the first screen every pending player sees, reused by
  `Account.at_post_login`. Two existing tests assert on it. The change now names
  the module, both tests, and a repo-wide grep for a third consumer.
- **An ADDED requirement contradicted an existing scenario.** The main spec's
  "Character creation enforces canonical identity and registry compatibility"
  carries a scenario asserting *"a preset-mode activation... holds `DEFAULT_SEX`
  (the preset catalog declares no sex)"*. Change 1 originally only ADDED a
  requirement saying the opposite, which would have archived two contradictory
  requirements into the same spec. It now also MODIFIES that requirement.
- **Two MODIFIED blocks silently dropped scenarios.** The affinity delta kept 3
  of 10 scenarios and the disguise delta kept 2 of 3, losing documented
  guarantees (`quest_completion` bypassing the daily cap, negative deltas never
  restoring budget, source and non-NPC rejection, promotion using canonical
  state) that neither change was touching. Both now reproduce their source block
  verbatim. **When writing a MODIFIED delta, extract the whole requirement block
  programmatically — a paged `sed` range is how all three of these were
  truncated.**
- **Two changes were over a workday**; changes 4 and 8 were split out (§10.1).
- Smaller corrections folded in: the companion is explicitly untitled (a stated
  non-goal rather than an oversight); a same-account test where one character is
  literally named 悠奈 while another's companion is also 悠奈; the guide's
  field-coverage test requires an inline-code span so short names like `key` or
  `age` cannot pass incidentally; and change 2 records *why* the card-blurb bound
  is a contract test rather than a load-time validator (the constant lives in the
  web layer, which neither lore nor rules may import).
