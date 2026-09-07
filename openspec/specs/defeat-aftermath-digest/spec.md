# defeat-aftermath-digest Specification

## Purpose

Close out the defeat aftermath: every entity the violation sequence
selected digests its own body's recorded state into exactly one outcome
(`residue` / `humiliated` / `none`) through a first-match rulebook table
over a closed condition vocabulary, mounts its shipped-surface marker buff,
wakes on a digest-selected zh-tw line family while conscious bystanders get
observation lines only, and a pure Narrator overlay renders one prose
paragraph per aftermath entry with guaranteed template degradation.

## Requirements

### Requirement: Each violated entity digests its own body's recorded state
At the end of the defeat aftermath, each entity the violation sequence
selected SHALL receive exactly one digest outcome — `residue`,
`humiliated`, or `none` — selected by the first matching rulebook row in
`world/rules/rulebook/defeat_aftermath.yaml` evaluated against ONLY that
entity's own existing sexual-state fields (its `sensitivity` level, its
`shame` level, its end-of-sequence arousal ordinal) plus the sequence's
in-memory `ViolationOutcome` for that entity (climax count, zero-landed
flag) handed through the same settlement call — never a persisted digest
input, and no replay bookkeeping. The digest section's rulebook schema
SHALL reject any race/species/persona condition key at load; the digest
SHALL read no affinity value and no other entity's state.

#### Scenario: High sensitivity with a climax digests residue
- **WHEN** a violated entity with high `sensitivity` ends the sequence with sequence-recorded climax ≥ 1
- **THEN** its digest outcome is `residue`

#### Scenario: Low sensitivity with high shame digests humiliated
- **WHEN** a violated companion with low `sensitivity` and high `shame` ends the sequence with its outcome's zero-landed flag set
- **THEN** its digest outcome is `humiliated`

#### Scenario: The digest loader rejects species-conditioned rows
- **WHEN** a digest rulebook row carries a race/species/persona condition key
- **THEN** rulebook load fails with a validation error before the section is consulted

#### Scenario: A Monster's pinned shame can never reach the humiliated band
- **WHEN** any violated entity whose `shame` is pinned at 無 digests
- **THEN** the outcome is `residue` or `none`, because the shame band in the row can never match — established without the rulebook reading species

### Requirement: Digest outcomes mount shipped-surface buffs on violated entities and bystanders stay lighter
The `residue` and `humiliated` outcomes SHALL mount their buff rows from
`world/rules/rulebook/buffs.yaml` — marker buffs with world-second durations
whose declared modifiers stay inside the shipped `bounds` effect surface —
on the violated entity. An allied bystander who was conscious but never
selected SHALL receive no digest buff.

#### Scenario: A digested companion wakes with the matching buff
- **WHEN** a companion's digest outcome is `humiliated`
- **THEN** after settlement the companion carries the `aftermath_humiliated` buff and no affinity value changed anywhere

#### Scenario: An unselected bystander carries no digest buff
- **WHEN** a bound companion stood (never selected by the sequence) while the player was violated
- **THEN** the bystander carries no digest buff and only the wake-line tone reflects the event

### Requirement: Wake-up lines are digest-selected with persona as flavor only
Each wake-up SHALL select its zh-tw line family by the entity's own digest
outcome. Persona flavor text MAY feed only the Narrator overlay voice and
SHALL never be an input to a digest condition or a buff grant.
`DigestOutcome` (selected participants) and `WakeObservation` (conscious
unselected bystanders) SHALL be separate outputs: a bystander receives an
observation line, no digest outcome, and no buff.

#### Scenario: Bystander observation is not a digest
- **WHEN** a conscious bystander who was never selected wakes after the sequence
- **THEN** it receives one observation line, carries no digest buff, and no `DigestOutcome` row exists for it

#### Scenario: Offline wake lines differ by digest only
- **WHEN** two fixture defeats digest `humiliated` versus `residue` for the same companion with every LLM profile disabled
- **THEN** the deterministic wake lines come from the two different template families and the buff grants differ accordingly

### Requirement: The Narrator overlays aftermath entries and always degrades to templates
The Narrator overlay SHALL be a pure render function over the aftermath
EventLog entries appended after the fixed wake lines: exactly one prose
paragraph per entry, never rewriting or duplicating an entry already
rendered, and never gating state. The prompt library's `narrator.system`
guidance SHALL cover the aftermath kind vocabulary. Any narrator failure,
timeout, or disabled profile SHALL discard only the overlay — the
deterministic wake lines and template lines remain the complete render and
the settled state is unchanged.

#### Scenario: Success renders one paragraph per entry
- **WHEN** the narrator profile answers for a sequence of N aftermath entries
- **THEN** the overlay contains exactly N paragraphs in entry order and the settled state is untouched by the overlay

#### Scenario: Profile failure discards only the overlay
- **WHEN** the narrator profile raises or times out
- **THEN** the player still receives the full deterministic wake/template lines and no state differs from the offline settlement

#### Scenario: Disabled profile renders templates only
- **WHEN** every LLM profile is disabled
- **THEN** the render equals the pure offline template path byte-for-byte

#### Scenario: Offline defeat still completes and renders
- **WHEN** a full defeat aftermath settles with every LLM profile failing
- **THEN** the player and companions receive digest-selected wake lines, all declared state writes occurred, and no narrator exception surfaces to the player
