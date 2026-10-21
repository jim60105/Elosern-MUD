# Spec Delta

## MODIFIED Requirements

### Requirement: explore.wait obeys the shared skip safety and clock API
The production action registry SHALL register `explore.wait`. Its payload SHALL accept exactly one of `daypart` (`midnight`, `dawn`, `noon`, `dusk`), `seconds` (a positive integer within the documented WebClient skip maximum), or `sleep` (the exact boolean true). The adapter SHALL recheck `evaluate_skip_safety(actor)` and invoke the same member-aware interruptible skip operation as text commands, preserving protocol bounds and actual elapsed receipts. Optional dream selection SHALL be honored only after real elapsed voluntary sleep; sleep entry SHALL first offer contextual handoff.

#### Scenario: Wait until dawn advances to the next occurrence
- **WHEN** a safe actor submits `explore.wait` with `daypart: "dawn"`
- **THEN** the clock advances only to the first relevant boundary within `seconds_until_daypart(calendar, "dawn")` with `AdvanceSource.SKIP` and the summary reports the elapsed duration

#### Scenario: An unsafe skip rejects before any clock advance
- **WHEN** an actor in a room with a living monster submits `explore.wait`
- **THEN** the adapter rejects with the matching safety reason, `get_world_clock().tick` is unchanged, and no event settles

#### Scenario: A custom duration is parsed server-side
- **WHEN** a safe actor submits `explore.wait` with `seconds: 3600`
- **THEN** the clock advances by up to 3600 actual seconds, stopping at the first relevant boundary with `AdvanceSource.SKIP`, and a value above the protocol bound is rejected before any advance

#### Scenario: The duration bound is protocol-only
- **WHEN** the `seconds` payload bound is documented
- **THEN** it is the documented WebClient skip maximum, a protocol-level bound that never changes command behavior

#### Scenario: Skip safety rejects combat and co-located monsters
- **WHEN** the adapter rechecks `evaluate_skip_safety(actor)` against current canonical state
- **THEN** active combat or a co-located living monster rejects

#### Scenario: The shared skip helper keeps command and WebClient computations identical
- **WHEN** the adapter computes the seconds to advance
- **THEN** it goes through the shared `world/rules` skip helper that `rest`/`sleep`/`wait` also consume, so `seconds_until_daypart` for a daypart, the bounded full-regen computation for `sleep`, and the submitted `seconds` as a request limit for a duration can never diverge between command and WebClient

#### Scenario: The wait summary is presented and one newer snapshot published
- **WHEN** the clock advance returns its `ScheduledEvent`
- **THEN** the adapter presents the summary through the escaped text path, does not advance time itself or let the browser choose an unsafe value, and publishes a full snapshot at one newer revision so the advanced header, status, shop hours, and quest deadlines refresh together

#### Scenario: An unsafe or malformed wait rejects without advancing the clock
- **WHEN** the location is unsafe, combat is active, the daypart is unknown, or the duration is out of bounds
- **THEN** the adapter rejects with a stable code and message and does not advance the clock

### Requirement: The waiting surface offers exactly three operations
The wait card, opened from the place card's 等待 button, SHALL offer exactly three time boundaries and no other: 等待直到黎明, submitting `explore.wait` with the `dawn` daypart; 睡眠至完全恢復, which submits `explore.wait` with the exact `sleep` flag, and offers handoff after zero-time posture entry, with optional dream collaboration only after an actual accepted elapsed sleep result; and 等待 N 小時, opening the bounded custom-duration form instead of dispatching.

#### Scenario: The waiting frame renders the three operations
- **WHEN** the player activates 等待 on the place card in exploration mode
- **THEN** the centred card renders 等待直到黎明, 睡眠至完全恢復, and 等待 N 小時 followed by `✕ 返回`, with no separate dream row and no midnight, noon, or dusk control, and the active row carries the active-row fill while the others do not

#### Scenario: The hours form dispatches whole seconds exactly once
- **WHEN** the player enters `1.5` hours in the 等待 form and confirms
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
- **WHEN** the player fills in the 等待 N 小時 form
- **THEN** it accepts hours with fractional input allowed, bounds the value to at least one second and at most the documented WebClient skip maximum (twelve hours), converts hours to whole seconds exactly once at the presentation boundary, and dispatches that value as the unchanged `explore.wait` `seconds` payload

