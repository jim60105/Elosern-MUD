# Spec Delta

## ADDED Requirements

### Requirement: Island movement uses scale-aware effective motion
For unchanged mode and level, island movement SHALL retain its existing FLIP pan and move world-anchored dots with the drawing. A changed level or mode SHALL use a short crossfade for effective full motion and switch immediately for effective reduced or off motion. Overlay and instance/interior transitions SHALL remain unchanged.

#### Scenario: Same scale pans the ground
- **WHEN** a move commits with unchanged projection level and mode
- **THEN** the existing pan transition is used and dots move with the same drawing transform instead of staying screen-fixed; final dot anchors still match world multiples.

#### Scenario: A changed level or mode never uses equal-scale FLIP
- **WHEN** a move changes uniform level or switches between uniform and compressed mode
- **THEN** full motion uses a short crossfade under the shared motion tokens; reduced/off commit the new projection immediately, without an animated scale interpolation or lingering previous-scale frame.

#### Scenario: Real gateway journey remains usable
- **WHEN** the player walks Altoria south gate to wilderness and back in the real client
- **THEN** each settled island shows current and every available adjacent exit, valid far-side gate labels and usable return controls; the overlay still uses its existing lattice and coordinate-free layouts remain unchanged.
