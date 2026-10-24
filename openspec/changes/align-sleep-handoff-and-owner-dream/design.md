# Design

## Context

`use-room-actions.js` asks about dreams before dispatching sleep; `onDreamAnswer` sends sleep and dream together. The wait store tears down its card immediately. `_wait_adapter` and `CmdSleep` early-return on narrative handoff, dropping dream intent. `dream_surface.owner_id` uses `actor.pk`; `enter_after_sleep` demands positive elapsed voluntary recovery, which permits NPC ownership and makes an asleep-owner prompt impossible. `release_possession` changes verified bindings without physiology, which is correct and must remain so.

Prerequisites establish durable body-owned sleep receipts and all-sleep travel admission. Reuse existing possession confirmation, modal/selection focus behavior, dream lifecycle, draft/confirm and offline escape. The approved original design and `dream-sleep-surface` recovery-before-dream rules are explicitly superseded here, not preserved as compatibility paths.

## Goals / Non-Goals

**Goals:** one server-owned operation/control view routes sleep, verified handoff, owner-only dream and deterministic continuation; every branch remains recoverable offline and after reconnect.

**Non-Goals:** new modal styling, unrestricted possession, dream generation redesign, new posture enum, random encounters, carrying or live-save repair. This is a bounded consumer integration after the two deterministic prerequisites.

## Decisions

### Authoritative view projection and precedence

Derive `owner` from the authenticated account/session and canonical commander resolution, never `session.puppet.pk` alone. Revalidate that this owner owns the sleep receipt. Read verified possession mirrors and actual session binding. The owner is sleeping when its actual posture is either voluntary or forced with a valid accepted receipt. An eligible dream view requires owner still asleep and no companion possession. Companion sleep status is not a global dream gate.

After a committed controlled-body sleep transition, publish a structured contextual selection descriptor automatically; the browser opens it without Party Drawer navigation. Include every canonical effective companion in roster order, including remote/sleeping/unavailable entries with current reserve/fatigue and one stable disabled reason. Existing visibility/ownership rules remain binding; no unbound or stale NPC IDs are leaked as companions. Show an awake-owner return row when lawful. Each enabled row explicitly says possess companion or return owner. The final companion-list option is exactly `全員一起睡眠`; cancel/back is modal chrome outside that list. No row activation or cancel adds time.

When that same no-possession view qualifies for a dream question, expose the owner-specific question in the contextual surface's decision area outside the companion list. Use a single modal focus owner. Choosing possession revalidates and invalidates the unanswered dream offer without entering a dream. Choosing remain/recovery or cancelling companion selection advances no time and presents the ordinary dream yes/no step before any recovery. This serial presentation preserves the automatic complete companion popup and the owner-sleep/no-possession question without stacking focus traps. Every newly entered qualifying view issues the question; an unchanged revision/reconnect resumes the existing answer state instead of opening duplicate questions.

Explicit release onto a sleeping owner projects the dream decision even when other companions remain awake. If the owner is awake, return ordinary play with no dream question. Passive owner wake only updates status while companion possession remains selected. A sleeping owner never gains normal actions merely because bindings clear.

### Server contract and transport parity

The structured view carries owner ID, controlled-body ID, sleep ID/revision, presentation epoch/base revision, current candidate rows, dream eligibility and pending decision. Browser actions use existing action envelope IDs plus exact candidate or sleep identity. Server confirmation rederives authenticated session, current possession, membership, co-location, living/action/sleep state and receipt revision. Stale/died/moved/dismissed choices reject without time/control writes and return the current descriptor. Never substitute another candidate or automatically select the first available body.

Use existing verified puppet/session/lock/cmdset transition for owner return, owner-to-companion and companion-to-companion handoff. The all-party choice invokes the prerequisite's party entry and, if needed, verified release as one outer compensated operation. Validate release feasibility and party entry before writes. Failure after posture, receipt or control writes restores all selected members, projections, possession mirrors, locks, cmdsets, session bindings and locations. Commit no time during this choice; project the resulting owner view after commit.

Text receives the same roster/reasons and decisions. Existing possess/unpossess syntax remains, including lawful explicit release from a sleeping controlled companion. Mount authenticated nonacting control/status/sleep continuation/dream commands in the sleeping/released view without granting normal action capability. Replace `sleep dream` with ordinary accepted sleep followed by new `dream enter` on the qualifying view; the current bare `dream` command only renders state and must explicitly gain pending-question rendering. Add `dream decline` as the negative answer equivalent to closing/declining the browser question. Existing say/draft/confirm/awaken syntax remains for an associated session. `sleep continue` declines a pending question and continues the same accepted target. Update `commands/dream.py`, sleep/release command entry points and both command documents in the same apply change.

