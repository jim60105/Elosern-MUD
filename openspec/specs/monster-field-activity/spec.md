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
- **WHEN** a candidate has unknown activity/area/daypart references, impossible bounds or nonpositive/bool timing
- **THEN** the whole candidate rejects and the previous published registry remains unchanged

#### Scenario: Separate topology
- **WHEN** activity bounds include lawful settlement surroundings or a stationary exam/site
- **THEN** birth buffers do not become movement barriers and explicit stationary bindings grant no automatic movement or new combat ability

#### Scenario: Every possible solitary outcome is valid
- **WHEN** a solitary binding references a composition whose inclusive ranges permit more than one total member, including through a site override
- **THEN** publication accepts it; the member count never selects or rejects a policy, and construction disperses the members into one-member groups

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

### Requirement: Placements form movement groups from their binding policy
Zone births and manual-site population SHALL form movement groups from the policy of the binding each individual resolves. Individuals sharing one cohesive-group binding SHALL form one group; each solitary-roaming or stationary individual SHALL form its own one-member group. The read-only forecast SHALL project the same groups, and a failed placement SHALL leave no group.

#### Scenario: Solitary birth disperses
- **WHEN** a synthetic zone commits a solitary-bound birth of three individuals at one cell
- **THEN** three one-member groups exist at that home cell with their own saved decisions, and a later due decision moves one group while the other two stay

#### Scenario: Cohesive birth stays whole
- **WHEN** a synthetic zone commits a cohesive-bound mixed birth
- **THEN** exactly one group holds every constructed member

#### Scenario: Manual site formation
- **WHEN** a synthetic site populates a three-member composition once under a cohesive binding and once under a stationary binding
- **THEN** the cohesive population creates one three-member group and the stationary population creates three one-member groups, all owned by the site

#### Scenario: Forecast agreement
- **WHEN** the read-only forecast projects a zone birth or a matured site recovery
- **THEN** the number of projected groups and each group's member count equal what the committed writer creates for the same saved selection

#### Scenario: Failure leaves no partial grouping
- **WHEN** group registration fails after an earlier group of the same placement was written
- **THEN** individuals, groups, zone or site state, coordinates and live room caches equal the pre-placement state and a retry reproduces the same selection
