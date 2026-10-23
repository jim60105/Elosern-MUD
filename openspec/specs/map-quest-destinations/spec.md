# map-quest-destinations Specification

## Purpose
Resolve accepted commission destinations read-only into canonical map identity and world location for area and world map presenters.

## Requirements

### Requirement: Accepted commission destinations resolve on the server
For each accepted commission the server SHALL resolve ANCHOR locators to the anchor cell, GRID locators to the settlement anchor cell, wilderness species hunts to the point in the target terrain region nearest the player, and monster sites to the site cell. Resolution SHALL preserve canonical node identity for an on-map destination and SHALL NOT mutate quests, knowledge, rooms or clock.

#### Scenario: Locator families use their canonical source
- **WHEN** accepted commissions have ANCHOR, GRID and monster-site destinations
- **THEN** their world positions equal the relevant canonical anchor or site cells, while an on-area GRID destination retains its actual node identity instead of its anchor-cell world display position

#### Scenario: Nearest hunt point is deterministic
- **WHEN** two points in the target hunt region have equal nearest distance to the player
- **THEN** resolution chooses a documented stable coordinate tie order and repeated reads return the same point without spawning a monster or room

#### Scenario: Unlocatable destinations are not fabricated
- **WHEN** a commission has no supported resolvable destination
- **THEN** the map has no invented node or coordinate for that commission and other accepted destinations remain usable
