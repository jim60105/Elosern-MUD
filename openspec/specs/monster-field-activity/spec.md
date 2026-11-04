# monster-field-activity Specification

## Purpose
Validate immutable field activity, bounded geometry and aggression bindings separately from birth geometry and combat behavior profiles.

## Requirements

### Requirement: Activity declarations publish complete validated bindings
Activity publication SHALL atomically validate explicit bounded policy, positive decision timing and aggression references for each supported composition or placement before exposing immutable declarations.

#### Scenario: Complete forms
- **WHEN** stationary, solitary-roaming and cohesive-group declarations resolve region-intersection or home-distance geometry
- **THEN** legal-cell predicates derive from the same candidate map; count-compatible bindings resolve without interpreting prose or species labels

#### Scenario: Atomic rejection
- **WHEN** a candidate has unknown activity/area/daypart references, impossible bounds, nonpositive/bool timing or incompatible solitary/group members
- **THEN** the whole candidate rejects and the previous published registry remains unchanged

#### Scenario: Separate topology
- **WHEN** activity bounds include lawful settlement surroundings or a stationary exam/site
- **THEN** birth buffers do not become movement barriers and explicit stationary bindings grant no automatic movement or new combat ability

#### Scenario: Every possible solitary outcome is valid
- **WHEN** a solitary binding references a composition whose inclusive ranges permit more than one total member, including through a site override
- **THEN** publication rejects before sampling; a sampled singleton cannot authorize an incompatible possible outcome

### Requirement: Due activity moves bounded complete groups globally
Each actual activity group SHALL make saved deterministic positive-interval decisions globally, with cohesive members sharing one lawful affordable route inside ordinary bounds and stationary bindings remaining stationary.

#### Scenario: Unobserved and restart
- **WHEN** an inactive cell contains a due solitary or cohesive mixed group and game time advances
- **THEN** saved selection chooses stay or a complete legal journey without creating rooms; reload/repeated reads never redraw or move a subset

#### Scenario: Slowest member and topology
- **WHEN** group members differ in speed, access, corner legality or full-route reserve
- **THEN** the slowest self-moving member determines canonical duration and any required member refusal makes the group stay; birth exclusions do not block lawful travel

#### Scenario: Stationary bindings
- **WHEN** a manual site, quest or designated exam has no explicit roaming declaration
- **THEN** ordinary activity neither moves it nor restores a cleared site or changes its bound identities

#### Scenario: Return after escape
- **WHEN** a detached escaped member is outside its activity area at its next opportunity
- **THEN** it prefers a lawful adjacent step directly inside the original bounds, otherwise waits and retries without teleport, replacement or unlimited exploration
