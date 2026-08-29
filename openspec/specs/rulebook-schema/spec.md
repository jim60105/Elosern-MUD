# rulebook-schema Specification

## Purpose
TBD - created by archiving change buffs-rulebook. Update Purpose after archive.
## Requirements
### Requirement: Every rule carries a required, unique ID
`world/rules/rulebook/schema.py` SHALL define a `Rule` type with a required `id` field, and
`load_rules()` SHALL raise when loading a YAML file containing a rule with a missing or duplicated
`id`. No rule table under `world/rules/rulebook/` SHALL be loadable with an unidentified or
ambiguously-identified rule.

#### Scenario: A rule missing an id fails to load
- **WHEN** `load_rules()` is called against a YAML file containing a rule entry with no `id` key
- **THEN** it raises, naming the file and the entry's position, rather than silently assigning a
  generated ID or skipping the entry

#### Scenario: A duplicated id within one file fails to load
- **WHEN** `load_rules()` is called against a YAML file containing two entries sharing the same `id`
- **THEN** it raises, naming the duplicated `id`, rather than silently keeping only the first or last
  matching entry

#### Scenario: A well-formed rule file loads successfully
- **WHEN** `load_rules()` is called against a YAML file where every entry has a unique, non-empty `id`
- **THEN** it returns one `Rule` per entry, each exposing `id`, `when`, and `then`

### Requirement: evaluate_condition() is the one shared matcher for event, field-threshold,
field-changed, and buff-presence conditions
`world/rules/rulebook/schema.py` SHALL provide `evaluate_condition(when, context)` recognizing exactly
these condition keys: `event` (equality against `context["event"]`), `field` combined with `equals` or
`gte` (comparison against `context[field]`), `field_changed` combined with `direction` (membership
check against `context["_changed"]`), and `buff_active` (membership check against
`context["active_buffs"]`). When a `when` block names more than one condition key, they SHALL combine
with implicit AND. This SHALL be the only condition-matching function in the project usable by any
rule table under `world/rules/rulebook/`.

#### Scenario: An event condition matches the context's event
- **WHEN** `evaluate_condition({"event": "stimulus_applied"}, {"event": "stimulus_applied"})` is
  called
- **THEN** it returns `True`

#### Scenario: An event condition does not match a different event
- **WHEN** `evaluate_condition({"event": "stimulus_applied"}, {"event": "combat_started"})` is called
- **THEN** it returns `False`

#### Scenario: A field-equals condition matches an exact value
- **WHEN** `evaluate_condition({"field": "climax_phase", "equals": "進行中"}, {"climax_phase": "進行
  中"})` is called
- **THEN** it returns `True`

#### Scenario: A field-gte condition matches against an orderable value
- **WHEN** `evaluate_condition({"field": "arousal", "gte": 3}, {"arousal": 4})` is called, using
  ordinal stand-ins for an ordered-level field
- **THEN** it returns `True`, and calling it with `{"arousal": 2}` instead returns `False`

#### Scenario: A field-changed condition matches the recorded change direction
- **WHEN** `evaluate_condition({"field_changed": "arousal", "direction": "up"}, {"_changed":
  {"arousal": "up"}})` is called
- **THEN** it returns `True`, and calling it with `{"_changed": {"arousal": "down"}}` instead returns
  `False`

#### Scenario: A buff-active condition matches a buff key present in the context
- **WHEN** `evaluate_condition({"buff_active": "poisoned"}, {"active_buffs": {"poisoned", "fear"}})`
  is called
- **THEN** it returns `True`, and calling it with `{"active_buffs": {"fear"}}` instead returns `False`

#### Scenario: Multiple condition keys in one when block combine with implicit AND
- **WHEN** `evaluate_condition({"field": "arousal", "gte": 3, "buff_active": "aroused_surge"},
  context)` is called against a context satisfying only one of the two conditions
- **THEN** it returns `False`; it returns `True` only when both conditions are individually satisfied

#### Scenario: A context missing a referenced key is treated as unsatisfied, not an error
- **WHEN** `evaluate_condition({"field": "arousal", "gte": 3}, {})` is called against a context with no
  `arousal` key at all
- **THEN** it returns `False` rather than raising `KeyError`

#### Scenario: An unrecognized condition key raises rather than silently matching or ignoring
- **WHEN** `evaluate_condition({"unknown_condition_kind": "x"}, {})` is called
- **THEN** it raises, naming the unrecognized key, rather than treating the condition as vacuously true
  or silently skipping it

### Requirement: The effect (`then`) clause is opaque to the shared schema module
`world/rules/rulebook/schema.py` SHALL treat every `Rule.then` value as an uninterpreted `dict`. No
function in this module SHALL branch on, validate, or assign meaning to any key inside `then` — that
interpretation belongs exclusively to the module owning the specific rule table (e.g.
`world/rules/combat_modifiers.py` for `combat_modifiers.yaml`).

#### Scenario: schema.py loads a rule with an arbitrary then shape without inspecting it
- **WHEN** `load_rules()` loads a rule whose `then` value is `{"agility": "-20%", "accuracy": -15}`
  and a second rule whose `then` value is `{"field": "arousal", "delta": "+1..+2"}`
- **THEN** both load successfully as opaque dicts, and no function in `schema.py` raises or behaves
  differently based on which shape of `then` either rule carries

### Requirement: schema.py documents itself as the shared engine for every rulebook table, not a
combat-modifiers-specific module
The module docstring of `world/rules/rulebook/schema.py` SHALL state explicitly that it is intended to
be imported by every declarative rule table under `world/rules/rulebook/`, naming `sexual.yaml`
(owned by a later change) as an expected future importer of `Condition`/`evaluate_condition`/
`load_rules`, rather than a module private to this change's own `combat_modifiers.yaml`.

#### Scenario: The module docstring names the expected future consumer
- **WHEN** `world/rules/rulebook/schema.py`'s module docstring is inspected
- **THEN** it states that a future sexual-state rule table is expected to import this module's
  condition grammar and loader rather than reimplementing condition matching independently

### Requirement: Equipment-worn condition values are referentially validated at load

The combat-modifier rulebook SHALL preflight every `equipment_worn`
condition at its own load site, before any rule matching or startup
mirroring: the value must be a string naming an `ITEM_REGISTRY` member that
carries an equipment slot. Unknown keys, consumable/non-slot items, and
non-string values SHALL fail loading with an identifying error; the shared
evaluator SHALL additionally raise `ValueError` on a non-string value
rather than silently mis-matching, and a condition context that lacks the
worn-item fact SHALL fail the condition closed.

#### Scenario: Typo in a grace rule fails the preflight

- **WHEN** a combat-modifier rule declares `equipment_worn:
  sister_vestmenst`
- **THEN** the combat rulebook preflight rejects it with an identifying
  error before any matching occurs

#### Scenario: Non-slot item rejected

- **WHEN** a rule declares `equipment_worn` naming a consumable item key
- **THEN** loading fails

#### Scenario: Direct evaluator misuse raises

- **WHEN** `evaluate_condition` is called directly with a non-string
  `equipment_worn` value
- **THEN** it raises `ValueError` instead of returning a match result

#### Scenario: Valid authored grace rules load

- **WHEN** the shipped rulebook with the four authored grace rules loads at
  startup
- **THEN** preflight passes and the rules are queryable through the
  matcher
