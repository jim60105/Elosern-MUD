## ADDED Requirements

### Requirement: A qualified passive self-recovers once on canonical climax entry

A qualified passive SHALL restore its holder's HP when that holder canonically enters the in-progress climax phase. The restored amount SHALL be an authored fraction of the holder's maximum HP, floored to a whole number, and SHALL cost no resource of any kind — no MP, no SP, no action, no cast.

The restoration SHALL occur exactly once per canonical entry into that phase: it SHALL be driven by the phase *transition*, never by the phase state, so a climax extension or any other event occurring while the holder is already in that phase SHALL restore nothing further. A holder who does not qualify for the passive SHALL receive nothing.

The trigger SHALL be the phase entry alone. The restoration SHALL NOT depend on how the holder's arousal was accrued: a climax reached entirely outside combat, through stimulus carrying no HP loss, SHALL pay out exactly as one reached through damage. The passive is therefore both the damage loop's third leg and a deliberate out-of-combat recovery option, priced by the climax's own existing costs rather than by a provenance check.

The restoration SHALL be clamped to the holder's missing HP, SHALL never raise HP above maximum, and SHALL never apply to a holder at or below zero HP — it restores, it does not revive. A holder whose maximum HP is unreadable or not positive SHALL receive nothing rather than a guessed amount.

The restoration SHALL settle inside the transaction that performed the phase transition, so a later failure in that settlement restores the HP, the phase and the pleasure gauge together.

#### Scenario: Entering climax restores the authored fraction

- **WHEN** a synthetic qualified holder missing more than the authored fraction of its maximum HP canonically enters the in-progress climax phase
- **THEN** its HP increases by the floored authored fraction of maximum HP, and no MP, SP or action is consumed

#### Scenario: A second stimulus during climax restores nothing further

- **WHEN** a synthetic qualified holder that already entered the in-progress climax phase receives a further qualifying stimulus without leaving that phase
- **THEN** its HP is unchanged by the passive

#### Scenario: A climax reached without any damage pays out identically

- **WHEN** a synthetic qualified holder missing more than the authored fraction of its maximum HP reaches the in-progress climax phase entirely through stimulus that inflicted no HP loss
- **THEN** its HP increases by the same floored authored fraction as a damage-driven climax would have restored

#### Scenario: A holder without the passive receives nothing

- **WHEN** a synthetic holder that does not qualify for the passive canonically enters the in-progress climax phase
- **THEN** its HP is unchanged

#### Scenario: The restoration cannot overheal

- **WHEN** a synthetic qualified holder missing less than the authored fraction of its maximum HP enters the in-progress climax phase
- **THEN** its HP rises to exactly its maximum and no surplus is carried anywhere

#### Scenario: The restoration never revives

- **WHEN** a synthetic qualified holder at or below zero HP would enter the in-progress climax phase
- **THEN** no HP is restored

#### Scenario: An unreadable maximum restores nothing

- **WHEN** a synthetic qualified holder whose maximum HP is unreadable or not positive enters the in-progress climax phase
- **THEN** no HP is restored and no write occurs

#### Scenario: A failed settlement restores the whole cascade

- **WHEN** the transaction that performed the phase transition fails after the passive restored HP
- **THEN** HP, climax phase and the pleasure gauge are all restored to their pre-transaction values

#### Scenario: A malformed self-recovery fraction fails at load

- **WHEN** a rule authors the self-recovery action with a fraction that is not a finite number in the open-closed range from zero to one
- **THEN** rule loading raises naming that rule id