Browser sleep configuration retains three wait-root operations. Its sleep flow offers recovery/default or bounded duration using existing duration form conventions. `explore.wait` carries the prerequisite's declared sleep payload. Dream answers are separate actions bound to the accepted sleep ID/revision; remove the old dream-before-sleep question, combined `dream` sleep flag, and narrative-only adapter early return. Keep the action/revision lock until the authoritative outcome arrives; render the contextual descriptor, not a speculative resulting time.

### Single owner receipt lifecycle

The prerequisite's receipt is the sole physiology episode. Add bounded owner-view decision state to that receipt or its existing owner-owned operation Attribute, and associate dream session with `owner_id`, `sleep_id` and revision. The narrative owner may write its own dream session, but it cannot wake bodies, replace sleep targets or tick the clock.

| Transition | Durable result | Time/restoration |
| --- | --- | --- |
| Accept sleep | Body posture plus receipt, question pending if owner/no possession | Zero |
| Confirm companion | Verified possession; owner's receipt persists | Zero |
| Explicit release | No possession; sleeping owner question pending or awake ordinary view | Zero |
| Dream yes | Revalidate owner asleep/no possession; link existing/new owner dream session to same receipt | Zero |
| Question decline/close | Record declined for this control-view decision; choose continuation or refreshed handoff | No independent charge |
| Exchange | Existing bounded exchange state | Zero |
| Confirm/draft/awaken/offline exit | Close/draft narrative session, set same sleep continuation intent | Clock commits only remaining accepted sleep |
| Wake target reached | Reconcile owner awake, complete receipt, clear sleeping-view intent | No second sleep |
| Reconnect | Restore canonical view, receipt cursor and existing narrative progress | Zero wall-clock change |

Dream entry may occur at zero accepted elapsed time while the owner truly sleeps. This is an accepted posture episode, never fabricated completed sleep. A fully recovered default recovery request immediately reconciles awake and has no dream question; positive duration permits a real sleeping view even at full gauges. Forced sleep creates its existing minimum-threshold plan through the prerequisite and may ask for explicit opt-in in a safe released view; it never auto-enters a dream or bypasses combat/hostile restrictions.

All exits, including failed generation, draft, confirm and `awaken`, route once to the same deterministic continuation seam. Departure itself adds no independent time or restoration. Continuation advances only the remaining owner interval; it can finish sleep or return a real interaction interruption. If the owner has already awakened through another accepted advance, reconcile that completed receipt, close/resume narrative state as appropriate and return ordinary play without a new recovery. A response confirming a now-stale dream offer rejects with the current awake/possessed view.

Idempotency uses stable sleep and interval identities plus revisions, not positive elapsed as proof. Commit dream answer/association and continuation intent under owner lock; retries reuse the durable result and progress. A failure between narrative departure and clock continuation leaves the receipt continuation intent pending, so reconnect resumes it once. Fault within an interval rolls that interval and its cursor/result back together. Preserve completed earlier intervals. Cancellation of an unconfirmed handoff or dream prompt changes no posture and has no time cost of its own. Never wake the owner in unpossess.

### Owner-targeted automatic continuation and interruptions

When every operable present body is asleep, no companion is possessed and the dream question is declined or dismissed, accept one durable owner-targeted continuation intent automatically. Operable means the owner plus present living effective physiological members otherwise capable of action if awake; dead/defeated/incapable bodies cannot serve as substitutes. Do not include remote bodies as possible controllers. At intent creation, require actual owner sleep and a valid accepted target.

Use owner duration deadline or declared recovery target/remaining bound, never the earliest companion wake as the terminal goal. Execute the existing clock in boundary-sized intervals. At each physiology boundary commit once, update all bodies and re-evaluate the next boundary; a companion waking earlier neither interrupts nor steals control. Its subsequent time uses awake consumption/practice rules. This authorization remains valid after that early wake, so an all-asleep precondition is checked at start, not re-required for every interval.

Stop automatic continuation at owner wake/accepted cap, a real registered interactive event, changed control intent from a concurrent authenticated request, or existing unsafe combat/hostile condition. No random event is invented. Ordinary waits still stop and discard their remainder at first wake; this retained owner continuation is an explicit exception to the old discard/first-awake wording. No per-second loop is needed, and each committed interval must either advance a positive number of seconds or finalize a due zero-offset transition; repeated zero-offset wake/depletion cannot loop forever.

