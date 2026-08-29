## ADDED Requirements

### Requirement: Gauge ceilings stay synced with worn equipment

Every successful equipment toggle SHALL recompute each gauge trait's
non-literal ceiling adjustment from scratch as the sum of the currently
worn items' gauge caps (positive-only by rulebook contract) inside the same
transaction as the equipment write, with trait storage snapshotted and
restored on failure. When a recompute lowers a ceiling, the same transaction
SHALL settle the gauge's current value to the lowered ceiling (a
deterministic resource cost of unequipping), so stored state can never
exceed its effective maximum. The literal base maximum SHALL never be
written, the recompute SHALL never accumulate, and reported maxima, heal
clamps, full restores, and recovery SHALL consequently observe the effective
maximum.

#### Scenario: Equipping a capped item raises the live maximum

- **WHEN** an actor equips an item granting `gauge_caps hp +15` and then
  heals past the pre-equip maximum
- **THEN** healing succeeds up to the raised effective maximum and the
  trait's stored literal base is unchanged

#### Scenario: Unequipping settles excess current to the lowered ceiling

- **WHEN** an actor at full effective HP unequips the `hp +15` item
- **THEN** current settles to the lowered ceiling inside the toggle
  transaction and the status read model renders the row without error

#### Scenario: Recompute never accumulates

- **WHEN** an actor repeatedly equips and unequips a mix of capped items
  through ten toggles
- **THEN** the ceiling adjustment equals exactly the sum over the currently
  worn set, with no residue from prior equipment

#### Scenario: Failed toggle restores gauge ceilings

- **WHEN** a toggle's transaction fails after the ceiling recompute
- **THEN** both the equipment mapping and the gauge traits are restored to
  their pre-call state
