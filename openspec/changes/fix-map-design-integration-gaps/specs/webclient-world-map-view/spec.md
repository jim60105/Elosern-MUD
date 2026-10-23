# Spec Delta

## MODIFIED Requirements

### Requirement: Newly lit districts animate accessibly from their landmark
After the first fresh world snapshot of a drawer opening establishes its baseline, a previously unlit district becoming lit through a subsequent eligible committed discovery while open SHALL play one 600 ms landmark-origin ink spread and announce 已探明：<district>. Reduced/off motion SHALL switch instantly. Initial data, retained cache, repeated payloads, reopening already-lit districts and epoch retirement SHALL not replay discovery.

#### Scenario: New discovery update arrives while visible
- **WHEN** a district transitions from unlit to lit in an active map session after its fresh opening baseline through an eligible committed discovery
- **THEN** one ink spread starts at its landmark and one live announcement is emitted

#### Scenario: Reduced motion or existing knowledge
- **WHEN** reduced motion is active or already-lit data is initially rendered
- **THEN** reduced motion applies instantly and existing knowledge does not produce a new discovery animation/announcement

#### Scenario: Closed-period knowledge is present in the opening response
- **WHEN** a stale cached unlit body precedes the current opening's fresh response containing a district discovered while the drawer was closed
- **THEN** that district appears lit without ink or discovery announcement; later repeated replies or tab remounts do not replay it

#### Scenario: A real open discovery remains single-shot
- **WHEN** the fresh baseline contains an unlit district and a later committed move while the world view is active lights it, followed by repeated identical replies
- **THEN** full motion reveals from the supplied landmark over 600 ms and announces once, reduced/off render instantly with one live announcement, and repeated replies add neither another animation nor another announcement

#### Scenario: Opening and session retirement cancel pending effects
- **WHEN** the drawer closes, a world tab is remounted or the transport generation or epoch changes with queued reveal frames or announcements
- **THEN** stale effects are cancelled, cached or initially lit districts cannot replay, and returning to the tab retains eligible viewport memory without treating remounted knowledge as a new discovery
