## ADDED Requirements

### Requirement: Scene subjects carry the background in effect and its sentence
For a scene subject the panel SHALL carry, as tile artwork, the descriptor of the archetype's background in effect (its scene gallery card, else its bundled image), its stored card rows with descriptors whose terminal is the archetype's bundled scene image rather than a person silhouette, and, while it is selected, the archetype's scene sentence as `description`. Both validators SHALL accept scene subject keys and `gallery/scene/` card URLs.

#### Scenario: A scene without a card shows its bundled image
- **WHEN** the selected scene subject `scene:t_arch` has no gallery card
- **THEN** its tile artwork resolves the bundled `t_arch` image, `cards` is empty, and `description` is `t_arch`'s sentence

#### Scenario: A scene card row is a landscape original
- **WHEN** `scene:t_arch` holds one card
- **THEN** its row carries the card's original under `gallery/scene/t_arch/` and a bundled-scene terminal, and both validators accept the payload

#### Scenario: Non-scene subjects carry no description
- **WHEN** the selected subject is a character or monster
- **THEN** `description` is null
