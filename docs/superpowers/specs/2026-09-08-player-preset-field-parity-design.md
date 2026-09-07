# Player Preset Field Parity Design

Date: 2026-09-08
Status: approved by the project owner in a brainstorming session
Change split: `player-preset-field-parity` (this document) →
`preset-starting-companions` (§10.1) → `portrait-prompt-appearance` (§10.2)

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
| D8 | All new fields default to empty. Except for `sex` and the existence of a persona record, this change alters no observable starting state. |
| D9 | The eight shipped cards receive only mechanical edits in this change: `sex="female"`, and the existing `background` string moved into `PresetPersona`. Persona prose is authored later by the project owner as pure data. |
| D10 | A docsify authoring guide ships with this change (§6). |
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

        Empty strings and empty containers are omitted, so a minimally
        authored preset still yields a valid import-card-shaped record.
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

`preset-starting-companions` (§10.1) adds two more entries to the rules-side
sweep for the same reason.

### 3.2 Field ordering

`PlayerPreset` uses `dataclasses.KW_ONLY` from the first new field onward:
`sex` is a **required keyword argument**, so a new card that omits it fails at
construction instead of silently inheriting `DEFAULT_SEX` — the exact defect
this change exists to close. Removing the positional `background` slot also
means the eight cards must pass `active_skills`, `passive_skills`,
`affinity_elements`, and every new field by keyword. All eight are edited in
this change, so the transition is mechanical and the tests catch a miss.

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

So the whole observable delta of this change is: preset characters are `female`
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

No new test module is added, so `.github/evennia-shards.json` needs no change.
`tests/test_creation_parity_contract.py::test_sex_values_and_default_mirror_across_python_and_js`
must stay green: this change adds a preset field and never touches
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
portrait prompt (§10.2).

## 9. Incidental observations

Recorded, not fixed by this change:

- `PERSONA_IMPORT_CARD_KEYS` is defined twice, at
  `world/rules/character_creation.py:136` and
  `world/rules/persona_edit.py:28`. One should import the other.
- `world/art/subjects.py::character_description` (line 212) deliberately
  excludes persona text from the portrait prompt (design D6), so enriching
  `appearance` has no effect on generated art until §10.2 lands. This is a
  boundary, not an oversight.

## 10. Follow-up changes

### 10.1 `preset-starting-companions`

Decided in the same session, blocked on this change:

A preset may ship with NPC companions that join the party at activation with
high affinity. 悠奈 and 悠花 declare each other symmetrically.

- Companion stats mirror the partner's own `PlayerPreset` (zero data
  duplication; the twin genuinely is that character).
- Seeded affinity is **95** — well above `invite_threshold` 70, inside 至愛,
  with headroom so one friendly-fire point does not drop a stage. `cap` stays
  at `NATURAL_CAP` 99; the `cap_breaks` milestone table is untouched.
- Name collisions take the `-{pk}` suffix, following
  `world/rules/guild_exams.py::_key_taken_by_other`.
- The companion is spawned **inside** the activation transaction; any failure
  rolls the whole creation back and deletes the partial NPC, following
  `_spawn_opponent`.
- The companion is an `LLMNPC`, so `commands/invite.py` can re-invite her after
  a dismissal.
- Layering: `PlayerPreset` gains `starting_companions: tuple[StartingCompanion, ...]`
  (`preset_key`, `affinity`, `relationship`); a new
  `world/rules/starting_companions.py` owns assembly; `world/rules/affinity.py`
  gains the seed writer so it remains the sole affinity writer;
  `world/rules/party.py::join_party` performs the binding.
- The rules-side load-time check validates `len(starting_companions) <=
  PARTY_MAX_COMPANIONS` and `affinity <= NATURAL_CAP` (the D7 seam).
- The companion's persona comes straight from the partner preset's
  `PresetPersona`, plus a `social_connection` entry naming the owning player —
  which is why this change lands first.

### 10.2 `portrait-prompt-appearance`

Whether authored `appearance` sub-keys should reach the SD WebUI prompt.
Today `character_description` uses only display name, race/subrace label, age,
and the style fragment, so two cards of the same race and age produce nearly
identical prompts. That change must address why the design D6 boundary exists,
which sub-keys may cross it, and how the hidden identity layer stays excluded.
