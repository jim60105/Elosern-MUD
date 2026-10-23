# Spec Delta

## MODIFIED Requirements

### Requirement: Accepted commission destinations resolve on the server
For each accepted commission the server SHALL resolve ANCHOR and GRID locators to their anchor cells, regional species hunts to the nearest target-region point and monster sites to site cells. Actor and instance origins SHALL use canonical enclosing anchors for uniquely registered ordinary interiors. Resolution SHALL retain on-map node identity and SHALL NOT mutate quests, knowledge, rooms or clock, including absent persistent instance-origin Attributes.

#### Scenario: Locator families use their canonical source
- **WHEN** accepted commissions have ANCHOR, GRID and monster-site destinations
- **THEN** their world positions equal the relevant canonical anchor or site cells, while an on-area GRID destination retains its actual node identity instead of its anchor-cell world display position

#### Scenario: Nearest hunt point is deterministic
- **WHEN** two points in the target hunt region have equal nearest distance to the player
- **THEN** resolution chooses a documented stable coordinate tie order and repeated reads return the same point without spawning a monster or room

#### Scenario: Unlocatable destinations are not fabricated
- **WHEN** a commission has no supported resolvable destination
- **THEN** the map has no invented node or coordinate for that commission and other accepted destinations remain usable

#### Scenario: A registered service interior supplies the hunt origin
- **WHEN** the active actor stands in an ordinary service room tagged to registered places belonging to one enclosing anchor with canonical geography and has an accepted regional species hunt
- **THEN** the hunt uses that anchor cell as its origin and yields the supported nearest-region destination; other accepted ANCHOR, GRID and site destinations remain available and the room remains coordinate-free

#### Scenario: An instance entered from a registered interior retains canonical positioning
- **WHEN** an actor's instance origin or a commission's bound-instance destination origin is a uniquely registered ordinary interior
- **THEN** its enclosing anchor cell supplies the world position while the instance destination retains its canonical room identity; no room-local coordinates or additional map knowledge are created

#### Scenario: Missing and ambiguous origins stay unknown without writes
- **WHEN** resolution reads a missing persistent instance-origin Attribute, an origin that is another instance, an unregistered interior, conflicting enclosing anchors or a registration with missing geography
- **THEN** no origin coordinate is fabricated, the absent Attribute stays absent in persistence, and unrelated resolvable destinations remain usable; a live bound-instance room may retain its canonical identity with unknown world position
