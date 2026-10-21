# Party Fatigue, Sleep, and Control Design

Date: 2026-10-21
Status: Approved; OpenSpec proposals created (§16); not implemented.
Companion design: [World Map Scale](2026-10-21-world-map-scale-design.md).

## 1. Outcome and architectural authority

Model sustained activity separately from immediate SP. Each player character and effective party companion owns an independent mental reserve. Its fatigue consequences use the existing debuff system. Players may accept worsening penalties to travel longer; extreme depletion causes forced sleep rather than an arbitrary daily mileage quota.

Keep the player-driven clock and deterministic single-writer boundary from `2026-07-29-ai-mud-engine-design.md`. With no accepted time-bearing action, no game time passes and no reserve changes. The rules core owns reserve, sleep, debuff projection and action eligibility. Presentation and AI never write these states.

This design amends sleep duration and skip semantics where they currently derive only from HP/MP/SP or treat all SKIP participants alike. It deliberately preserves terminal-only combat time settlement. Main OpenSpec capabilities remain the implemented contract until their owning changes land.

## 2. Scope, approved simplifications, and exclusions

Included are independent reserve state, staged fatigue debuffs, activity rates, voluntary and forced sleep, existing waiting operations, control handoff after incapacitation, stationary party policy, battle targeting and terminal fatigue settlement, and all-forced-sleep engagement defeat.

No vehicles, fast travel, carrying sleepers, split-party exploration, full food/water/encumbrance simulation, or new party-capacity limit is added. No independent quiet-rest action, stance, button, or special regeneration category is added. No active-monster encounter system is introduced; current lack of active monsters does not justify leaving the engagement edge undefined.

Forced-waking abilities and mental-restoration items are non-goals. The representation must allow a future explicit state-changing effect without freezing sleep eligibility for an entire battle.

The following earlier brainstorming proposals were expressly superseded and must not appear in implementation:

- Per-round natural fatigue consumption or sleep recovery.
- Natural threshold-based awakening while a battle is in progress.
- Advancing the world clock every combat round.
- All-sleeping combat observation until someone wakes.
- A special extension or replacement of the ordinary combat round cap to support sleeping spectators.
- A quiet-rest rate of minus one percentage point per hour.

## 3. Existing contracts that constrain the change

`world/rules/clock.py` settles world time and restores transactional surfaces. `world/rules/movement_settlement.py` owns movement compensation. `world/rules/time_skip.py`, `commands/skip.py`, and the exploration wait adapter currently route sleep/wait through `AdvanceSource.SKIP`. Existing sleep duration comes from the slowest HP/MP/SP time-to-full and can be zero for full gauges. None of those facts identifies which individual member is actually asleep.

The existing party-time contract settles co-located companions with the commander during relevant advances, including when controlling a possessed companion. It does not imply that co-located members share an activity or all sleep together.

`world/rules/possession.py` currently refuses entry during combat and maintains one mirrored possession with verified session transfer. `world/rules/combat_session/` permits commander-selected companion commands without changing possession, excludes action-forbidden allies from required commands, and advances accumulated combat time once at terminal settlement. Sleep must remain distinct from the persisted knockout/defeat sets.

The existing sleep/dream flow commits accepted sleep once before optional dream collaboration. Forced sleep must not open a dream automatically or block deterministic play behind a generative service.

## 4. State and numerical representation

### 4.1 Mental reserve

Use the player-facing term 精神儲備. Its range is 0 through 100 percent, inclusive; a higher value means more capacity to remain active. It is independent of HP, MP and SP. Spending or restoring SP does not implicitly spend or restore mental reserve.

Store reserve persistently on each owning entity, not as an ordinary Python instance attribute or an account-wide party gauge. Use integer reserve units with 3,600 units per percentage point:

- Empty reserve: 0 units.
- Full reserve: 360,000 units.
- Forced-sleep wake threshold: 72,000 units, representing 20 percent.

