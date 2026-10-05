## MODIFIED Requirements

### Requirement: Standing portraits retain contours and truthful grounded fallbacks
Standing portraits SHALL retain their supplied image contours and align their feet or silhouette base with the stage floor. Missing artwork SHALL use the server-selected built-in silhouette — the committed attribute-selected image rendered as its own alpha mask (see `webclient-art-panel`'s reference-artwork requirement) — carrying the subject name and truthful availability state, without inventing generation or a URL; when no fallback media identity is carried (e.g. a scene-kind actor), the existing grounded standing-silhouette treatment SHALL apply unchanged. Repeated visual image captions SHALL be suppressed only on the stage; accessible identity and state SHALL remain available.

#### Scenario: Unavailable portrait is not generating
- **WHEN** an actor has missing or failed art
- **THEN** a grounded silhouette states the subject and missing or failed state once, and no generating shimmer runs

#### Scenario: Pending motion respects preference
- **WHEN** pending art renders at full, reduced and off motion
- **THEN** only full motion animates the silhouette; the pending label remains readable at every level

#### Scenario: The stage silhouette is attribute-selected
- **WHEN** stage actors for an adult male, adult female, child, elder, and monster character all lack artwork in one scene
- **THEN** each renders the silhouette its server-resolved fallback key selects — never one shared shape for every missing actor — with identity and truthful state labels retained

#### Scenario: Compact stage preserves labels
- **WHEN** the player silhouette, vitals and command line render at the 1451x790 reference viewport
- **THEN** the silhouette identity and state are not occluded by vitals or the command line and all HUD controls remain reachable
