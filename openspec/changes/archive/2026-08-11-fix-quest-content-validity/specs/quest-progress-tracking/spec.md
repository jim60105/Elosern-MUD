## ADDED Requirements

### Requirement: Arrival observation advances at most one per event and never exceeds quantity

REACH/ESCORT arrival observation SHALL increment stage progress by at most one per matching arrival event and SHALL cap progress at the objective quantity, so even a non-1 quantity (should one slip through) can never jump to full completion in a single arrival. The post-follow re-observation (party-follow D-2) SHALL NOT re-count the same arrival event: when a companion was already present in the destination, the re-run is skipped because the first observation has already advanced every matching stage for that event.

#### Scenario: First arrival with quantity one completes the stage

- **WHEN** the player arrives at a matching destination with companion co-presence and the stage quantity is 1
- **THEN** progress becomes 1, the stage completes exactly once, and a repeated post-follow observation advances nothing

#### Scenario: Arrival never over-fills progress

- **WHEN** a matching arrival would advance progress beyond the objective quantity
- **THEN** progress is capped at the quantity and the quest transitions at most once
