## MODIFIED Requirements

### Requirement: The creation dock is keyboard-first, form-capable, and confirmation-protected
In `creation` mode the action dock SHALL present preset cards and the custom form rather
than exploration or service menus. Arrow keys SHALL navigate finite lists and buttons, Tab
and Shift+Tab SHALL move focus through text/numeric fields, Enter SHALL activate the
focused control or submit a complete server-declared form, and Escape SHALL pop exactly one
menu level without discarding the saved server wizard draft. The custom form SHALL require a
subrace selection (no "無子種族" radio is rendered), SHALL display an allocation briefing
(total budget, six-axis count, each axis's 0–span, and the sum-must-equal-budget rule)
above the allocation fields, and SHALL provide a bounded optional background text field.
The form action buttons (confirm, reset, cancel, and concept-apply) SHALL be operable by
pointer through the shared focus/disabled/submission gate as well as by keyboard, and SHALL
pre-empt the keyboard bridge (a capture-phase listener) while the form owns focus, so keys
the form owns are claimed by the form and none reach the bridge's fall-through text path;
the capture listener SHALL be removed when the form closes. The final activation and the
destructive custom reset SHALL each require an explicit confirmation panel. Disabled entries
SHALL remain focusable with their explanation and SHALL submit nothing. Validation messages
SHALL be associated with the field they concern and announced through the accessible live
region. A stale revision SHALL preserve typed unsent values locally where safe, refresh
server-declared choices, and ask the player to review rather than automatically resubmitting.
No canonical service or creation state SHALL be stored in localStorage.

#### Scenario: Custom form completes without typed commands
- **WHEN** a player uses arrows and Tab/Shift+Tab to choose race and subrace, reviews the
  allocation briefing, types name, ages, allocations, and an optional background into the
  fields, confirms, and activates
- **THEN** the flow submits exactly `creation.custom` once with the expected payload
  (including the required subrace and any background), then `creation.activate` once, and
  the exploration snapshot follows

#### Scenario: The custom form cannot submit without a subrace
- **WHEN** a player leaves the subrace unselected in the custom form and confirms
- **THEN** the form reports the missing subrace against the subrace field and sends no
  `creation.custom` mutation

#### Scenario: The allocation briefing renders before the fields
- **WHEN** the custom form renders race and subrace with a resolvable profile
- **THEN** it displays the profile budget, the six-axis count, each axis's 0–span range,
  and the rule that the total must equal the budget above the allocation inputs

#### Scenario: Form action buttons respond to pointer clicks
- **WHEN** a player clicks the confirm, reset, cancel, or concept-apply button with the
  pointer
- **THEN** the button runs the identical action the keyboard Enter would run, obeying the
  shared disabled/in-flight/awaiting-revision gate, and no unclaimed keydown reaches the
  bridge's fall-through text path for clicks or for keys the form owns

#### Scenario: The form claims its keys without breaking native input
- **WHEN** a player types or presses Tab, modifier, or IME-composition keys while the
  custom form owns focus
- **THEN** native focus movement, text input, and Chinese IME continue to work (no
  `preventDefault` on those keys), the form's capture-phase pre-emption claims those keys
  (so no unclaimed keydown reaches the bridge), and a held or repeated Enter submits at most
  once

#### Scenario: A pointer click and a keyboard Enter cannot double-submit
- **WHEN** a player activates a form button by pointer while the same button also receives a
  keyboard-synthesized Enter
- **THEN** exactly one `creation.*` mutation is emitted per deliberate activation, with the
  in-flight / awaiting-revision gate and the pointer bridge's primary-single-activation
  check suppressing the duplicate

#### Scenario: Activation and reset require confirmation
- **WHEN** the player focuses activation or the custom reset but has not confirmed
- **THEN** no mutation is sent and Escape returns exactly one menu level without activating
  or clearing the draft
