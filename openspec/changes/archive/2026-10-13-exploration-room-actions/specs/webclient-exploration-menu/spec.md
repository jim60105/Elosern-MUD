## MODIFIED Requirements

### Requirement: The waiting surface offers exactly three operations
The wait card, opened from the place card's 等待 button, SHALL offer exactly three time boundaries and no other: 等待直到黎明, submitting `explore.wait` with the `dawn` daypart; 睡眠至完全恢復, which first asks 進入夢境協作？ and then submits `explore.wait` with the exact `sleep` flag, plus the `dream` flag when the player answers 是; and 休息 N 小時, opening the bounded custom-duration form instead of dispatching.

#### Scenario: The waiting frame renders the three operations
- **WHEN** the player activates 等待 on the place card in exploration mode
- **THEN** the centred card renders 等待直到黎明, 睡眠至完全恢復, and 休息 N 小時 followed by `✕ 返回`, with no separate dream row and no midnight, noon, or dusk control, and the active row carries the active-row fill while the others do not

#### Scenario: The hours form dispatches whole seconds exactly once
- **WHEN** the player enters `1.5` hours in the 休息 form and confirms
- **THEN** exactly one `ui_action` is submitted — `explore.wait` with `seconds: 5400` — the form closes, and no resulting world time is displayed before the server snapshot arrives

#### Scenario: An out-of-bounds hours value errors without dispatching
- **WHEN** the player enters `12.01` hours (or clears the field) and confirms
- **THEN** the form shows the bounded Traditional Chinese message, emits no `ui_action`, and stays open for correction

#### Scenario: Locked controls cannot start a skip
- **WHEN** an action is in flight or the client awaits its declared presentation revision
- **THEN** every wait row is disabled and Enter or pointer activation on them submits nothing

#### Scenario: The frame shows three cards plus a back row with focused treatment
- **WHEN** the wait card renders
- **THEN** it shows exactly those operations plus the trailing `✕ 返回` row, and the row that `aria-activedescendant` names carries the active-row fill

#### Scenario: The custom hours form bounds, converts, and dispatches once
- **WHEN** the player fills in the 休息 N 小時 form
- **THEN** it accepts hours with fractional input allowed, bounds the value to at least one second and at most the documented WebClient skip maximum (twelve hours), converts hours to whole seconds exactly once at the presentation boundary, and dispatches that value as the unchanged `explore.wait` `seconds` payload

#### Scenario: The form shows no resulting world time and reports bounds in Chinese
- **WHEN** the custom form is filled in, or its value is rejected or out of bounds
- **THEN** it does not derive or display a resulting world time, and a rejected or out-of-bounds value shows a Traditional Chinese bound message with no dispatch

#### Scenario: The surrounding skip vocabulary is unchanged
- **WHEN** the waiting surface is scoped
- **THEN** the server-side skip maximum is unchanged, and the four-daypart payload vocabulary stays valid for the text commands and authored suggestion rows that still use it