The approved hourly rates then become exact integer unit deltas per game second. No per-action fractional loss is dropped, and splitting an interval into multiple advances produces the same result when activity and boundary events are unchanged. Display may round percentages; eligibility always reads the stored exact value.

Newly constructed ordinary entities start with full reserve and awake posture. Existing authored character construction/synchronization must explicitly establish this baseline through the owning deterministic path; do not treat arbitrary malformed reserve as an excuse to refill a fatigued character. Validate type and bounds before writes.

### 4.2 Sleep posture

Persist each member's posture as awake, voluntarily sleeping, or forcibly sleeping. Posture records only a real condition; there is no persistent quiet-rest posture. Sleeping is separate from HP-based knockout, death, paralysis, or defeat.

Forced sleep latches when reserve reaches zero at an accepted settlement boundary. Reaching one unit above zero does not wake the member. Natural forced-sleep release occurs at 20 percent or higher, outside live combat, and leaves the member with the fatigue stage associated with that reserve.

A voluntary sleep operation explicitly names the body entering sleep, defaulting to the current acting body. Co-location, ownership or one shared clock advance never selects the other members for sleep. Controlling a companion, selecting sleep for that body, and returning to an awake owner is valid. Do not add a separate party sleep-planner feature.

## 5. Fatigue debuff projection

| Exact reserve interval | State | Foot-travel multiplier | Combat modifier |
| --- | --- | --- | --- |
| 70 to 100 percent | Normal | 1.00 | None from fatigue |
| At least 40, below 70 percent | 輕度疲勞 | 0.90 | Agility -5%; accuracy adjustment -5 |
| At least 20, below 40 percent | 中度疲勞 | 0.75 | Agility -10%; accuracy adjustment -10 |
| Above zero, below 20 percent | 重度疲勞 | 0.50 | Agility -20%; accuracy adjustment -20 |
| Forced sleep remains latched below its wake threshold | 強制睡眠 | Travel forbidden | Actions forbidden; still targetable |

Accuracy adjustments are flat values in the existing combat-modifier convention, not percentage multipliers. Travel multipliers apply to foot speed; the agility modifier does not multiply movement again. A party moves at the slowest travelling member's effective speed.

Fatigue stages are mutually exclusive. The forced-sleep projection replaces the ordinary fatigue stage while that posture remains active; after waking at 20 percent the member receives moderate fatigue. Do not stack light, moderate and severe penalties or rewrite stored base stats.

Declare harmful/critical status presentation through the existing buff and status-display registries. The persisted reserve and sleep posture are authoritative; debuffs project that state and do not expire independently just because their nominal duration elapsed. Reconcile them atomically whenever reserve or posture changes.

General-purpose cleanse must not erase physiological fatigue or its cause. Explicit future reserve/sleep effects may change the authoritative state; no such ability is implemented here. This requires the owning change to integrate protected physiological status with the existing cleanse eligibility policy, not a UI-only exemption.

## 6. Activity rates and ordinary resource behavior

| Member activity over the settled interval | Net reserve change per hour | Exact units per second |
| --- | --- | --- |
| Ordinary awake activity or awake waiting | -4 percentage points | -4 |
| Foot travel | -8 percentage points | -8 |
| Awake combat participation, settled only at terminal outcome | -12 percentage points | -12 |
| Actual sleep, voluntary or forced | +12 percentage points | +12 |

These are net rates, including the cost of staying awake. Do not add the ordinary awake rate again to travel or combat. No quiet-rest rate exists. A member who remains awake during waiting uses the ordinary awake rate.

Do not add a terrain exertion multiplier in this change. Terrain already lengthens travel time, increasing total reserve cost. A later separately designed exertion policy may distinguish equal-duration activities; this design does not invent it.

Short-term SP retains its existing action costs and natural regeneration rules. This design introduces no unapproved numeric walking SP drain, hunger rate, thirst rate, or carrying formula. The long-term reserve cannot be refilled by an ordinary SP restoration, so SP regeneration during travel does not erase sustained fatigue.