#### Scenario: The form shows no resulting world time and reports bounds in Chinese
- **WHEN** the custom form is filled in, or its value is rejected or out of bounds
- **THEN** it does not derive or display a resulting world time, and a rejected or out-of-bounds value shows a Traditional Chinese bound message with no dispatch

#### Scenario: The surrounding skip vocabulary is unchanged
- **WHEN** the waiting surface is scoped
- **THEN** the server-side skip maximum is unchanged, and the four-daypart payload vocabulary stays valid for the text commands and authored suggestion rows that still use it

### Requirement: explore.practice books one declared skill for a member
The production action registry SHALL register `explore.practice` with a payload of exactly `actor_id` (a positive safe-integer party member id) and `skill` (a bounded non-space key of at most 64 characters). The adapter SHALL reauthorize the member for the acting purpose, reject an active combat session with `booking_in_combat`, preflight the skill against that member, and record the booking without advancing the clock; the next eligible positive-duration awake SKIP interval that settles the member grows the booked skill.

#### Scenario: Declared practice grows only the booked skill
- **WHEN** the commander books companion 艾拉's uncapped active `healing_light` through `explore.practice` and then waits 7200 seconds with 艾拉 present
- **THEN** the booking itself advances no time, the later SKIP advance grows only 艾拉's `healing_light` under the whole-hour settlement rule, and each action publishes a full snapshot at exactly one newer revision

#### Scenario: Unknown or capped practice skills advance nothing
- **WHEN** the submitted `skill` is unknown to the named member or already capped for that member
- **THEN** the result carries the stable code `PRACTICE_SKILL_UNKNOWN` or `PRACTICE_SKILL_CAPPED` with a Traditional Chinese message, the clock is unchanged, and the member's previous booking is unchanged

#### Scenario: An ambiguous practice payload rejects at the validator
- **WHEN** an `explore.practice` payload omits `actor_id` or `skill`, carries `seconds` or another extra field, or carries a non-integer `actor_id`
- **THEN** the dispatcher rejects it with outcome `rejected` and stable code `malformed_payload` without invoking the adapter

#### Scenario: Booking in combat is refused
- **WHEN** `explore.practice` arrives while the commander is in an active combat session
- **THEN** it is rejected with `booking_in_combat` and no booking changes

#### Scenario: A forged member is never replaced by the commander
- **WHEN** `explore.practice` names an NPC outside the party
- **THEN** it is rejected with `not_party_member` and the commander's booking is unchanged

#### Scenario: Rebooking replaces the member's booking
- **WHEN** a member with a standing booking for `healing_light` is booked for `mass_heal`
- **THEN** the member's single booking now names `mass_heal`

#### Scenario: The whole-hour settlement stage stays the sole practice writer
- **WHEN** a booking is recorded
- **THEN** the adapter writes only the member's booking; practice progression is written only by the clock's whole-hour practice settlement stage on a later eligible awake SKIP advance

#### Scenario: A failed advance rolls back clock and booking
- **WHEN** the later SKIP advance that settles a booking raises after settlement started
- **THEN** the clock growth and the booking are both restored, and no skill progression is applied

#### Scenario: Skip safety and skill preflight carry the stable rejection codes
- **WHEN** the booking preflight runs
- **THEN** an active combat session rejects with `booking_in_combat`, and an unknown or capped skill rejects with the stable codes `PRACTICE_SKILL_UNKNOWN` or `PRACTICE_SKILL_CAPPED`; skip safety applies later to the skip that settles the booking

#### Scenario: Ownership and cap are revalidated at commit time
- **WHEN** the booking action reaches its write, and again when the settling SKIP advance runs
- **THEN** skill ownership and cap are revalidated against current canonical state for the named member

#### Scenario: Rejections clear stale bookings and success publishes one newer snapshot
- **WHEN** the booking action finishes
- **THEN** rejection paths leave the member's previous booking unchanged, and success publishes a full snapshot at exactly one newer revision whose summary line names the member and the booked skill

