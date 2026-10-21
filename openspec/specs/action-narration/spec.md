# action-narration Specification

## Purpose
Provides deterministic, authored Traditional-Chinese narration for resolved skill actions
and combat rounds: which sentence each event entry renders, which qualitative severity
word replaces a number, and why identical inputs always produce identical prose with no
model, network, or clock dependency.

## Requirements

### Requirement: Authored narration is a catalog validated against the shipped registries

A frozen narration catalog SHALL be keyed by the shipped skill and sexual-act keys and SHALL
be validated at import, before any action resolves. Validation SHALL reject a catalog row whose
key is not a shipped ACTIVE skill or sexual act, a duplicate key, a missing row for an ACTIVE
skill outside the declared pending-family set, and any row that violates the line bounds. The
pending-family set SHALL be a frozen authoring declaration that only shrinks.

#### Scenario: A missing row for a covered skill fails the import

- **WHEN** an ACTIVE skill whose category is outside the declared pending-family set has no
  catalog row and the catalog is loaded
- **THEN** loading raises a named narration-catalog error naming that skill key, and the
  server does not start with a silently generic line for it

#### Scenario: An unknown or duplicate key fails the import

- **WHEN** the catalog declares a row for a key that is not an ACTIVE shipped skill or a
  sexual act, or declares the same key twice
- **THEN** loading raises a named narration-catalog error naming the offending key

#### Scenario: A synthetic catalog scope never trips validation

- **WHEN** a behavior test substitutes a synthetic skill catalog for the live registry
- **THEN** catalog validation still reads the shipped snapshot and neither fails nor changes

### Requirement: Variant selection is deterministic and consumes no gameplay randomness

For one entry, the rendered line SHALL be chosen from that entry's authored variants by a
CRC digest over a canonical seed built from the narration scope, skill key, entry kind, the
entry's ordinal in the log, the entry's target key and the qualitative band. Selection SHALL
NOT draw from the gameplay RNG, read the wall clock, or depend on process state.

#### Scenario: The same inputs render the same line twice

- **WHEN** the same resolved entry is rendered twice, in two different processes
- **THEN** both renders return the same string

#### Scenario: Narration never changes a roll, a number, or committed state

- **WHEN** an action resolves while the gameplay dice entry point is patched to raise on any
  call made by narration
- **THEN** the action still resolves successfully, the committed state and every entry's
  numeric `data` value are identical to the pre-narration result, and the draw count of the
  action's own hit and damage rolls is unchanged

#### Scenario: A different narration scope varies the line

- **WHEN** the same skill, kind and target resolve under two different narration scopes with
  a row that carries more than one variant
- **THEN** the chosen variant may differ, and each choice is stable for its own scope

### Requirement: Narration prose contains no numeric magnitude

Every authored narration line SHALL contain no ASCII digit and no payload field reference;
every magnitude SHALL be expressed as a qualitative band or verdict word. Exact numbers
SHALL remain in the entry's structured data unchanged.

#### Scenario: Damage, healing, cost and pleasure lines carry no number

- **WHEN** an action emits `damage`, `heal`, `resource_spend` and `pleasure_gain` entries with
  numeric amounts
- **THEN** every rendered line for those entries contains no digit, while each entry's `data`
  amount is still the exact integer the resolver recorded

#### Scenario: A roll line hides the raw roll

- **WHEN** an attack emits a `roll` entry whose `data["raw_roll"]` is 92
- **THEN** the rendered line neither contains "92" nor any other digit, and still reads as a
  hit or a miss consistent with `data["hit"]`

### Requirement: Authored lines carry a declared participant-slot budget

Each authored line SHALL carry at most two participant slots, and for every authored line and
every composed action-plus-outcome pair its literal code-point count plus the declared name
bound per slot SHALL stay inside the beat-text bound. Each entry kind SHALL ship a compact
fallback with no participant slot and a length well inside that bound.

#### Scenario: An over-length row fails authoring validation

- **WHEN** a catalog row's literal text plus the declared name bound per slot exceeds the
  beat-text bound
- **THEN** loading raises a named narration-catalog error naming that row

#### Scenario: A row beyond the slot budget fails authoring validation

- **WHEN** a catalog row declares more participant slots than the budget, or a composed pair
  whose combined slots exceed it
- **THEN** loading raises a named narration-catalog error naming that row

### Requirement: The built line degrades to its compact fallback when names do not fit

When an entry is built, the selected line SHALL be checked against its actual rendered length,
and the selector SHALL take the first named variant that fits, falling back to the compact
fallback when none does. The compact fallback SHALL therefore bound every rendered line no
matter how long a participant key is.

#### Scenario: An over-long participant key still yields a beat

- **WHEN** a settled round contains a damage entry whose participant key is 300 code points
  long
- **THEN** the beat's text is at most the beat-text bound, the beats panel is available, and
  the projected HP still matches the recorded HP