An awake member with a practice booking uses ordinary awake reserve consumption during the actual study interval in this initial calibration. A sleeping member cannot earn practice for the same interval. Preserve that sleeping member's booking without consuming it; process it only on a later eligible awake study interval. This deliberately changes the current assumption that every co-located booking is consumed by any SKIP.

## 7. Calibration and travel consequences

A full-reserve human walking six hours loses 48 percentage points, ending at 52 percent. Ten further hours of ordinary awake activity cost 40 points, leaving 12 percent before bed. Eight hours of sleep supply 96 points, clamped to 100. This schedule can sustain repeated travel days.

Six healthy road hours have an unreduced baseline of 27 km at 4.5 km/h. Fatigue crosses 70 percent after 3.75 walking hours, so the same six-hour continuous walk under these rates covers 25.9875 km: 16.875 km at full speed and 9.1125 km at the light-fatigue speed. Travel estimates must use the changing speed rather than promise 27 km every day.

Continuous foot travel from full reserve reaches zero after 12.5 hours if no other activity intervenes. Fatigue reduces useful distance before that point. This is a reserve consequence, not a daily cap; midnight does not reset the measure. The companion map design defines admission for a sparse road that would exhaust a member before its next node.

Forced sleep from zero reaches the 20-percent wake threshold after 6,000 game seconds, or 100 minutes. Waking at that threshold leaves moderate fatigue and is not equivalent to full recovery. Voluntary sleep may continue to a higher recovery target.

## 8. Player-driven time and waiting

### 8.1 No passive wall-clock simulation

Only an accepted time-bearing action advances the world. Looking at menus, reading status, choosing a control target, disconnecting, or doing nothing advances neither time nor reserve. Existing free operations such as inventory inspection do not acquire invented time costs.

All actual player-driven noncombat advances must settle the present co-located party's mental time even when a narrower existing resource effect concerns only one member. This mental-time scope must not silently widen unrelated HP/MP/SP, rite, quest or practice effects. Ordinary NPC populations are not globally scanned or simulated for this feature.

For combat, use the existing terminal participant policy and the battle activity accounting in section 10. Dead/deleted actors do not receive physiological revival from reserve settlement.

### 8.2 Existing waiting surface

Use the existing waiting entry for a custom duration or an existing daypart boundary. Relabel the current custom-duration presentation consistently as waiting instead of adding a quiet-rest choice beside sleep. Text duration waits and browser duration waits must reach the same rules operation; update both command documents and their contracts when the surface changes. Do not keep a second quiet-rest command with a different mental rate.

The existing `rest`/duration mechanism is a time-skip transport, not proof of an implemented quiet-rest activity state. Its non-sleeping, non-practice time uses awake waiting semantics. Preserve existing practice capabilities and unrelated resource behavior through the shared deterministic path.

Waiting advances time for a purpose while the selected body stays awake. It supplies no special reserve recovery or invented guard/ambush bonus. Sleep is correctly the better choice when the player's objective is mental recovery; waiting is useful when the player wants to remain awake while a companion sleeps or a world deadline approaches.

### 8.3 Per-member settlement

Resolve a transient activity classification for every settled member. Sleeping members recover; awake members consume at their own actual activity rate. `AdvanceSource.SKIP` alone cannot distinguish sleep, wait, or practice and cannot mark the whole party asleep.

For a 600-second wait, a forced-sleeping member at zero reaches 2 percent and remains asleep. An awake companion starting at 60 percent reaches approximately 59.3333 percent. The interval is shared, while posture and reserve are independent.

### 8.4 Event boundaries

Noncombat waits and sleep operations advance only to the earliest relevant boundary within the requested interval: an involved member falling into forced sleep, a sleeping member naturally reaching its wake target, or an actual registered event requiring interaction such as an encounter. Commit only the elapsed portion, publish the event, and discard the unperformed remainder. A retry cannot replay an already committed interval.

