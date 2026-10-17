# Spec Delta

## MODIFIED Requirements

### Requirement: Out-of-combat item use advances deterministic time once
A successful out-of-combat item use SHALL compose its complete item plan and the player-driven world's canonical six-second advance inside one outer transaction and rollback journal; that advance SHALL settle the user's present party scope. A rejected or failed use SHALL advance no time. A failure in any due clock callback SHALL roll back the item effect, consumption, contained mirror, clock, due-event effects, and all in-process caches together. Combat use SHALL add no command-default time because combat-session round settlement owns elapsed time.

#### Scenario: Exploration use advances six seconds
- **WHEN** an injured actor successfully uses a healing potion outside combat
- **THEN** the item effect and consumption commit and the world clock advances exactly six seconds once

#### Scenario: Rejected exploration use advances no time
- **WHEN** a full-HP actor attempts to use a healing potion outside combat
- **THEN** the world clock and every item-use surface remain unchanged

#### Scenario: Clock callback failure rolls back item use
- **WHEN** a due deterministic clock callback fails during the six-second advance after item planning
- **THEN** HP, inventory, contained mirror, clock tick, due-event state, and in-process caches all equal their pre-use values

#### Scenario: Exploration use settles the present party
- **WHEN** the commander successfully uses a potion outside combat with companion 艾拉 present
- **THEN** the six-second advance settles the commander and 艾拉 together, and a clock-callback failure
  restores both members' surfaces