#### Scenario: The fallback still hides the number

- **WHEN** the compact fallback renders for a `damage` entry whose amount is recorded
- **THEN** the fallback line contains no digit and the entry's data keeps the exact amount

### Requirement: A resolved action opens with its own skill's action narration

The first entry of a resolved action's log SHALL render an action clause authored for that
specific skill, composed with the outcome clause selected for that entry's kind and band.
Entries after the first SHALL render from their kind pool without repeating the action clause.
A successful action that produces no entries SHALL still emit exactly one action-narration
entry carrying that skill's action clause.

#### Scenario: Two skills open differently

- **WHEN** two different ACTIVE skills resolve against the same target
- **THEN** each log's first line names that skill's own action, and the two first lines differ

#### Scenario: A skill with no effects still narrates

- **WHEN** an ACTIVE skill whose effects stage nothing resolves successfully
- **THEN** the log carries exactly one action-narration entry and the player sees that skill's
  action line instead of nothing

### Requirement: Mechanical entries narrate qualitatively instead of listing state changes

Each mechanical entry kind SHALL render from a multi-variant authored pool, with a
skill-or-act override taking precedence. Resource spending, trait changes, skill practice,
pleasure gain, lifetime counters and sexual transitions SHALL each read as a narrated
consequence rather than a state-change announcement.

#### Scenario: Two different mechanical kinds never read alike

- **WHEN** one action emits a `resource_spend` entry and another emits a `skill_practice` entry
- **THEN** their rendered lines differ and neither announces a generic state change

#### Scenario: Repeated casts do not repeat the same mechanical line

- **WHEN** two casts of the same skill resolve under different narration scopes
- **THEN** at least one of the repeated mechanical kinds renders a different authored variant

### Requirement: Sexual verdicts and participant roles drive the sexual narration

A `sexual_resist` entry SHALL render a verdict clause selected from its own payload: resisted,
auto-complied, or complied. A participant's own pleasure or counter line SHALL use the
actor-voice clause when the entry's target is the action's actor, and the counter clause SHALL
reflect whether the act records that counter for the performer or for every participant.

#### Scenario: A resisted act reads as a refusal

- **WHEN** a resistible sexual act resolves with `resisted` true
- **THEN** the rendered line states that the target declined, and no pleasure or counter entry
  follows for that target

#### Scenario: The caster's own line differs from the target's

- **WHEN** a sexual act grants pleasure to both the caster and its target
- **THEN** the two `pleasure_gain` entries render different clauses, one in the caster's own
  voice and one describing the target's response

### Requirement: Structural combat prose is authored once and stays stable

The round marker, the terminal outcome announcements, the engagement opening and the
overwhelm resolution summary SHALL be authored prose owned by the narration catalog.
The round marker and terminal announcements SHALL remain a single stable line each; the
engagement opening SHALL name the engaged foe; the overwhelm summary SHALL contain no numeric
count while its structured data keeps the round, hit and total-damage values.

#### Scenario: The overwhelm summary hides its counts and keeps its data

- **WHEN** a lopsided engagement resolves through overwhelm compression
- **THEN** the summary line contains no digit, and the entry's `data` still carries the round
  count, hit count and total damage

#### Scenario: The engagement opening names the foe

- **WHEN** a player engages a monster from the exploration surface
- **THEN** the opening line names the engaged monster instead of saying "the target"

### Requirement: Narration resolution degrades instead of rejecting an action

Every runtime narration lookup SHALL fall back through the documented chain and SHALL never
raise out of the action pipeline. A narration fault SHALL NOT turn a legal action into a
rejected action.

#### Scenario: An unknown skill key still resolves

- **WHEN** an action resolves for a skill key with no catalog row and no family tier
- **THEN** the action still succeeds and renders the generic kind pool's line for each entry

### Requirement: Every non-elemental ACTIVE skill has its own action narration

Each ACTIVE skill in the martial-arts, holy-rite, divine-mystery and enhancement categories
SHALL declare its own authored action narration, and SHALL render that line as the opening of
its resolved action instead of the category-tier line. The catalog's pending-family set SHALL
no longer contain those four categories.

#### Scenario: Two skills of one family open differently

- **WHEN** two ACTIVE martial-arts skills resolve against the same target under the same
  narration scope
- **THEN** each log's opening line comes from that skill's own row and the two lines differ

#### Scenario: A newly added skill in these families fails at import without a row

- **WHEN** an ACTIVE martial-arts, holy-rite, divine-mystery or enhancement skill exists in the
  shipped registry with no authored narration row
- **THEN** catalog loading raises a named narration-catalog error naming that skill

#### Scenario: The authored rows still obey the shared bounds

- **WHEN** a family row exceeds the literal-length budget, the slot budget or the no-digit rule
- **THEN** catalog loading raises the same named error the bound contract defines, with no
  family-specific exception