Preserve the existing safe-skip gate. Waiting cannot bypass an active combat session or a present hostile. A forced-sleep transition can occur in unsafe circumstances without pretending the member voluntarily passed a safe-sleep gate; that transition does not grant a time skip or protection. A later valid engagement applies section 10.

Existing current lack of active monsters remains unchanged. Do not add a random ambush roll to make waiting appear useful.

When a wait wakes a companion or changes the controlled body's capability, stop and return control before automatically consuming further time. Fatigue-stage changes that do not require interaction can update within the same requested interval; they are not an excuse to drop fractional consumption.

### 8.5 Indivisible nonmovement actions

Existing indivisible actions such as a field cast retain their full accepted effects, resource costs and time cost as one atomic unit. Sample each settled member's actual activity/posture for that interval, apply its reserve delta for the full interval, and enter forced sleep at completion if the result reaches zero. Do not retrospectively turn the remainder into sleeping time or grant recovery. This is settlement granularity, rather than a claim that all physiology is simulated continuously inside an indivisible action.

An actor already unable to act fails ordinary preflight with zero effects/time. An eligible actor with little reserve may complete an accepted indivisible action and then collapse. The same completion rule applies when an unselected awake companion reaches zero during that action's shared time; it does not erase the caster's effects or shorten the paid interval. Emit prompts only after the complete transaction commits.

Interruptible waits, sleep and their eligible study intervals use section 8.4 instead. Movement uses the separately declared sparse-edge admission rule in the map design. A new long-duration activity must explicitly define its interruption/completion policy rather than inheriting indivisible semantics to bypass sleep for arbitrarily long work.

## 9. Sleep, control handoff, and stationary party policy

### 9.1 Voluntary sleep completion

The existing voluntary sleep-to-full calculation must include mental reserve alongside the existing HP/MP/SP recovery requirement, subject to the existing maximum skip bound and actual interruption. Full ordinary gauges must no longer produce zero-duration sleep while mental reserve still needs recovery.

A forced-sleeping body naturally targets the minimum 20-percent wake threshold. Sleep is settled once. Later optional dream collaboration uses the committed result without restoring resources or advancing time a second time. Forced sleep never opens a dream automatically.

Sleep entry and elapsed sleep are separate boundaries. Commit the selected body's sleeping posture without advancing time, then, when an awake eligible body exists, offer the handoff choice before advancing the requested sleep interval. The player may transfer and perform awake activities while that body remains asleep, or explicitly continue the existing sleep-to-recovery operation. Without an awake candidate, use the non-acting recovery surface in section 9.3. Closing the choice advances no time and does not falsely report a completed sleep.

This ordering preserves the path of putting a possessed companion to sleep and returning to the awake owner. It does not add a party sleep planner. Dream collaboration can be offered only after a real accepted elapsed sleep result, never merely from committing sleep entry.

### 9.2 Current body falls asleep

After a successful committed transition makes the currently controlled body unable to act through sleep, offer control transfer to an awake, living, action-capable, co-located eligible party member. If controlling a companion while the owner is awake, returning to that owner is also a valid choice. Another companion can be selected through a full verified transfer rather than creating nested possession.

The prompt lists actual candidates with their current fatigue state and whether the operation returns to the owner or possesses a companion. Do not automatically possess the first candidate. Selecting or inspecting candidates costs no game time. Revalidate membership, presence, sleep, living/action state, and session identity when confirming; a stale candidate is rejected without changing control.

This is a contextual handoff prompt, not a new general unrestricted combat-possession feature. When the controlled body becomes unavailable, the deterministic core retains the authenticated account's authority to inspect status and choose a valid handoff or wait. It does not authorize that sleeping body to cast, move, or use an item.

Existing single-possession mirrors, account scope, puppet locks, cmdsets and rollback/restore rules remain binding. Change the current combat gate only for the explicit sleep-driven handoff needed to retain a valid control target; do not waive party membership or allow remote possession. Selection and cancel leave the commander identity and combat draft untouched. A technical transfer failure leaves the old binding truthful and offers retry/status rather than claiming success.

