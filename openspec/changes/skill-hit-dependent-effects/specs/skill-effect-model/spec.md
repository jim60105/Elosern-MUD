# Spec Delta

## ADDED Requirements

### Requirement: Effect hit dependencies reference earlier damage occurrences
Per-effect policy SHALL optionally require a hit from one explicitly named earlier damage occurrence in the same ordered skill. Registry validation SHALL reject absent, forward, self, non-damage or malformed references. Unconfigured effects SHALL retain their existing behavior.

#### Scenario: Authoring errors fail before play
- **WHEN** synthetic definitions declare out-of-bounds, forward/self or non-damage dependencies or a malformed reference
- **THEN** construction or registry load rejects them

#### Scenario: Repeated damage occurrences remain distinct
- **WHEN** a skill has two identical damage IDs and a rider refers to the first occurrence
- **THEN** only the referenced occurrence supplies qualifying hits

### Requirement: Damage provides trusted invocation-local typed hit outcomes
The existing damage hit rolls SHALL supply typed outcomes keyed by occurrence and target identity within one final invocation. No description or event prose parsing, caller-forged outcome or cross-round flag SHALL determine dependency success. Preflight SHALL validate structure without rolls or manufactured hit outcomes.

#### Scenario: No second hit roll
- **WHEN** one single-strike damage occurrence and dependent rider resolve
- **THEN** exactly the source hit roll occurs; a hit delivers the rider and a miss skips it

#### Scenario: Preflight cannot manufacture outcomes
- **WHEN** a request carries forged outcome-like context and is preflighted and resolved
- **THEN** preflight consumes no dice or state; final qualification follows resolver-owned source outcomes only

#### Scenario: Outcome scope is local
- **WHEN** a previous invocation hit and a new invocation misses
- **THEN** the new rider is skipped regardless of previous outcomes

#### Scenario: Identity is not display text
- **WHEN** two targets share a display name and only one is hit
- **THEN** only the hit entity qualifies

### Requirement: Dependent recipients intersect ordinary audiences with source hits
A dependent occurrence SHALL receive only the intersection of its validated ordinary audience and the referenced source occurrence's hit targets. A source hit qualifies independently of actual HP loss. For multiple source strikes, the dependent occurrence SHALL execute once per target when any strike hits.

#### Scenario: Miss and diversion differ
- **WHEN** one target is missed and another hit is fully diverted or absorbed
- **THEN** the missed target receives no rider and the hit target qualifies even with zero HP loss

#### Scenario: Multi-strike any-hit is once per target
- **WHEN** each hit/miss combination of a two- or three-strike source resolves
- **THEN** at least one hit produces one rider for that target and all misses produce none; there is no per-strike rider multiplication

#### Scenario: Audience never expands
- **WHEN** the source hits an enemy while the rider audience includes an ally or self absent from the source hit set
- **THEN** the absent entity receives no dependent effect; relation and gauge-state audience gates remain in force

#### Scenario: Target subset is respected
- **WHEN** an area source hits a strict subset and the rider has a narrower valid audience
- **THEN** delivery follows the intersection and cannot re-add targets rejected by targeting

#### Scenario: Other supported target effects reuse the contract
- **WHEN** a synthetic status/buff target effect depends on source damage
- **THEN** it uses the same routing behavior without transfer-only or species branches

### Requirement: Dependent effects retain normal settlement and rollback
Damage, dependent effects, costs and practice SHALL remain in one normal action transaction with existing effects-before-cost settlement. Failed commits SHALL restore all touched participants and state and release rolled-back practice claims. A skipped rider SHALL NOT cancel payment for a resolved miss.

#### Scenario: Late failure restores all surfaces
- **WHEN** a synthetic action stages damage, transfer/recovery, costs and practice and a later pending effect fails
- **THEN** actor and targets gauges and touched buffs/attributes return to pre-action values; a same-tick retry may claim practice

#### Scenario: Miss still resolves and pays
- **WHEN** an affordable action misses its source strike and its only rider is hit dependent
- **THEN** the rider is skipped but costs and normal successful-action practice semantics remain

#### Scenario: Unconfigured skills retain settlement
- **WHEN** ordinary existing effects without dependency metadata resolve
- **THEN** their recipient selection, rolls, payment order and rollback are unchanged

