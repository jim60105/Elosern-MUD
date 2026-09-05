# Delta spec: import-loader (profession-import-assembly)

Adds profession-driven assembly to the loader, and widens the literal-stats requirement by exactly
one exception: a profession's default tier may seed traits only when the record declares no
literal stats.

## MODIFIED Requirements

### Requirement: Loaded trait values are the literal imported stats, merged onto the race floor for omitted keys, never re-derived or multiplied
`loader.py` SHALL construct traits from `race_floor(RACE_REGISTRY[race])` updated by the record's
literal `stats`, with no skill multipliers, no profession multipliers, and no re-derivation. The
sole tier influence allowed: when the record declares `profession` whose registry row carries a
non-null `default_tier` AND the record's own `stats` is empty, trait construction SHALL route
through the race-baseline tiered construction (`initial_trait_config(race, subrace, tier)`)
instead of the plain race floor. A record declaring any literal stat keeps those literal values
unchanged, and a record without `profession` (or with a null-tier row) SHALL construct traits
byte-identically to the pre-change loader.

#### Scenario: Literal stats beat any profession tier
- **WHEN** a record with `"profession": "merchant"` (row tier non-null) also declares literal
  `stats` values
- **THEN** the constructed entity's traits equal the literal values merged onto the race floor,
  exactly as before the profession field existed

#### Scenario: Empty stats with a tiered profession use the tiered baseline
- **WHEN** a record declares `profession` naming a row whose `default_tier` is a real tier key and
  declares `"stats": {}`
- **THEN** the constructed traits equal `initial_trait_config(race, subrace, tier)` for that tier

#### Scenario: No profession means no behavior change
- **WHEN** a record omits `profession`
- **THEN** trait construction is byte-identical to the pre-change loader for the same record

## ADDED Requirements

### Requirement: A profession-bearing NPC record assembles blueprint components with explicit precedence
When a validated NPC record declares `profession`, `loader.py` SHALL attach, inside the record's
construction transaction, every component of the profession blueprint that the record does NOT
list explicitly in its own `components` (blueprint minus explicit types — an explicit entry of the
same type replaces the blueprint entry entirely, design D5). Component kwargs SHALL come only
from authored sources: the record's explicit `components` entry kwargs, or — for a
blueprint-only component — the record's kwargs under the same type key. When a blueprint
component's identity kwargs (any of `service_id`, `shop_key`, `branch_key`, `dialogue_key`)
cannot be fully supplied from authored record data, the WHOLE batch SHALL be rejected with a named
issue; the loader SHALL NEVER invent or default an identity value. Assembly SHALL attach through
the same component-attach path `world/rules/guild_economy.py`'s sync uses, and an
absent-`profession` record SHALL construct byte-identically to the pre-change loader.

#### Scenario: Blueprint minus explicit components
- **WHEN** a record declares a profession whose blueprint carries `guild_staff` and
  `scripted_dialogue`, and its own `components` lists a `guild_staff` entry with full kwargs
- **THEN** the constructed NPC carries the record's `guild_staff` kwargs, plus the blueprint's
  `scripted_dialogue` component (kwargs from the record's same-type entry if present), and no
  second `guild_staff`

#### Scenario: Missing identity kwargs reject the batch instead of guessing
- **WHEN** a record declares `"profession": "merchant"` with no `components` entry supplying the
  `merchant` component's `service_id` and `shop_key`
- **THEN** the batch is rejected naming the record, the component, and the missing kwargs, and no
  entity persists

#### Scenario: Assembly rides the import transaction
- **WHEN** component attachment fails midway (e.g. a duplicate component slot)
- **THEN** `load_batch` persists nothing for the whole batch, matching the existing
  all-or-nothing contract

### Requirement: A blueprint schedule template is applied to assembled NPCs only
When the profession row's `schedule_template` is non-null and the constructed entity is an `NPC`,
the loader SHALL store the template-reference schedule (`{"schema_version": 1, "template": <key>}`)
through `world/rules/npc_schedules.py::set_npc_schedule` inside the same transaction; a null
template applies no schedule; the shipped professions (all null templates) therefore change
nothing for shipped records.

#### Scenario: A tiered-and-scheduled profession schedules the NPC
- **WHEN** a test profession row carries `schedule_template: guard` and a record uses it
- **THEN** the constructed NPC carries the validated template-reference schedule for `guard`

#### Scenario: Null template stores nothing
- **WHEN** a record uses a shipped profession (null template)
- **THEN** the NPC carries no schedule attribute and settlement skips it exactly as today