An unselected member falling asleep produces a status notification without stealing the current selection or opening a mandatory transfer prompt. A sleeping body waking does not automatically pull control away from the companion the player selected.

### 9.3 No awake candidate outside combat

Retain a non-acting waiting/status surface for the authenticated player. Offer explicit waiting for recovery; no realtime background advance occurs. A safe advance stops when the first eligible member wakes, then offers the ordinary handoff choice. If a hostile is already present, do not bypass the skip-safety gate; resolve the valid engagement path, including immediate all-forced-sleep defeat.

This is outside-combat waiting. There is no all-sleeping combat observation mode.

### 9.4 Stationary party

If any present party member is in forced sleep, refuse all party travel, including settlement exits, wilderness steps and cross-layer gates. Possessing an awake member does not make sleeping bodies follow, teleport them, carry them, or permit that member to split off. Party members may interact, organize items, or fight at the current location through existing lawful operations.

A travel refusal at this gate advances no time or reserve and moves no entity. The player can voluntarily sleep before reaching zero. Leaving a sleeper behind, carrying them and remote recovery simulation are excluded.

## 10. Simplified combat integration

### 10.1 Opening roster and targetability

Include present sleeping members in the battlefield as living participants when otherwise eligible under existing roster/living rules. Do not exclude them as knocked out solely because they sleep. Existing HP-based knockout exclusions remain unchanged.

Sleep forbids actions, not targeting. It removes the member from required allied command collection and execution eligibility, without silently selecting an automatic attack. Enemies may still target the sleeper under normal targeting and damage rules. The monster AI observes the actual inability-to-act restriction and does not infer death, absence, invulnerability, or an automatic win from sleep.

A sleeping commander remains the party owner; an awake companion's commanded action still uses that companion's skills and costs. The handoff feature changes the controlled body where appropriate, not quest ownership or the session owner.

### 10.2 No natural in-battle reserve updates

During a live combat session, neither reserve nor its fatigue debuff changes merely because another round is completed. The world clock still advances once at terminal outcome, using completed rounds times the existing six-second round duration. Do not add a cast-time charge for an in-session skill.

A member asleep on entry remains asleep throughout the battle unless a future explicit effect changes that state. No per-round natural wake deadline is scheduled or polled. This is absence of natural wake simulation, not an immutable sleep lock.

The existing ordinary round cap and ordinary no-eligible-actor behavior remain in place except for the explicit opening condition below. No special thousand-round spectator loop is added.

### 10.3 Terminal fatigue settlement

At terminal settlement, apply each eligible participant's reserve change once for its actual accumulated combat interval, then project fatigue and natural sleep release. Preserve the existing terminal idempotency marker and atomic round/settlement unit; reconnect or retry cannot charge or restore the same combat time twice.

For a member continuously awake over ten completed rounds, 60 seconds costs 0.2 percentage points. A continuously sleeping member gains 0.2 points at terminal settlement only. No recovery occurs merely while the player spends wall-clock time selecting commands.

Sleep posture and defeat remain distinct. Mental recovery cannot revive a dead entity, remove an already established defeat, or undo existing aftermath. An undefeated sleeper reaching 20 percent at terminal settlement wakes into moderate fatigue. A still-below-threshold sleeper stays asleep after victory, keeping the party stationary.

To avoid blocking a future explicit waking effect, retain the initial sleep posture and any explicit posture transition at a round boundary in the session's activity accounting. Derive awake/sleep durations at terminal settlement from those intervals and `rounds_elapsed`; recording a posture transition does not itself tick fatigue. Do not give the entire battle's sleep recovery to a member explicitly awakened partway through it. No new waking effect or item is authored now.

For an undefeated awake participant entering at 0.1 percent, ten completed rounds still leave that reserve unchanged during live combat. Terminal consumption is 0.2 points, clamped to zero, and forced sleep begins only at that terminal boundary. Do not simulate an earlier collapse and retroactively restore reserve for the remaining combat seconds.

