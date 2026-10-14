# Spec Delta

## MODIFIED Requirements

### Requirement: The presence rail shows people and objects on the stage floor
In exploration mode the stage SHALL render `PresenceRail` right-aligned on the stage floor, inset left of the right-hand island column: interact targets as gold medallions, other present entities as dashed muted medallions, then a separator and objects as steel lozenges, in `ExplorationMenu.presenceEntries` order, each with a name plate. It SHALL yield to the foe line-up in combat, hide during dialogue and under a centred card, and render nothing when empty.

#### Scenario: Entries follow the overview order
- **WHEN** the room has two interact targets, one bystander, and two objects
- **THEN** the rail shows two gold medallions, one dashed muted medallion, a separator, and two lozenges, each with its name plate, in that order

#### Scenario: A medallion shows the face crop or the initial
- **WHEN** a target or bystander's `portrait_ref` resolves to a URL-bearing image in the art catalog
- **THEN** its medallion shows the face crop through the existing face-rect data

#### Scenario: A medallion without a portrait shows the initial
- **WHEN** a target or bystander has no `portrait_ref`, its catalog entry is unknown or unavailable, or its real image fails to load
- **THEN** its medallion shows the first character of the target's name

#### Scenario: The rail is hidden outside exploration and under a card
- **WHEN** the mode is combat or dialogue, or a centred card is open
- **THEN** the rail is not visible and takes no focus

#### Scenario: An empty room renders no rail
- **WHEN** the room has no people and no objects
- **THEN** the rail renders no element and no placeholder

#### Scenario: Replacement art recovers after a failed face image
- **WHEN** a medallion's image fails to load and a newer committed art entry replaces that image URL
- **THEN** the failed image uses the name initial and the new URL can render its supplied face crop without dispatch or reopening the rail

## ADDED Requirements

### Requirement: Non-party person focus uses the admitted portrait and truthful fallback
A focused target rendered outside the companion lineup SHALL use its server-authored exploration reference to resolve the current art catalog image, preserving the existing stage placeholder when null, unknown, unavailable or failed. Catalog updates SHALL refresh the open target without reopening its verb card or dispatching a focus action.

#### Scenario: An accepted portrait reaches non-party focus
- **WHEN** an accepted exploration snapshot names a real catalog image for a non-lineup target and its medallion opens the verb card
- **THEN** the medallion renders the supplied face crop and the actor-right figure renders that image using the supplied stage geometry; opening sends no action and pushes no frame

#### Scenario: A non-party image cannot load
- **WHEN** the non-party target's real image fails to load or its reference resolves to no usable image
- **THEN** focus retains the same target and usable verbs while the figure shows the established truthful placeholder without inventing a URL

#### Scenario: Current art refresh reaches an open card
- **WHEN** one newer committed update supplies a usable reference and image for the still-focused target, or replaces its prior catalog image URL
- **THEN** that open card's figure renders the new admitted image, its target identity and verb order remain unchanged, and no focus message is sent
