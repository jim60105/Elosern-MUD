# sexual-act-registry Delta Specification

> Written against the post-`sexual-intercourse-acts` main specs (see tasks.md ordering note).
> The MODIFIED requirement below uses the header that `sexual-intercourse-acts`'s delta produces.

## MODIFIED Requirements

### Requirement: _act_family() populates every row's effects with the pleasure and sexual_counter prefixes for that row's own key, plus one sexual_event entry per declared event and one act_pair_event entry when the row declares pair_events
`world/skills/sexual_acts/_builder.py`'s `_act_family()` SHALL set every `SkillDef` it constructs to
`effects=[f"pleasure:{key}", f"sexual_counter:{key}", *(f"sexual_event_actor:{name}" if name in
_ACTOR_SCOPED_EVENTS else f"sexual_event:{name}" for name in row.sexual_events),
*(f"act_pair_event:{key}",) if row.pair_events else ()]`, where `key` is that row's own key,
`row.sexual_events` is that row's declared event tuple in order, a declared event name in the
`_ACTOR_SCOPED_EVENTS` vocabulary is emitted through the actor-scoped `sexual_event_actor:` prefix
and every other declared name through `sexual_event:`, and the trailing `act_pair_event:<key>`
entry is present exactly when the row declares a non-empty `pair_events` tuple.

#### Scenario: A family row's SkillDef carries both new prefixes keyed to its own act
- **WHEN** `_act_family()` is called with one row naming key `"test_act"` and `sexual_events=()`
- **THEN** `SKILL_REGISTRY["test_act"].effects` equals
  `["pleasure:test_act", "sexual_counter:test_act"]`

#### Scenario: A row declaring sexual_events gains one sexual_event entry per name, in order
- **WHEN** `_act_family()` is called with one row naming key `"test_act"` and
  `sexual_events=("frequent_stimulation", "watched_during_activity")`
- **THEN** `SKILL_REGISTRY["test_act"].effects` equals `["pleasure:test_act",
  "sexual_counter:test_act", "sexual_event:frequent_stimulation",
  "sexual_event_actor:watched_during_activity"]` — the actor-scoped name uses the actor-scoped
  prefix, the participant-scoped name does not

#### Scenario: A row declaring pair_events gains exactly one trailing act_pair_event entry naming its own key
- **WHEN** `_act_family()` is called with one row naming key `"test_act"`, `sexual_events=()`, and a
  non-empty `pair_events` tuple
- **THEN** `SKILL_REGISTRY["test_act"].effects` equals `["pleasure:test_act",
  "sexual_counter:test_act", "act_pair_event:test_act"]`

#### Scenario: The effect strings never name a different act's key
- **WHEN** `_act_family()` builds more than one row in a single call
- **THEN** each row's `effects` list names only that row's own key, never another row's

## ADDED Requirements

### Requirement: Acts classify each declared event by name into the actor-scoped or participant-scoped channel
`world/skills/sexual_acts/_builder.py` SHALL declare `_ACTOR_SCOPED_EVENTS`, a frozenset naming the
performer-scoped event vocabulary exactly: `self_exposure`, `public_exposure`,
`watched_during_activity`, `public_sexual_activity`. A structural test SHALL assert that every
member of `_ACTOR_SCOPED_EVENTS` is a value some rule in `world/rules/rulebook/sexual.yaml` carries
as `when["event"]`, that every event name an act declares resolves to exactly one of the two
channels (actor-scoped names in the set, participant-scoped names outside it), and that no act
declares an event name absent from both vocabularies.

#### Scenario: The vocabulary names only real rulebook events
- **WHEN** the structural test iterates `_ACTOR_SCOPED_EVENTS`
- **THEN** every member appears as a `when["event"]` value in `world/rules/rulebook/sexual.yaml`

#### Scenario: The channel classification is by event name, never per-row override
- **WHEN** any two acts both declare `"self_exposure"`
- **THEN** both acts' effects carry `sexual_event_actor:self_exposure` — a catalog row cannot
  choose the other channel for a name

#### Scenario: An act declaring an event in neither vocabulary fails the structural test
- **WHEN** a hypothetical act declares `sexual_events=("a_fake_event",)`
- **THEN** the structural test fails, naming the act's key and the unrecognized event