If a sleep transition follows terminal fatigue settlement, emit any handoff prompt only after the final transaction commits and after defeat/aftermath has established the real surviving state. No prompt may target a companion who has just been removed or defeated by the same terminal operation.

### 10.4 Entire party in forced sleep when combat begins

After canonical participant validation, if every present allied party participant is forcibly sleeping, enter the existing defeat settlement immediately. Do not wait for a command, run an enemy round, simulate sleep recovery to a threshold, or invent one elapsed combat round.

Use a zero-round session through the ordinary deterministic terminal writer so existing defeat aftermath, persistence and diagnostics run once. Time inherently advanced by that existing aftermath remains applicable; only invented combat time is forbidden. Preserve exam-mode outcome policy rather than invoking ordinary hostile aftermath for an examination.

This rule is tested through a direct valid engagement boundary even though active-monster encounters are not currently implemented. It does not add proactive hostiles.

### 10.5 Failure and lifecycle boundaries

A sleep or fatigue write failure rolls back the complete terminal unit, including traits, buffs, reserve, posture, session metadata, clock and touched caches. Existing knockout/defeat bookkeeping must not be repurposed as a sleep flag.

Disconnect pauses the session with no reserve/time change; reconnect restores its sleeping participants and draft without running a round. Existing forced-sleep debuffs remain visible on reconnect. Deletion, dismissal and account lifecycle continue through existing verified possession cleanup; the new prompt does not create an alternative writer.

## 11. Component boundaries

The implementation should have small deterministic interfaces with these responsibilities:

| Responsibility | Input | Output/ownership |
| --- | --- | --- |
| Fatigue policy | Exact reserve, sleep posture, declared activity and game seconds | Pure interval effects, next boundaries, fatigue stage and travel modifier; authored constants have one read-only source |
| Fatigue settlement | Validated entities and interval effects | Atomic reserve/posture/debuff writes through the rules core |
| Time-skip orchestration | Explicit sleep or waiting request, authoritative party scope and safety | One actual elapsed interval, member-specific activities, interruptions and existing clock events |
| Movement integration | Sparse road geometry, party restrictions, changing fatigue speed | Validated cost and one atomic movement settlement; no sleeping follower movement |
| Control handoff | Account/commander, current unavailable body, selected live candidate | Existing verified possession/return transition with transactional compensation |
| Combat integration | Roster/posture, completed rounds, terminal outcome | Normal action prohibition and targetability; one terminal reserve settlement or immediate opening defeat |
| Presentation | Read-only status and handoff eligibility | Localized labels, candidate choices, rejection reasons and ordinary wait/sleep results |

Reserve policy does not own transport sessions or battlefield persistence. Possession does not own fatigue arithmetic. The clock remains the only world-time writer. Avoid a second debuff table or independent UI eligibility implementation.

## 12. Persistence, errors, and observability

Every new persistent surface must join the relevant clock, movement and terminal rollback snapshots. A failed multi-member settlement restores all members, including in-process Evennia caches. A committed forced-sleep transition and its projected debuff must never disagree after reload.

Use the existing observability facade and boundary-event conventions. Include available character, commander, room, tick, session and reason identifiers in context. Emit real state transitions and control-transfer outcomes after durable commit, not per-second noise or fake successful handoffs. Do not log credentials or expand unrelated observability scope.

Use stable error reasons for a sleeping actor, sleeping party travel block, stale/ineligible handoff candidate, and unsafe wait. Preserve existing relevant reasons when they already express the refusal. Technical exceptions must not become an ordinary fatigue penalty or silently refill reserve.

A malformed reserve or posture fails before action writes. An unavailable or stale candidate returns current choices without transferring to a substitute. Browser and text entry points use the same authoritative rules; a browser modal is never the sole enforcement point.

## 13. Presentation contract

Use the existing status/debuff surface for fatigue stages and forced sleep. Show the member identity and reserve percentage using display rounding that does not change exact thresholds. Convey inability to act with text as well as existing severity styling.

