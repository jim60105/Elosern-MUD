# wilderness-travel-planning Specification

## Purpose
Expose bounded read-only travel.plan with sequential settlement prediction. This capability owns its observable mechanism and rejection boundaries.

## Requirements

### Requirement: Travel queries route within revealed wilderness
travel.plan SHALL perform a read-only bounded route query over revealed passable cells in the current window using canonical duration weights and diagonal legality.

#### Scenario: Routing and errors
- **WHEN** synthetic terrain contains a river, blocked diagonal, cheaper road, fog and a winding route>60 steps
- **THEN** routing obeys constraints, prefers lower cost and produces the specified outside/unrevealed/unreachable/too-long errors

#### Scenario: Read isolation and publication
- **WHEN** a valid/refused query enters production dispatch
- **THEN** no gameplay/object/Attribute/clock state changes and only bounded correlated result data publishes

### Requirement: Travel prediction matches sequential admitted steps
Travel planning SHALL predict admitted per-step duration and worst fatigue using existing rounded traversal/reserve rules and deterministic pace/nightfall stop indices.

#### Scenario: Committed equivalence
- **WHEN** heterogeneous synthetic travellers walk the predicted admitted prefix through real transactional steps
- **THEN** durations/stages match each prediction, including within-step thresholds and exact-zero sleep

#### Scenario: Stops and refusal
- **WHEN** all paces, initially advanced fatigue, night entry, zero destination and first/later preflight refusal are queried
- **THEN** indices/reasons follow design.md, first refusal/asleep returns party-cannot-travel and later refusal exposes only admitted steps

#### Scenario: Flight charge follows execution after admission
- **WHEN** a synthetic actor owns allowed flight, restricted flight or only flash_step and the present party includes eligible or sleeping/depleted travellers
- **THEN** normal physical preflight still decides admission, allowed flight alone produces zero charged seconds and unchanged reserves/calendar, and every admitted prediction matches real settlement

#### Scenario: Initial pace state agrees with move interruption
- **WHEN** identical light, moderate or severe initial fatigue is used for a query and a move with the same walk context
- **THEN** both stop after the first legal step when already at or beyond the selected voluntary threshold, while forced pace has no voluntary stop

#### Scenario: Frozen route selection is distinct from replay
- **WHEN** two synthetic routes rank differently under initial-fatigue edge weights and cumulative fatigue replay
- **THEN** selection follows the frozen weights and each returned admitted step still predicts its actual sequential charged settlement
