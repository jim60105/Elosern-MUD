## ADDED Requirements

### Requirement: Standing portraits retain contours and truthful grounded fallbacks
Standing portraits SHALL retain their supplied image contours and align their feet or silhouette base with the stage floor. Missing artwork SHALL use a standing silhouette with the subject name and truthful availability state, without inventing generation or a URL. Repeated visual image captions SHALL be suppressed only on the stage; accessible identity and state SHALL remain available.

#### Scenario: Unavailable portrait is not generating
- **WHEN** an actor has missing or failed art
- **THEN** a grounded silhouette states the subject and missing or failed state once, and no generating shimmer runs

#### Scenario: Pending motion respects preference
- **WHEN** pending art renders at full, reduced and off motion
- **THEN** only full motion animates the silhouette; the pending label remains readable at every level

#### Scenario: Compact stage preserves labels
- **WHEN** the player silhouette, vitals and command line render at 1280x720
- **THEN** the silhouette identity and state are not occluded by vitals or the command line and all HUD controls remain reachable