The handoff prompt is shown only when the current body becomes unable to act through sleep. It offers eligible awake candidates, a return-to-owner choice when lawful, and waiting/status when there is no candidate or the player declines. Cancel costs no time and never grants a sleeping body normal actions. Keyboard focus and stale-response handling must follow the existing modal/selection conventions; no independent visual redesign is in scope.

Keep sleeping members visible in combat with an explicit sleeping/action-unavailable label. Do not hide them, assign a command, or show a defeated appearance solely from fatigue. Existing HP/defeat presentation remains separate.

The waiting surface offers the existing duration/daypart use cases with consistent terminology. No quiet-rest sibling action or recovery promise appears beside sleep. Forced sleep never auto-opens optional dream collaboration.

## 14. Behavior acceptance and focused verification

Permanent tests must establish behavior and consumer boundaries, not copy registry rows as a second balance table. Use synthetic members and independently known outcomes. Register any added or moved test module in the owning shard manifest. Update command docs and their contract if duration-wait or sleep command semantics change.

Required scenarios include:

1. Two co-located members with different postures settle the same explicit wait at different rates, without changing who is sleeping.
2. Looking at status, cancelling handoff, or doing nothing advances no time/reserve.
3. Exact threshold boundaries select one fatigue stage; forced sleep persists above zero until 20 percent; state reload reproduces the same action gates and debuffs.
4. Split and unsplit intervals produce the same reserve under the same activities, including fractional percentage values and saturation at full reserve.
5. Full HP/MP/SP with incomplete mental reserve still gives a nonzero voluntary sleep requirement; forced sleep stops at the minimum wake boundary without claiming full recovery.
6. A sleeping member's practice booking is preserved and earns nothing for sleeping time; a different awake studying member can settle its own booking.
7. Every party exit refuses with zero time/location changes while a present member is forcibly sleeping, including while controlling an awake companion.
8. A current-body sleep transition offers only valid co-located awake candidates, preserves owner identity, and revalidates a stale selection. Inject a transfer failure and prove the verified binding/session/cmdsets restore.
9. An unselected companion sleeping does not steal control; a body waking does not automatically repuppet the owner.
10. Waiting stops at the first relevant forced-sleep/wake/registered-event boundary and commits no requested remainder. Existing unsafe-wait rejection remains effective.
11. Sleeping allies are present, targetable, observed as unable to act by monster AI, and absent from required commands. Sleeping alone does not populate knockout IDs or end the session.
12. A nonterminal combat round changes neither mental reserve nor the world clock. Ten completed rounds settle 60 seconds once at terminal outcome; a retry/reconnect cannot settle again.
13. A near-threshold sleeper remains asleep throughout live rounds. An undefeated sleeper reaching the threshold wakes during terminal settlement. Sleep recovery never revives an already defeated entity.
14. All-forced-sleep engagement immediately uses the ordinary defeat path with zero invented combat rounds and no observation mode. A repeated terminal attempt adds no second aftermath.
15. The existing combat round cap and unrelated HP/MP/SP settlement remain unchanged. No per-round fatigue or extended spectator loop survives from the rejected proposal.
16. A fault after reserve/debuff or later terminal writes restores clock, every touched member, activity/session metadata and cached state together.
17. An indivisible field action with a nearly depleted actor completes its accepted effects, full costs and full elapsed time once, then enters forced sleep. Repeat with only an unselected companion nearly depleted and prove the caster's completed action is not truncated.
18. Putting a possessed companion to sleep commits entry without elapsed time and offers return to an awake owner before recovery; later owner actions recover the sleeping companion without marking the owner asleep.
19. An awake combatant at 0.1 percent stays unchanged during live rounds, then reaches zero and forced sleep after ten rounds settle once, with no retrospective sleeping recovery or pre-commit handoff.

Implementation smoke evidence must exercise real wait/sleep commands and a real party battle/control boundary, including reload. Verify the actual browser handoff/status surface and a text path without a live LLM. The current documentation work does not claim those runtime changes are implemented.

