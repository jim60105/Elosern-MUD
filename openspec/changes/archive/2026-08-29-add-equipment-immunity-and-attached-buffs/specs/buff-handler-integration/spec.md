## ADDED Requirements

### Requirement: Action-workflow debuff grants are neutralized by worn equipment immunity

When the action-resolution workflow would grant a debuff-polarity buff to a
target whose worn equipment confers immunity to that buff key, the staged
effect SHALL be a non-mutating neutralization with a stable
`equipment_immune|<entity>|<buff_key>` event tag and Traditional-Chinese
renderer text visible to actor and target, and the buff storage SHALL be
untouched. The buff-grant chokepoint SHALL independently refuse the write for
immune targets as a defense-in-depth backstop. Immunity rejects only new
grants while worn: it SHALL NOT remove, pause, or alter already-applied
debuffs. Buff-polarity grants and entities without equipment SHALL be
unaffected.

#### Scenario: Poisoned strike lands but does not apply

- **WHEN** a skill would apply `poisoned` to an actor wearing 淨化吊墜
- **THEN** no buff instance exists afterwards, the event log records the
  stable neutralization for both sides, and the action's damage settled
  normally

#### Scenario: Existing poison survives equipping the pendant

- **WHEN** an already-poisoned actor equips 淨化吊墜 and rounds tick
- **THEN** the poison keeps ticking exactly as before and the pendant
  prevents only new debuff grants

#### Scenario: Buff-polarity grants bypass the gate

- **WHEN** an ally applies `focus` to the same actor
- **THEN** the buff applies normally with no neutralization event

#### Scenario: Repeated attempts never half-apply

- **WHEN** the immune target is hit by three separate poison casts in one
  round
- **THEN** buff storage is unchanged after all three and each attempt
  produced its own neutralization event
