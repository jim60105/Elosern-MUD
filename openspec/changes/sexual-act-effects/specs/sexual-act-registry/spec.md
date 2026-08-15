## ADDED Requirements

### Requirement: _act_family() populates every row's effects with the pleasure and sexual_counter prefixes for that row's own key, plus one sexual_event entry per declared event
`world/skills/sexual_acts/_builder.py`'s `_act_family()` SHALL set every `SkillDef` it constructs to
`effects=[f"pleasure:{key}", f"sexual_counter:{key}", *(f"sexual_event:{name}" for name in
row.sexual_events)]`, where `key` is that row's own key and `row.sexual_events` is that row's declared
event tuple in order, replacing the empty `effects=[]` this function produced before
`sexual-act-effects` defined those two new prefixes and wired up reuse of the existing `sexual_event:`
prefix.

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

#### Scenario: The effect strings never name a different act's key
- **WHEN** `_act_family()` builds more than one row in a single call
- **THEN** each row's `effects` list names only that row's own key, never another row's

### Requirement: an act's sexual_events never names a pleasure-, wetness-, or climax-settlement-owned event
`SexualActDef.sexual_events` SHALL NOT contain any of `"stimulus_applied"`,
`"sustained_stimulus_applied"`, `"extreme_stimulus_applied"`, `"climax_ends"`, or
`"climax_extended"`. A structural test SHALL enforce this across the whole assembled registry.

#### Scenario: An act declaring a forbidden event fails the structural test
- **WHEN** a hypothetical act declares `sexual_events=("stimulus_applied",)`
- **THEN** the structural test fails, naming the offending act's key and the forbidden event

#### Scenario: An act declaring direct_stimulus_applied passes
- **WHEN** an act declares `sexual_events=("direct_stimulus_applied",)`
- **THEN** the structural test passes — this event is additive wetness, not forbidden, per
  `sexual-act-effects`'s own D-8

### Requirement: solo acts declare no participant_counters, structurally enforced
Every `SexualActDef` whose paired `SkillDef.target_spec` is `TargetSpec.SELF` SHALL declare
`participant_counters=()`. A structural test SHALL enforce this across the whole assembled registry.

#### Scenario: A SELF-target act with a non-empty participant_counters fails the structural test
- **WHEN** a hypothetical `SexualActDef` paired with a `TargetSpec.SELF` `SkillDef` declares
  `participant_counters=("duo_act_count",)`
- **THEN** the structural test fails, naming the offending act's key

#### Scenario: A SELF-target act with an empty participant_counters passes
- **WHEN** a `SexualActDef` paired with a `TargetSpec.SELF` `SkillDef` declares
  `participant_counters=()`
- **THEN** the structural test passes for that act

### Requirement: every act outside the 異種 and 神之秘法 lines targeting another entity declares a non-null target_part
A structural test SHALL assert that every act whose line (`SkillDef.group`) is not `"異種"` or
`"神之秘法"`, and whose `target_spec` is not `SELF` or `NONE`, declares a non-`None` `target_part`.

#### Scenario: A 關係線 act with no target_part fails the structural test
- **WHEN** a hypothetical act on the `"關係"` line with `target_spec=TargetSpec.SINGLE` declares
  `target_part=None`
- **THEN** the structural test fails, naming the offending act's key

#### Scenario: An 異種線 act with no target_part passes
- **WHEN** an act on the `"異種"` line with `target_spec=TargetSpec.SINGLE` declares
  `target_part=None`
- **THEN** the structural test passes, per `sexual-act-registry`'s own existing invariant requiring
  exactly this for that line