## 15. Delivery and alternatives

The user selected SP plus a separate long-term reserve over SP-only fatigue or a full survival simulator. SP-only consumption could be erased by ordinary gauge regeneration; a food/water/load simulator would exceed the requested scope.

The user selected stationary recovery over carrying sleepers or splitting the party. The user then replaced natural in-battle recovery with terminal-only settlement because the 100-minute minimum sleep would require approximately 1,000 six-second rounds from empty reserve. The final battle model preserves existing timing and avoids that complexity.

Record the two designs as shared context, then obtain written-spec approval before invoking `writing-plans`. Implementation must subsequently follow the repository's OpenSpec workflow and amend affected capabilities together, including party authority, possession, sleep/wait, debuff/cleanse, movement, and combat contracts. No gameplay implementation, migration, new item, or skill is authorized merely by committing these design documents.

## 16. Proposed changes

This design is decomposed into six dependency-ordered OpenSpec changes. Each is sized to about one workday, was validated with `openspec validate <change> --strict`, and records the exact branch and worktree its implementation worker must use. All are committed on the primary branch; none is implemented.

| Change | Commit | Scope | Tasks |
| --- | --- | --- | ---: |
| `establish-mental-reserve-core` | `a52ec2a5` | Mental reserve core, exact units and the pure prediction API | 10 |
| `project-physiological-fatigue` | `8566ac40` | Staged debuff projection, cleanse protection and sleep action prohibition | 11 |
| `settle-party-sleep-and-wait` | `5ea32830` | Per-member sleep settlement, bounded waits, indivisible actions and stationary party | 15 |
| `handoff-sleeping-party-control` | `b2b72fd4` | Sleep-driven possession handoff with browser and text parity | 11 |
| `integrate-sleeping-combat-rosters` | `8829a80a` | Sleeping members present, targetable and observed as unable to act | 11 |
| `settle-terminal-combat-fatigue` | `85b5f725` | Terminal one-shot fatigue settlement and zero-round all-forced-sleep defeat | 11 |

The implementation worker is **luna** for every change, using `feat/<change-slug>` on branch and `.worktrees/<change-slug>` as worktree.

### 16.1 Cross-batch contract with the map design

`integrate-fatigue-aware-traversal` in the companion batch carries `depends-on: external:party-fatigue-and-sleep`. The integration step replaces that token with **`settle-terminal-combat-fatigue`**, which transitively requires every change in this batch. Replacing the token with any single earlier component would let traversal integrate against a partial physiology contract; the whole batch must be treated as one scheduling barrier. Re-run `openspec validate --all --strict` after the replacement.

## 17. Parallel implementation order

Wave numbers below are the shared numbers from the combined eight-wave order in the companion design, so this batch occupies waves 1, 2, 3 and 5 and shares wave 3 with the map batch. Changes sharing declared code conflicts serialize even inside a wave.

| Wave | Changes | Workers | Basis |
| --- | --- | ---: | --- |
| 1 | `establish-mental-reserve-core` | 1 | No prerequisites; new reserve module and entity state are isolated from map work |
| 2 | `project-physiological-fatigue` | 1 | Needs wave 1 reserve; buff, status-query and party-scope surfaces serialize with later consumers |
| 3 | `settle-party-sleep-and-wait`, `integrate-sleeping-combat-rosters` | 2 | Sleep needs wave 2 projection plus the map batch's `charge-distance-based-travel`; rosters need only wave 2, so they run beside sleep on disjoint surfaces |
| 4 | `handoff-sleeping-party-control` | 1 | Declares conflicts with the sleep adapters and combat authority landed in wave 3 |
| 5 | `settle-terminal-combat-fatigue` | 1 | Needs wave 3 rosters and wave 4 post-commit handoff routing |

Wave 3 is the batch's only parallelism. Everything after it serializes: handoff depends on both wave 3 changes, and terminal settlement closes the physiology contract that `integrate-fatigue-aware-traversal` then consumes.
