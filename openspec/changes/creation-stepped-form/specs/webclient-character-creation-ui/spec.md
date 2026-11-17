# Spec Delta

## MODIFIED Requirements

### Requirement: Creation presents a bounded desktop identity form and allocation workspace
The creation wizard SHALL present a persistent portrait slot beside freely navigable identity, story and allocation steps, with confirmation in its shared footer. All current required and optional fields, errors and confirmation actions SHALL remain reachable at 1451x790 and 2560x1440 without page-level horizontal scrolling. Preset cards SHALL render server-supplied canonical artwork in one card wall without inventing media URLs.

#### Scenario: Custom form remains complete
- **WHEN** a keyboard user completes creation at the 1451x790 reference viewport
- **THEN** name, sex, both ages, race/subrace, allocations and optional fields are reachable in logical order, with visible errors and confirmation controls

#### Scenario: Preset lacks artwork
- **WHEN** a synthetic preset’s descriptor has no official image attempt
- **THEN** the card uses the supplied alpha terminal through the shared artwork loader, never a fabricated portrait URL

## ADDED Requirements

### Requirement: Custom step navigation preserves unsent form authority
The custom form SHALL keep its current step locally, preserve unsent field values across step changes, and display the descriptor-derived remaining allocation points on the step rail. Existing validation SHALL route focus to the first invalid field’s step without introducing new creation rules.

#### Scenario: Free navigation keeps values
- **WHEN** a player moves directly between nonadjacent steps or uses the previous/next controls
- **THEN** unsent values survive, no server action is sent, and the footer confirmation remains usable on every step

#### Scenario: Validation reveals the first invalid field
- **WHEN** existing native or custom submission validation identifies invalid fields
- **THEN** the step containing the first invalid field in identity/story/allocation display order opens, receives focus at that field, and the step has a non-color error indicator and associated message

#### Scenario: Remaining points are presentation arithmetic
- **WHEN** allocations or the selected server profile change while any step is open
- **THEN** the rail displays the profile budget minus the entered allocation sum without clamping invalid input or authorizing submission

#### Scenario: Empty portrait follows the table
- **WHEN** sex or apparent age changes before live portrait integration
- **THEN** the persistent slot selects the matching server silhouette interval, shows the current name or an unnamed label, and offers no generation control

### Requirement: Concept guide completion follows proposal fields
The concept guide SHALL derive completion indicators from present values in the current proposal contract, excluding sex and portrait. A fresh concept apply SHALL return the custom form to its identity step without submitting the form or copying concept text into a portrait prompt.

#### Scenario: A partial proposal marks only supplied values
- **WHEN** a synthetic proposal omits some optional fill fields
- **THEN** guide indicators distinguish present values from absent ones and claim neither sex nor portrait completion

#### Scenario: Existing proposal does not navigate on rebuild
- **WHEN** a rebuild or remount re-renders an unchanged proposal revision
- **THEN** existing revision-gated fill behavior remains and there is no new navigation, submission or success toast
