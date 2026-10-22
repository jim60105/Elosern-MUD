# Spec Delta

## MODIFIED Requirements

### Requirement: Recent deed rendering has complete bounded groups
Groups SHALL sort by latest included tick descending and stable source identity ascending, retaining at most eight. Every retained group SHALL carry occurrence time and location context from its committed sources. Event JSON, envelope and references SHALL fit 8000 Unicode code points by dropping older complete groups. Oversized singleton groups SHALL be omitted. Claims SHALL retain their outcomes and supporting IDs; empty rendering SHALL mean empty material.

#### Scenario: Deterministic tie and cap
- **WHEN** more than eight groups share several latest ticks
- **THEN** the newest eight follow stable source tie order

#### Scenario: Unicode and oversized groups
- **WHEN** non-ASCII groups and their references exceed the budget or one group cannot fit alone
- **THEN** complete groups are omitted until valid complete JSON fits, with no clipped outcome or unsupported claim

#### Scenario: No renderable evidence
- **WHEN** every eligible group is too large
- **THEN** the feed is empty and cannot justify generation

#### Scenario: Different locations are rendered without misattribution
- **WHEN** eligible groups include a compressed group whose occurrences span rooms and an encounter with an action in another room
- **THEN** rendered facts retain each occurrence's authorized time and location context and the request remains valid within the existing group and JSON limits

#### Scenario: Renamed room does not change a committed fact
- **WHEN** a rendered source location is renamed or removed after settlement
- **THEN** the request still describes the committed location snapshot without reading the live room or truncating the JSON

#### Scenario: Context growth removes only whole groups
- **WHEN** adding authorized location and objective context exceeds the rendering budget
- **THEN** the oldest complete groups are dropped and every retained fact keeps its source IDs and outcomes

### Requirement: Nomination diagnostics preserve privacy
Nomination workflow diagnostics SHALL identify player, trigger, frozen tick and source counts through the existing observability boundary. Exceptions SHALL retain exception context. Operational logs SHALL omit full private deed prose; transcript payloads SHALL follow existing retention and credential exclusions.

#### Scenario: Bounded operational context
- **WHEN** a source query or generation raises after gameplay commits
- **THEN** a bounded workflow diagnostic carries exception context and no full private deed prose

#### Scenario: Admitted workflow diagnostics use the selection tick
- **WHEN** a nomination is admitted at nonzero world tick and later generation or persistence fails
- **THEN** admission, selection and failure diagnostics all use the same frozen tick rather than zero or a later clock value

#### Scenario: Nomination does not extend gameplay transaction
- **WHEN** a nomination is admitted while the world clock continues advancing
- **THEN** selection retains the admitted tick window and does not recalculate it after model response or reading gameplay state
