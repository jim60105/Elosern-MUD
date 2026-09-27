## ADDED Requirements

### Requirement: Creation presents a bounded desktop identity form and allocation workspace
The creation wizard SHALL organize identity/race context, a bounded-width form and allocation preview into three desktop regions. All current required and optional fields, errors and confirmation actions SHALL remain reachable at 1280x720, 1440x900 and 1920x1080 without page-level horizontal scrolling. Preset cards SHALL use the available grid evenly and SHALL NOT claim unprovided portrait art.

#### Scenario: Custom form remains complete
- **WHEN** a keyboard user completes creation at 1280x720
- **THEN** name, sex, both ages, race/subrace, allocations and optional fields are reachable in logical order, with visible errors and confirmation controls

#### Scenario: Preset lacks artwork
- **WHEN** preset cards render without portrait references
- **THEN** cards show truthful authored identity and decorative local artwork only, never a fabricated portrait URL

### Requirement: Creation controls preserve native entry and existing authority
Themed creation selects and checkboxes SHALL preserve native keyboard/IME behavior. Allocation steppers SHALL retain direct numeric entry and use only existing server bounds and budget rules; previews SHALL NOT become a second stat authority.

#### Scenario: Invalid allocation is edited
- **WHEN** a player types a value outside its advertised range
- **THEN** the existing validation/error path remains effective and preview does not silently make it valid

#### Scenario: Concept fill settles
- **WHEN** a concept proposal arrives while its request is in flight
- **THEN** the existing revision-gated custom-form fill and confirmation flow remain unchanged by layout
