## ADDED Requirements

### Requirement: Scene tiles are landscape and open no tray
Scene subject tiles SHALL render at 16:9 with their committed tile artwork, and selecting one SHALL open no tray because the scene kind holds one card.

#### Scenario: Selecting a scene opens no tray
- **WHEN** a committed v4 fixture's `scene` category lists two scene subjects and one is selected with `max_cards: 1`
- **THEN** both tiles are landscape, no tray renders, and the owner tile carries no `aria-expanded`
