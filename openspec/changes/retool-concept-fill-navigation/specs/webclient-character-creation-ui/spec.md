## MODIFIED Requirements

### Requirement: The creation dock is keyboard-first, form-capable, and confirmation-protected
In `creation` mode the action dock SHALL present preset cards and the custom form rather
than exploration or service menus. Arrow keys SHALL navigate finite lists and buttons, Tab
and Shift+Tab SHALL move focus through text/numeric fields, Enter SHALL activate the
focused control or submit a complete server-declared form, and Escape SHALL pop exactly one
menu level without discarding the saved server wizard draft. The custom form SHALL require a
subrace selection (no "無子種族" radio is rendered), SHALL display an allocation briefing
(total budget, seven-axis count, each axis's 0–span, and the sum-must-equal-budget rule)
above the allocation fields, and SHALL provide a bounded optional background text field. The
form action buttons (confirm, reset, cancel, and concept-apply) SHALL be operable by
pointer through the shared focus/disabled/submission gate as well as by keyboard, and SHALL
pre-empt the keyboard bridge (a capture-phase listener) while the form owns focus, so keys
the form owns are claimed by the form and none reach the bridge's fall-through text path;
the capture listener SHALL be removed when the form closes. While a concept apply is in
flight the concept tab SHALL present a prominent in-progress state — a visible large
spinner with an explicit waiting message — and SHALL disable the concept input and the
concept-apply button until a fresh proposal revision is applied or a result carrying the
submitted request id with a non-success outcome settles the request; through the whole
in-flight window no store publish or draft re-sync SHALL move the presented tab — the tab
is pinned while the loading state is alive. The browser SHALL present no other completion
affordance for a settled apply beyond the custom-tab switch (the confirmation/failure
toast is surfaced by the action-feedback slice, not the form). The final activation and the
destructive custom reset SHALL each require an explicit confirmation panel. Disabled entries
SHALL remain focusable with their explanation and SHALL submit nothing. Validation messages
SHALL be associated with the field they concern and announced through the accessible live
region. A stale revision SHALL preserve typed unsent values locally where safe, refresh
server-declared choices, and ask the player to review rather than automatically resubmitting.
A committed `creation` panel that carries no draft and only a transient proposal SHALL NOT
reset the creation dock's stage — the panel signature covers presets, races, and the draft
only, so a proposal delivery alone never navigates the player.
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
- **THEN** it displays the profile budget, the seven-axis count, each axis's 0–span range,
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

#### Scenario: An in-flight concept apply shows a prominent waiting state
- **WHEN** a player submits a concept and the generative layer has not yet settled
- **THEN** the concept tab shows a large spinner with an explicit waiting message, the
  concept input and apply button are disabled so no second concept is submitted, and the
  waiting state clears exactly when a fresh proposal is applied or a non-success result
  bearing the submitted request id settles the request

#### Scenario: The concept tab stays pinned through in-flight republishes
- **WHEN** a concept apply is in flight and the store commits panel updates or draft
  re-syncs whose stage signal would otherwise mirror onto the presented tab
- **THEN** the presented tab remains the concept tab for the whole in-flight window, and
  the waiting state clears without ever being replaced by the preset tab

#### Scenario: A proposal-only panel refresh never navigates the dock
- **WHEN** a concept apply completes and the store commits a `creation` panel with no draft
  and a `proposal` slot
- **THEN** the creation dock's stage is unchanged (the player is not moved to the preset
  stage), and any tab movement comes solely from the overlay's own completion navigation
