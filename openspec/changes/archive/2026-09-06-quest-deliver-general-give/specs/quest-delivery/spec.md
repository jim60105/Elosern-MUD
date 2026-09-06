# Delta spec: quest-delivery (quest-deliver-general-give)

## ADDED Requirements

### Requirement: The general give advances the delivery

The general give command (`給`) SHALL route both of its transfer branches — the canonical-key branch
and the materialized-object branch — through the same committed-transfer advance seam the
dialogue-intent transfer primitive uses, inside its own transaction, with the surrounding give
owning the snapshots and the rollback, so the delivery advance commits atomically with the item
movement and rolls back with it. The snapshots SHALL cover both parties' inventory, quest log, and
traits surfaces, the receiver plan's acquisition pin rooms, and the pin rooms the delivery advance
touches. A failed advance SHALL restore all of them to a byte-identical world, reconcile the moved
objects' in-process caches, and report a safe Traditional Chinese message. The give's established
refusals — unmovable items and refused moves — SHALL keep their existing outcomes.

The general give SHALL perform no quest-scoped refusal and no combat gate: it stays a raw transfer,
a transfer that matches no active delivery stage SHALL move the items and advance nothing, and only
the committed-transfer observer decides progress. The quest-scoped refusal semantics remain the
contract of `交付` / `explore.deliver`.

#### Scenario: Giving the objective key to the bound recipient advances the stage

- **WHEN** the holder gives the objective's registry key to the stage's bound recipient through the
  general give's canonical-key branch
- **THEN** the transfer commits and the delivery stage advances by the transferred quantity, capped
  at the objective quantity, exactly as an intent-driven transfer would

#### Scenario: Giving a partially completing quantity leaves the stage advertising the remainder

- **WHEN** the holder gives fewer items than the stage's remaining objective quantity to the bound
  recipient
- **THEN** the stage advances by the transferred quantity and the exploration affordance keeps
  advertising the remaining quantity

#### Scenario: Giving a materialized registry object advances the stage

- **WHEN** the holder gives materialized objects whose registry keys match the objective's
  `item_key` to the bound recipient
- **THEN** the objects move, the canonical key list updates on both sides, and the delivery stage
  advances by the number of matching keys moved, one advance per distinct key

#### Scenario: Giving to an unbound recipient transfers and advances nothing

- **WHEN** the holder gives a registry key to a co-located target that is not the bound recipient
  of any active delivery stage
- **THEN** the transfer commits normally, no quest state changes, and no refusal is raised

#### Scenario: A mid-combat qualifying give advances the stage

- **WHEN** the holder has an active combat session and gives the objective's item to the bound
  recipient
- **THEN** the give is not combat-gated: the transfer commits and the delivery stage advances, per
  the raw-verb honesty split

#### Scenario: A failed advance rolls the whole give back

- **WHEN** the delivery advance fails after the give's inventory plans applied
- **THEN** the give's transaction rolls back, both parties' inventories, quest logs, traits, and
  the receiver plan's acquisition pin state are byte-identical to before the command, the moved or
  materialized objects' in-process caches are reconciled with the rolled-back database, and the
  player receives a safe Traditional Chinese failure message
