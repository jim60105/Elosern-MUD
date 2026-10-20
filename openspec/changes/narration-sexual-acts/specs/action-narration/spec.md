# Spec Delta

## ADDED Requirements

### Requirement: Every sexual act has its own action narration

Each ACTIVE sexual act SHALL declare its own authored attempt line, and SHALL render that line
as the opening of its resolved cast instead of the line-of-act fallback. The attempt line SHALL
describe what the caster does without asserting contact, so the verdict clause that follows it
reads correctly whether the target complied or refused. The catalog's pending-family set SHALL
be empty.

#### Scenario: Two acts of one line open differently

- **WHEN** two ACTIVE acts of the same act line resolve against the same target under the same
  narration scope
- **THEN** each cast's opening line comes from that act's own row and the two lines differ

#### Scenario: A newly added act fails at import without a row

- **WHEN** a sexual act exists in the shipped act registry with no authored narration row
- **THEN** catalog loading raises a named narration-catalog error naming that act

### Requirement: The verdict completes the act's own line

A sexual cast's opening line SHALL be composed of the act's attempt line and exactly one verdict
clause selected from the resist entry's payload, differentiating resisted, auto-complied and
complied outcomes. The resist entry SHALL render for every target regardless of verdict, and a
resisted target SHALL receive no pleasure or counter entry.

#### Scenario: The same act reads as a refusal or as consent

- **WHEN** one act resolves once with `resisted` true and once with it false, all other inputs
  equal
- **THEN** both lines share the same act attempt clause and differ only in the verdict clause,
  and only the complied cast emits pleasure and counter entries for that target

#### Scenario: An auto-complied verdict states its own cause

- **WHEN** the verdict payload reports `auto_comply` true and `resisted` false
- **THEN** the rendered clause states that the target yielded rather than choosing, and it is
  distinguishable from the ordinary complied clause

### Requirement: Sexual transition and counter prose covers exactly what the catalog can emit

The transition clause pool's key set SHALL equal the union of every act's sexual events and every
pair-event name, and the counter clause pool's key set SHALL equal the union of every act's
performer and participant counters, each with a performer and a participant clause. Both SHALL be
validated at import against the catalog-derived sets.

#### Scenario: A new event name without a clause fails the import

- **WHEN** an act declares a sexual event or pair-event name absent from the transition pool
- **THEN** catalog loading raises a named narration-catalog error naming the event

#### Scenario: A new counter without clauses fails the import

- **WHEN** an act declares a lifetime counter absent from the counter pool, or a counter present
  in the pool lacks one of the two role clauses
- **THEN** catalog loading raises a named narration-catalog error naming the counter

### Requirement: Participant role selects the sexual counter and pleasure clause

A `pleasure_gain` or `sexual_counter` entry whose participant is the cast's actor SHALL render
the performer clause; an entry whose participant is another target SHALL render the participant
clause. The counter clause SHALL follow the act's own counter declaration, so a counter declared
only for the performer never renders as a shared bodily record.

#### Scenario: The caster's own pleasure line differs from the target's

- **WHEN** one act grants pleasure to both the caster and its target
- **THEN** the caster's entry renders the performer clause and the target's entry renders the
  participant clause

#### Scenario: A performer-only counter stays performer-only

- **WHEN** an act declares a counter in its performer counters and resolves against one target
- **THEN** that counter's rendered line uses the performer wording and no participant wording

### Requirement: The pending-family set is empty and stays pinned

After this change no ACTIVE skill family may be exempt from per-skill narration coverage. The
declared pending-family set SHALL be empty, and a test SHALL pin it empty so no family can
silently re-open an exemption.

#### Scenario: Adding a skill anywhere fails without a row

- **WHEN** an ACTIVE skill of any category exists in the shipped registry with no authored
  narration row
- **THEN** catalog loading raises a named narration-catalog error naming that skill

#### Scenario: Re-opening an exemption fails the pin

- **WHEN** the pending-family set is changed to contain any family
- **THEN** the pinning test fails, naming the family that was re-opened
