# sexual-act-registry Specification

## Purpose

Define the `SexualActDef` sidecar metadata that lets an ordinary `SkillDef` be a counter-gated sex
act, the six-module catalogue package with pre-declared empty stubs, and the structural invariants
that keep the paired registries honest. The catalogue content itself (the 62 acts and the divine
line) ships in later proposals; this capability only makes that content possible.

## Requirements

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

### Requirement: Every SexualActDef is paired with an ordinary SkillDef under the same key, categorised SEXUAL_ACT
`_act_family()` SHALL construct, for each row it is given, one `SkillDef` (with `category=
SkillCategory.SEXUAL_ACT`, `group` set to the family's line, `kind=SkillKind.ACTIVE`, `cost={}`, and
`usable_out_of_combat=True`) and one `SexualActDef` sharing that `SkillDef`'s `key`, and SHALL
register both under the same key in `SKILL_REGISTRY` and `SEXUAL_ACT_REGISTRY` respectively.

#### Scenario: A family row produces a matching SkillDef and SexualActDef
- **WHEN** `_act_family()` is called with one row naming key `"test_act"`
- **THEN** `SKILL_REGISTRY["test_act"]` exists with `category is SkillCategory.SEXUAL_ACT` and
  `SEXUAL_ACT_REGISTRY["test_act"]` exists, and both share the key `"test_act"`

#### Scenario: A sex act costs no resource
- **WHEN** any `SkillDef` built by `_act_family()` is inspected
- **THEN** its `cost` is an empty mapping and `usable_out_of_combat` is `True`

### Requirement: The six line modules ship pre-declared and pre-imported
`world/skills/sexual_acts/` SHALL contain `solo.py`, `shame.py`, `partner.py`, `combat.py`,
`interspecies.py`, and `divine.py`, each exporting one module-level tuple constant
(`SOLO_ACTS`, `SHAME_ACTS`, `PARTNER_ACTS`, `COMBAT_ACTS`, `INTERSPECIES_ACTS`, `DIVINE_ACTS`
respectively). `solo.py`, `shame.py`, `partner.py`, and `combat.py` carry the seed acts registered
by the `sexual-act-seeds` change. `interspecies.py` (filled by `sexual-catalog-interspecies`) and
`divine.py` (filled by `sexual-catalog-divine-core`) are no longer required to remain empty — every
one of the six modules SHALL export a non-empty tuple once its owning catalog proposal has landed.
`world/skills/sexual_acts/__init__.py` SHALL import all six and merge their contents into
`SEXUAL_ACT_REGISTRY` and `SKILL_REGISTRY`.

#### Scenario: The six content modules are importable and non-empty
- **WHEN** each of `solo.py`, `shame.py`, `partner.py`, `combat.py`, `interspecies.py`, and `divine.py`
  is imported after every catalog proposal that fills it has landed
- **THEN** its declared tuple constant exists and is a non-empty tuple of act rows

#### Scenario: A later proposal fills exactly one module with no other line module touched
- **WHEN** a hypothetical catalog proposal changes `solo.py`'s `SOLO_ACTS` tuple to a different
  non-empty tuple of rows and changes no other line module
- **THEN** `SEXUAL_ACT_REGISTRY` and `SKILL_REGISTRY` both reflect the new acts after re-import, with
  no edit required to `__init__.py`, `_builder.py`, or any other line module

### Requirement: Every act applying pleasure to another participant applies non-zero pleasure to its own actor, unless it requires divine arts
`_act_family()` SHALL raise `ValueError`, naming the offending key, for any row whose
`actor_pleasure_ratio` is not strictly greater than zero, unless the family's `requires_divine_arts`
keyword argument is `True`.

#### Scenario: A zero actor-pleasure-ratio row is rejected for a non-divine family
- **WHEN** `_act_family()` is called with `requires_divine_arts=False` and a row declaring
  `actor_pleasure_ratio=0.0`
- **THEN** it raises `ValueError` naming that row's key

#### Scenario: A zero actor-pleasure-ratio row is accepted for a divine family
- **WHEN** `_act_family()` is called with `requires_divine_arts=True` and a row declaring
  `actor_pleasure_ratio=0.0`
- **THEN** construction succeeds

### Requirement: No act declares the generic body-part channel; only 異種 and 神之秘法 acts may omit a target part
`_act_family()` SHALL raise `ValueError` for any row whose `actor_part` or `target_part` equals
`world.lore.sexual_vocab.GENERIC_BODY_PART`. `_act_family()` SHALL raise `ValueError` for any row
declaring a non-`None` `target_part` when the family's line is `"異種"` or `"神之秘法"`. Every
non-`None` part on any row SHALL be a member of `world.lore.sexual_vocab.BODY_PARTS`.

#### Scenario: Declaring the generic body part is rejected
- **WHEN** `_act_family()` is called with a row whose `actor_part` equals `GENERIC_BODY_PART`
- **THEN** it raises `ValueError` naming that row's key

#### Scenario: An 異種 act declaring a target part is rejected
- **WHEN** `_act_family()` is called with line `"異種"` and a row whose `target_part` is not `None`
- **THEN** it raises `ValueError` naming that row's key

#### Scenario: A part outside BODY_PARTS is rejected
- **WHEN** `_act_family()` is called with a row whose `actor_part` is a string not present in
  `BODY_PARTS`
- **THEN** it raises `ValueError` naming that row's key and the invalid part

### Requirement: Every counter and event an act names actually exists, checked across the whole assembled registry
A structural test SHALL assert that every string appearing in any act's `unlock` keys,
`actor_counters`, or `participant_counters` is one of `SexualState`'s eleven documented lifetime
counter attribute names, and that every string in any act's `sexual_events` or in any act's
`pair_events` event positions is a value some rule in
`world/rules/rulebook/sexual.yaml` carries as `when["event"]`.

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

### Requirement: SEXUAL_ACT_REGISTRY's keys and SKILL_REGISTRY's SEXUAL_ACT-categorised keys agree exactly, modulo the three named mastery/mystery exclusions
A structural test SHALL assert that `set(SEXUAL_ACT_REGISTRY)` equals the set of `SKILL_REGISTRY` keys
whose `category` is `SkillCategory.SEXUAL_ACT`, with `{"divine_sexual_arts", "divine_sexual_mastery",
"reincarnation_boon_yuna"}` excluded from that comparison on both sides.

#### Scenario: The two registries agree with zero acts registered
- **WHEN** the structural test runs against this change alone (no catalog content yet)
- **THEN** it passes, because both sides of the comparison are empty after the three named exclusions

#### Scenario: A SkillDef categorised SEXUAL_ACT with no paired SexualActDef fails the structural test
- **WHEN** a hypothetical skill is added to `SKILL_REGISTRY` directly (not through `_act_family()`)
  with `category=SkillCategory.SEXUAL_ACT` and a key not in `SEXUAL_ACT_REGISTRY` and not one of the
  three named exclusions
- **THEN** the structural test fails, naming the unmatched key

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
