## ADDED Requirements

### Requirement: sexual.yaml rules share change 6's condition grammar unmodified, with a then vocabulary this change owns
`world/rules/rulebook/sexual.yaml` SHALL be loaded via `world.rules.rulebook.schema.load_rules()`,
the identical function change 6's `combat_modifiers.yaml` uses, and every rule's `when` clause SHALL
be evaluated via the identical `evaluate_condition()` function. No second condition evaluator SHALL
be authored anywhere in this change's scope. Each rule's `then` clause SHALL use a vocabulary
(`field`, `delta`, `set`, `add`, `set_from`, `part_from_context`, `irreversible`) that this change
defines and interprets in its own module, never inspected by `schema.py`.

#### Scenario: sexual.yaml loads via the shared loader with no duplicate or missing IDs
- **WHEN** `world/rules/rulebook/sexual.yaml` is loaded via `load_rules()`
- **THEN** it returns one `Rule` per entry, each with a unique, non-empty `id`, and raises nothing

#### Scenario: The same evaluate_condition() function used by combat_modifiers.yaml also evaluates sexual.yaml's rules
- **WHEN** `world/rules/sexual_state.py`'s source is inspected
- **THEN** it imports `evaluate_condition` from `world.rules.rulebook.schema` and contains no
  reimplementation of condition matching

### Requirement: apply_event() evaluates sexual.yaml against live entity state and mutates matching fields
`world/rules/sexual_state.py` SHALL provide `apply_event(entity, event, **context) -> list[str]`,
which builds a context dict from `entity.sexual`'s current field values plus any caller-supplied
context, evaluates every rule in `sexual.yaml` via `evaluate_condition()`, and applies each matching
rule's `then` clause by mutating the named `SexualState` field. Unlike change 6's `evaluate_combat_
modifiers()`, this function SHALL write entity state — it is not a pure query.

#### Scenario: A stimulus event raises arousal
- **WHEN** `apply_event(entity, "stimulus_applied")` is called on an entity whose arousal starts at
  `"平靜"`
- **THEN** `entity.sexual.arousal.level` becomes `"微興奮"` or `"中等"` (a `+1` or `+2` delta), and
  `"arousal_up_on_stimulus"` appears in the returned list of fired rule IDs

#### Scenario: A cascading field-changed rule fires within the same apply_event() call
- **WHEN** `apply_event(entity, "stimulus_applied")` raises arousal, which in turn satisfies
  `wetness_follows_arousal_increase`'s `field_changed` condition
- **THEN** both `"arousal_up_on_stimulus"` and `"wetness_follows_arousal_increase"` appear in the
  returned list of fired rule IDs from the single `apply_event()` call, and `entity.sexual.wetness`
  reflects the increase

#### Scenario: An event that matches no rule changes nothing and fires nothing
- **WHEN** `apply_event(entity, "unrelated_event")` is called
- **THEN** no field on `entity.sexual` changes, and an empty list is returned

### Requirement: climax_phase transitions are constrained to the valid cycle, enforced independently of which rule attempts the change
`climax_phase` SHALL only move between adjacent states in its defined cycle
(未達→接近→進行中→餘韻→未達, plus 餘韻→接近). A `then` clause naming any other target level for
`climax_phase` SHALL have no effect, regardless of which rule fires it.

#### Scenario: climax_gate does not regress an in-progress climax
- **WHEN** `entity.sexual.climax_phase` is `"進行中"` and an event fires that would otherwise satisfy
  `climax_gate`'s condition (arousal remains at `極限`)
- **THEN** `entity.sexual.climax_phase` remains `"進行中"`, unchanged by `climax_gate`'s `set: 接近`
  effect

#### Scenario: climax_progresses_on_continued_stimulus only fires from 接近
- **WHEN** `entity.sexual.climax_phase` is `"未達"` and `apply_event(entity, "stimulus_applied")` is
  called
- **THEN** `climax_progresses_on_continued_stimulus` does not fire, since its condition requires
  `climax_phase` to already equal `接近`

### Requirement: virginity_once is irreversible once applied
`virginity_once`'s effect on `virgin` SHALL be permanent: once `entity.sexual.virgin` becomes `False`
as a result of this rule firing, no later rule application SHALL be able to set it back to `True`.

#### Scenario: virgin stays false after the triggering event
- **WHEN** `apply_event(entity, "first_vaginal_penetration")` is called on an entity whose `virgin` is
  `True`
- **THEN** `entity.sexual.virgin` becomes `False`, and `"virginity_once"` and
  `"experience_vaginal_added"` both appear in the returned fired-rule list

### Requirement: Every rule ID in sexual.yaml has exactly one corresponding unit test
For every `Rule.id` present in `world/rules/rulebook/sexual.yaml`, `world/rules/tests/
test_sexual_state.py` SHALL define exactly one test function named `test_rule_<id>`. A regression
test SHALL mechanically verify this correspondence, mirroring change 6's identical discipline for
`combat_modifiers.yaml` and `buffs.yaml`.

#### Scenario: Every seed rule has a matching test function
- **WHEN** the mechanical correspondence check inspects `sexual.yaml`'s rule IDs against
  `test_sexual_state.py`'s test function names
- **THEN** it finds exactly one `test_rule_<id>` function for each rule ID defined in `sexual.yaml`

#### Scenario: Adding a rule without a matching test fails the correspondence check
- **WHEN** a new rule is added to `sexual.yaml` with no corresponding `test_rule_<id>` function added
  to `test_sexual_state.py`
- **THEN** the mechanical correspondence check fails, naming the rule ID missing a test
