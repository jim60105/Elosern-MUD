# sexual-act-registry Delta Specification

## RENAMED Requirements

- FROM: `### Requirement: _act_family() populates every row's effects with the pleasure and sexual_counter prefixes for that row's own key, plus one sexual_event entry per declared event`
- TO: `### Requirement: _act_family() populates every row's effects with the pleasure and sexual_counter prefixes for that row's own key, plus one sexual_event entry per declared event and one act_pair_event entry when the row declares pair_events`

## MODIFIED Requirements

### Requirement: SexualActDef carries exactly the metadata a sex act needs beyond SkillDef
`world/skills/sexual_acts/_builder.py` SHALL define `SexualActDef` as a frozen dataclass with exactly
these fields: `key`, `unlock` (a mapping of `SexualState` counter attribute names to integer
thresholds, all of which SHALL be met for the act to unlock), `base_pleasure` (a positive integer),
`actor_part` and `target_part` (each `None` or a member of `world.lore.sexual_vocab.BODY_PARTS`),
`actor_pleasure_ratio` (a float), `actor_counters` and `participant_counters` (each a tuple of
`SexualState` counter attribute names), `sexual_events` (a tuple of event-name strings in emission
order), `resistible` (a bool), and `pair_events` (a tuple of `(sex_pair, event_name)` entries, empty
for acts without a sex-conditional event; see the pair-events requirement). `SexualActDef` SHALL
declare no `line` field; an act's line is read from the paired `SkillDef.group`.

#### Scenario: A seed act declares an empty unlock mapping
- **WHEN** a `SexualActDef` is constructed with `unlock={}`
- **THEN** construction succeeds and the act is always available regardless of any counter's value

#### Scenario: SexualActDef declares no line field
- **WHEN** `SexualActDef`'s field set is inspected
- **THEN** it contains no field named `line`, and an act's line is obtained by reading
  `SKILL_REGISTRY[act.key].group` instead

#### Scenario: An act without a sex-conditional event declares an empty pair_events tuple
- **WHEN** a `SexualActDef` is constructed for an ordinary act that does not name `pair_events`
- **THEN** its `pair_events` is the empty tuple

### Requirement: _act_family() populates every row's effects with the pleasure and sexual_counter prefixes for that row's own key, plus one sexual_event entry per declared event and one act_pair_event entry when the row declares pair_events
`world/skills/sexual_acts/_builder.py`'s `_act_family()` SHALL set every `SkillDef` it constructs to
`effects=[f"pleasure:{key}", f"sexual_counter:{key}", *(f"sexual_event:{name}" for name in
row.sexual_events), *(f"act_pair_event:{key}",) if row.pair_events else ()]`, where `key` is that
row's own key, `row.sexual_events` is that row's declared event tuple in order, and the trailing
`act_pair_event:<key>` entry is present exactly when the row declares a non-empty `pair_events`
tuple.

#### Scenario: A family row's SkillDef carries both new prefixes keyed to its own act
- **WHEN** `_act_family()` is called with one row naming key `"test_act"` and `sexual_events=()`
- **THEN** `SKILL_REGISTRY["test_act"].effects` equals
  `["pleasure:test_act", "sexual_counter:test_act"]`

#### Scenario: A row declaring sexual_events gains one sexual_event entry per name, in order
- **WHEN** `_act_family()` is called with one row naming key `"test_act"` and
  `sexual_events=("frequent_stimulation", "watched_during_activity")`
- **THEN** `SKILL_REGISTRY["test_act"].effects` equals `["pleasure:test_act",
  "sexual_counter:test_act", "sexual_event:frequent_stimulation",
  "sexual_event:watched_during_activity"]`

#### Scenario: A row declaring pair_events gains exactly one trailing act_pair_event entry naming its own key
- **WHEN** `_act_family()` is called with one row naming key `"test_act"`, `sexual_events=()`, and a
  non-empty `pair_events` tuple
- **THEN** `SKILL_REGISTRY["test_act"].effects` equals `["pleasure:test_act",
  "sexual_counter:test_act", "act_pair_event:test_act"]`

#### Scenario: The effect strings never name a different act's key
- **WHEN** `_act_family()` builds more than one row in a single call
- **THEN** each row's `effects` list names only that row's own key, never another row's

### Requirement: Every counter and event an act names actually exists, checked across the whole assembled registry
A structural test SHALL assert that every string appearing in any act's `unlock` keys,
`actor_counters`, or `participant_counters` is one of `SexualState`'s eleven documented lifetime
counter attribute names, and that every string in any act's `sexual_events` or in any act's
`pair_events` event positions is a value some rule in `world/rules/rulebook/sexual.yaml` carries as
`when["event"]`.

#### Scenario: An unrecognized counter name fails the structural test
- **WHEN** a hypothetical act declares `unlock={"自慰次數": 10}` (the Chinese label, not the
  attribute name `masturbation_count`)
- **THEN** the structural test fails, naming the act's key and the unrecognized string

#### Scenario: An unrecognized event name fails the structural test
- **WHEN** a hypothetical act declares `sexual_events=("a_fake_event",)`
- **THEN** the structural test fails, naming the act's key and the unrecognized event

#### Scenario: An unrecognized pair-event name fails the structural test
- **WHEN** a hypothetical act declares `pair_events=((("female", "male"), "a_fake_event"),)`
- **THEN** the structural test fails, naming the act's key and the unrecognized event

## ADDED Requirements

### Requirement: An act declaring pair_events SHALL be a SINGLE-target act whose entries are sorted two-sex tuples naming real rulebook events
`_act_family()` SHALL raise `ValueError`, naming the offending key, for any row that declares a
non-empty `pair_events` tuple unless all of the following hold: the row's `target_spec` is
`TargetSpec.SINGLE`; every entry's sex pair is a tuple of exactly two members of
`world.lore.sex.SEX_VALUES`, each entry sorted ascending with no pair repeated; and no entry's event
name is one of the forbidden `sexual_events` names (`stimulus_applied`, `sustained_stimulus_applied`,
`extreme_stimulus_applied`, `climax_ends`, `climax_extended`).

#### Scenario: A pair-events act with an AREA target spec is rejected
- **WHEN** `_act_family()` is called with a row declaring `pair_events` and
  `target_spec=TargetSpec.AREA`
- **THEN** it raises `ValueError` naming that row's key

#### Scenario: A pair-events entry with an unsorted or unknown sex pair is rejected
- **WHEN** `_act_family()` is called with a row whose `pair_events` contains `(("male", "female"),
  "first_vaginal_penetration")` (unsorted) or a pair naming a value outside `SEX_VALUES`
- **THEN** it raises `ValueError` naming that row's key

#### Scenario: A pair-events entry naming a forbidden event is rejected
- **WHEN** `_act_family()` is called with a row whose `pair_events` names `"climax_ends"`
- **THEN** it raises `ValueError` naming that row's key and the forbidden event
