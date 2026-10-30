## Purpose

Provide a server-authoritative whole-party camp decision with guarded dream consent and a skippable browser recovery presentation, without deriving game rules in the client.

## ADDED Requirements

### Requirement: Camp preview is read-only and authoritative

`explore.camp_preview` SHALL accept no input and return overall availability, default mode and each mode's availability, stable refusal code/message, dream eligibility and wake/reserve predictions for selected present members. It SHALL use camp's selection, safety and targets, with no persistence, clock advance or implicit initialization.

#### Scenario: Preview parity
- **WHEN** preview is followed by camp in an unchanged state with no intervening interruption
- **THEN** each predicted per-member wake and reserve matches the accepted targets and completed result; the browser computes neither wake nor recovery

#### Scenario: Existing sleepers and mode default
- **WHEN** a party includes an existing forced or voluntary sleeper and remote companions
- **THEN** preview preserves the existing sleeper's target, excludes remote members, and selects until-dawn at dusk/night or until-recovered otherwise

#### Scenario: Each refusal is reachable without writes
- **WHEN** combat, a hostile, an ineligible member or possession conflict prevents camp
- **THEN** preview returns the same stable gate code and zh-TW message as camp, with no attribute, receipt, dream, clock or reveal writes

#### Scenario: Mode-dependent eligibility
- **WHEN** the owner or whole party is already fully recovered
- **THEN** dawn can remain available while recovery is unavailable or cannot offer a dream; switching modes uses that mode's refusal and dream eligibility

#### Scenario: Piecewise member prediction
- **WHEN** a member starts awake/full or wakes before the latest selected sleeper
- **THEN** its reserve prediction includes canonical awake consumption through the camp endpoint, while its own wake target remains distinct

### Requirement: Camp commits consent and continues accepted party sleep

`explore.camp` SHALL accept exactly `{mode: "until-dawn" | "until-recovered", dream: boolean}`, atomically enter the selected party and record guarded enter or decline for a sleeping owner, then continue selected accepted plans or hand off to the dream. Refusal SHALL write nothing and return the preview gate code; true when unofferable SHALL reject without silently declining. Existing sleepers and remote members SHALL retain their plans.

#### Scenario: Unchecked camp
- **WHEN** a safe accepted camp has dream false
- **THEN** an existing owner sleeping receipt records explicit decline without a question and selected accepted sleeps continue through existing boundaries until all selected plans wake or a real safety/interaction interruption

#### Scenario: Recovered owner with tired companion
- **WHEN** recovery camp selects a fully recovered awake owner and an unrecovered companion
- **THEN** no owner receipt or answer is fabricated, no question appears, and the companion's accepted sleep continues to its wake or a real interruption with an idempotent camp result

#### Scenario: Checked camp
- **WHEN** dream true is accepted for the authenticated sleeping owner without companion possession
- **THEN** the existing dream stage opens at zero elapsed time and its existing departure rules own subsequent continuation

#### Scenario: Atomic refusal
- **WHEN** a member fails preflight, dream is ineligible, control/receipt revalidation fails or an entry/answer write raises
- **THEN** no requested posture, receipt, answer, dream or time write survives and no camp result publishes

#### Scenario: Invalid wire payload
- **WHEN** mode is unknown, dream is absent or nonboolean, or payload contains extra keys
- **THEN** the request rejects before any state write

### Requirement: Camp results describe committed recovery once

Accepted camping SHALL return actual elapsed time, member before/after reserves, actual wake/result time, due events and interruption state/reason, and publish one commit-qualified `camp_result` travel event. Dream entry SHALL return a pending zero-elapsed result; its final result SHALL derive from the same accepted sleep at departure. Replayed delivery SHALL never repeat settlement or the event.

#### Scenario: Completed or interrupted recovery
- **WHEN** a camp continuation completes or a real event interrupts it
- **THEN** its result contains only committed elapsed/recovery, each selected member's before/after reserve and actual wake if reached, current result time, all due events and truthful interruption reason; one camp_result carries the server summary

#### Scenario: Dream defers final result
- **WHEN** camp enters a dream and later departs or reconnects
- **THEN** the entry response marks recovery pending with zero elapsed, and final/interrupt publication occurs once for that accepted camp using only committed intervals

#### Scenario: Recovery across process loss
- **WHEN** recovery restarts between intervals with due events, after the final interval commit or before travel-event publication
- **THEN** durable progress restores the complete result/events and the same logical camp_result identity without replaying elapsed time; a safety pause reports interruption

### Requirement: Camp card selects only server-supplied choices

The browser SHALL open a focused, Tab-trapped camp card from the leg action or forced-walking-sleep handoff, select the preview default, reset dream unchecked on every opening and submit one camp action on confirmation. Unavailable previews SHALL expose only cancellation and the server reason while the opener stays enabled. Cancellation SHALL return focus to its opener without sending camp.

#### Scenario: Input and reopening
- **WHEN** the card opens with an available preview
- **THEN** keys 1/2 select the two supplied modes, D toggles only an offered dream checkbox, Enter confirms once, Esc cancels, and reopening resets the checkbox

#### Scenario: Projection and refusal
- **WHEN** a mode is selected or preview refuses
- **THEN** available state shows supplied current time, wake and member current/predicted reserve; refusal replaces choices with the reason and cancellation, with no confirm dispatch

#### Scenario: Selecting an unavailable mode
- **WHEN** one mode refuses but the other is available
- **THEN** the default remains server-selected, its refusal disables confirmation while the other tile stays reachable, and selecting an unofferable-dream mode clears the checkbox

#### Scenario: Forced sleep shortcut
- **WHEN** a walking member falls asleep and the existing handoff opens
- **THEN** its first option 全員紮營 opens this card while all other handoff operations retain their behavior

### Requirement: Campfire beat is presentation-only and skippable

A successful nondream result SHALL show an event-width campfire beat with party medallions, sleep marks and reserve bars transitioning from committed before to after over 1.6 seconds, then result/events and continuation. Any early key/click SHALL finish the beat without sending another action. Motion off SHALL show final state immediately; dream entry SHALL show the existing dream stage instead.

#### Scenario: Early finish and motion off
- **WHEN** a key/click arrives during animation, or motion is off
- **THEN** final bars and result/events become immediately available without clock, reserve or command effects; a subsequent Continue/Enter returns to the travel surface

#### Scenario: Interrupted outcome
- **WHEN** the server reports an interrupted camp
- **THEN** the beat shows its supplied reason and due events, makes no full-recovery claim, and returns to the authoritative actionable surface
