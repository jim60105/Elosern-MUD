# Spec Delta

## MODIFIED Requirements

### Requirement: The resolver table completes with the combat and creation families

The resolver table SHALL additionally implement, and produce the menus the migrated push sites produce today: the combat family — `combat.root` `{}`, `combat.categories` `{}`, `combat.category` `{categoryIndex}`, `combat.group` `{categoryIndex, groupIndex}`, `combat.skill` `{skillKey}`, `combat.target` `{skillKey}`; the creation family — `creation.root` `{}`, `creation.presets` `{}`, `creation.form` `{view: "custom" | "concept"}`, `creation.confirm` `{kind, presetKey?}`.

#### Scenario: Every completed-table source resolves from a live snapshot

- **WHEN** each combat and creation source is resolved against a committed snapshot of its owning mode with valid params
- **THEN** each returns the menu its migrated push site produced, with the same row keys, server-authored payloads, and titles

#### Scenario: The retired party-exit frame never resolves

- **WHEN** a `combat.forfeit` descriptor reaches resolve after the party-scope exit cutover
- **THEN** it is an unregistered source and resolves to the shared unresolvable marker, and no live dock frame ever holds that descriptor

#### Scenario: No services descriptor is registered

- **WHEN** any `services.*` descriptor (for example `services.guild` or `services.stock`) resolves against any committed state
- **THEN** resolve returns the shared unresolvable marker (an unregistered source), and no router frame in any live mode ever holds a `services.*` descriptor

#### Scenario: No dialogue descriptor is registered

- **WHEN** `dialogue.root` resolves against any committed state
- **THEN** resolve returns the shared unresolvable marker (an unregistered source), and no router
  frame in any live mode ever holds a `dialogue.root` descriptor

#### Scenario: Combat sources read the combat-form context_actions panel

- **WHEN** a combat-family descriptor resolves
- **THEN** it reads the panel `context_actions` in its combat form, with selection state owned by the combat model

#### Scenario: Creation sources read the creation panel

- **WHEN** a creation-family descriptor resolves
- **THEN** it reads the panel `creation`

#### Scenario: Creation form resolves to the wizard's empty marker frame

- **WHEN** `creation.form` resolves with `{view: "custom" | "concept"}`
- **THEN** it resolves to the wizard's empty marker frame

#### Scenario: Services render outside the dock

- **WHEN** any service surface is presented
- **THEN** the committed `services` panel has no dock frame and every service surface renders in a frameless reference drawer or overlay, which is why no services family is implemented

#### Scenario: Dialogue presents in the narrative caption

- **WHEN** dialogue mode is live
- **THEN** dialogue keeps the exploration root frame in the dock and presents its scripted picks in the narrative caption, which is why no dialogue family is implemented

#### Scenario: Services and dialogue families are explicitly not implemented

- **WHEN** the completed resolver table is declared
- **THEN** it implements no services family and no dialogue family, and any `services.*` or `dialogue.*` descriptor is an unregistered source that resolves to the unresolvable marker
