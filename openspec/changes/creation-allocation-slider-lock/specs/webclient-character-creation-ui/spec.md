## MODIFIED Requirements

### Requirement: Creation controls preserve native entry and existing authority
Themed creation selects and checkboxes SHALL preserve native keyboard/IME behavior. Each allocation axis SHALL pair direct numeric entry with a synchronized slider bounded by the server point cap, render its point range as `low~high`, and disable its controls while its point cap and value are both zero; a zero-cap slider is always disabled. Steppers and sliders SHALL use only existing server bounds and budget rules; previews SHALL NOT become a second stat authority.

#### Scenario: Invalid allocation is edited
- **WHEN** a player types a value outside its advertised range
- **THEN** the existing validation/error path remains effective and preview does not silently make it valid

#### Scenario: Concept fill settles
- **WHEN** a concept proposal arrives while its request is in flight
- **THEN** the existing revision-gated custom-form fill and confirmation flow remain unchanged by layout

#### Scenario: Slider and numeric entry stay synchronized
- **WHEN** a player moves an axis slider, or types an in-range value into the axis number field
- **THEN** the other control shows the same value, the submitted allocation equals it, and the slider spans `0` to the axis point cap in steps of one without clamping to the remaining budget

#### Scenario: Point ranges use a tilde separator
- **WHEN** the custom form shows an axis help line, the budget briefing, or an out-of-cap allocation error for a profile
- **THEN** each axis point range reads `0~<point_cap>` and none of them separates the bounds with a hyphen or dash

#### Scenario: A zero-cap axis is locked
- **WHEN** the resolved profile gives an axis a point cap of zero and the axis value is zero
- **THEN** that axis's number field, slider and both steppers are disabled, the row is marked locked, and its value is still submitted as zero

#### Scenario: Changing race or subrace clears zero-cap points
- **WHEN** a player selects a race or subrace whose resolved profile gives an axis a point cap of zero while that axis holds a non-zero value
- **THEN** the axis value becomes zero and its controls are locked

#### Scenario: A stale value on a zero-cap axis stays correctable
- **WHEN** a zero-cap axis holds a non-zero value that did not come from a race or subrace change
- **THEN** its number field stays enabled, the row is not marked locked, and confirming reports the existing out-of-cap error on that axis's number field