At a real interaction, preserve the committed prefix and remaining sleep plan, mark continuation paused and publish the event. Expose status, legal awake-member handoff, and `sleep continue`/browser resume after event resolution. If the event requires an awake actor, use lawful handoff after the user chooses; do not grant the sleeping owner ordinary actions. If no awake actor exists, retain existing hostile/combat/defeat handling and its deterministic exits. Safety refusal never silently skips. Once the real interaction resolves, one resume action continues the remaining owner target across intermediate wakes, rather than requiring repeated wait clicks.

When the player declines with an awake operable companion already available, show refreshed handoff/status and explicit same-sleep continuation; no automatic fast-forward is mandated. Dream departure's explicit awaken/confirm/draft is itself authorization to finish the same owner sleep even if companions are awake. Browser question close is a server-visible decline bound to the current decision; disconnect alone is neither decline nor automatic time. Reconnect restores unanswered questions, resumes a previously committed continuation intent once, or exposes an interaction-paused state. It never re-enters a new sleep or charges wall time.

### Consumer ownership

| Owner | Owns | Must not do |
| --- | --- | --- |
| time_skip / clock / mental settlement | Sleep receipt, target/cursor, interval settlement and passive wakes | Derive player identity from possessed NPC or generate dreams |
| possession rules | Verified transfer/release and compensation | Wake owner or tick sleep |
| dream_surface / narrative lifecycle | Owner-bound session, exchanges, association and departure intent | Manufacture elapsed receipt or restore resources |
| server facade and command/action adapters | Authenticate, validate revision, invoke shared operation, publish current view | Run separate sleep or client eligibility rules |
| Browser store/composables | Existing modal focus, complete rows, locks and explicit answers | Choose first companion, pre-ask dream or authorize normal sleeping actions |

## Approved Design Amendments

During apply amend fatigue/sleep design §3/§9.1 to replace settle-before-dream and positive-elapsed prerequisites with accepted owner sleep plus no possession before recovery. Amend §9.3/§8.4/§14 to replace no-awake/manual-first-wake recovery for dream-decline with owner-targeted automatic continuation and the explicit interaction exception. Amend §13 to require all companions visible with availability and automatic contextual opening. Keep forced opt-in, offline play, combat restrictions and zero-time selection invariants. This proposal touches no design file outside its own directory. Main `dream-sleep-surface` Purpose can be updated when syncing implementation to remove its stale after-settlement wording; no separate compatibility requirement survives.

## Acceptance Sequences and Verification Boundaries

Use synthetic bodies and independently known times. Cover owner sleep -> popup -> possess -> local action; cancel at the same tick; all-party choice; controlled companion sleep -> owner return/next companion; early and late explicit release; asleep owner with awake companions receiving dream question; passive owner wake without repuppet. Cover all asleep -> decline/close -> owner wake, with companion waking earlier and consuming awake reserve before owner deadline; exact-duration saturation and slowest-gauge recovery; real interactive event and hostile/combat interruptions.

Cover dream yes -> exchange -> confirm/draft/awaken/offline failure with one receipt and no duplicate interval; owner wake or changed possession before confirmation; reconnect before/during/after entry, handoff, dream and recovery. Inject faults after posture, clock and control writes and check persisted/cache/session/projection/receipt restoration. Replace premature-question wiring assertions and manual-Party-Drawer browser journeys with real behavior. The travel prerequisite supplies the full actual consumer matrix, not merely `foot_speed_scale` assertions.

## Risks / Trade-offs

- Prompt/control race -> owner/session/receipt revision checked inside the existing compensated boundary.
- Multiple visible decisions -> one modal focus owner and server-owned pending question; selection and dream cannot dispatch concurrently.
- Partial narrative departure -> durable same-receipt continuation intent and interval replay guards.
- Unsafe/nonacting recovery -> publish the real interruption plus legal control/recovery actions; retain ordinary engagement/defeat policy.

## Deployment and Rollback

Apply with **gpt-luna**, branch `feat/align-sleep-handoff-and-owner-dream`, worktree `.worktrees/align-sleep-handoff-and-owner-dream`, after both dependencies land. Cut over all callers, including server facade and text commands; remove obsolete combined-sleep/dream entry and old positive-elapsed checks. No migrations, shims or live-save repair. Roll back as one consumer contract unit if needed. No full local CI/browser evidence run is authorized.
