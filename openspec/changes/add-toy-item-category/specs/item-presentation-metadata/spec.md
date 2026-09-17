## MODIFIED Requirements

### Requirement: Item presentation keys are safe, closed renderer contracts
Item kinds, icon keys, and rarity values SHALL be closed `StrEnum` vocabularies owned by `world.lore.items`.
The registry SHALL NOT carry free-form emoji, raw SVG, HTML, image URLs, CSS values, or localized text
used as a renderer selector. The closed kind vocabulary SHALL cover every item category the lore item
codex defines, and the client's local icon map SHALL cover the icon-key vocabulary member-for-member, so
that adding a category is a two-sided edit and no shipped item can resolve to the unknown-item fallback.
The fallback SHALL remain in place for a payload whose presentation is absent or whose icon key the
client does not yet know, and SHALL NOT be reachable by any registered item.

#### Scenario: Invalid visual identity data is rejected during registry validation
- **WHEN** an item definition supplies a value outside a presentation enum or an invalid summary
- **THEN** the registry-focused test fails before a presenter can publish the item

#### Scenario: The client icon map matches the server icon vocabulary exactly
- **WHEN** the client's icon-map keys are compared against the server's icon-key vocabulary
- **THEN** the two sets are equal, with every entry carrying inline path data and a Traditional Chinese label

#### Scenario: No registered item falls back to the unknown glyph
- **WHEN** every registered item's icon key is resolved through the client icon map
- **THEN** each resolves to a mapped entry, and the unknown-item fallback is reached only by an absent presentation
