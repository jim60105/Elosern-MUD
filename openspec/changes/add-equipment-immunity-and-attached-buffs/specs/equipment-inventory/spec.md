## ADDED Requirements

### Requirement: Attached buffs travel with the equipment toggle

A successful `toggle_equipment()` SHALL recompute attached buffs from the
worn-set diff inside the same transaction as the equipment write: instances
for `worn_before − worn_after` items removed first, then instances for
`worn_after − worn_before` items applied, each keyed by definition and item
key with unique-per-source persistent stacking. The buff storage SHALL join
the toggle's snapshot/restore set through attribute-handler snapshot and
assignment-restore (live buff reads after restore SHALL match pre-call
state). Repeated toggling SHALL never accumulate duplicate instances, only
the toggle path SHALL create attached instances, and attached instances
SHALL NOT carry gauge-ceiling modifiers (gauge headroom is owned by the
equipment-cap recompute alone).

#### Scenario: Beads heal while worn

- **WHEN** an actor equips 藥師珠串 and rounds pass under the existing tick
  engine
- **THEN** exactly one attached regen instance ticks and HP rises at the
  rulebook rate

#### Scenario: Singleton-slot replacement swaps instances

- **WHEN** an actor wearing a regen-bead accessory equips a second
  attached-buff item into the same occupied slot in one toggle
- **THEN** exactly the first item's instance is removed and exactly the
  second item's instance exists afterwards

#### Scenario: Unequipping removes exactly its instance

- **WHEN** the actor unequips 藥師珠串 while wearing another buff-granting
  accessory
- **THEN** only the regen instance is removed and the other buff is
  untouched

#### Scenario: Failed toggle leaves no orphan and no ghost

- **WHEN** a toggle transaction fails after an attached-buff apply or
  remove
- **THEN** equipment, gauge ceilings, and buff storage are restored to
  their pre-call state, and live buff reads on the same object show the
  restored state
