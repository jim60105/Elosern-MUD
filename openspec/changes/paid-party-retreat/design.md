# Design

## Context

request_party_exit/confirm_party_exit already bind commander/session/round/operation and snapshot round/clock/session writes. resolve_party_retreat uses _party_retreat_outcome, _escaped_party_retreat and _failed_party_retreat. Success currently marks all fled in place; failure already uses an empty allied provider. Predecessors supply real edges/history, journeys, paid combat-prefix cursors and arrival contact.

## Goals / Non-Goals

Complete one confirmed legal adjacent traversal with post-round affordability and no partial relocation. Preserve surrender, agility contest, carry-out, ordinary failure actions, exam FAIL and confirmation authority. No safe-destination bias, flee speed bonus or new carrying capacity model.

## Decisions

### Exact read-only post-attempt plan

Add `plan_party_retreat(commander: Any, record: CombatSessionRecord, battlefield: Battlefield, *, operation_id: str, preferred: PhysicalEdge | None) -> PartyRetreatPlan | None` to world_escape.py. Frozen `PartyRetreatPlan(edge: PhysicalEdge, member_ids: tuple[int,...], self_moving_ids: tuple[int,...], carried_ids: tuple[int,...], states_after_attempt: tuple[TravellerState,...], traversal: TraversalResolution, depart_tick: int, operation_id: str)` is the exact owner plan. None means legitimate blocked/unaffordable gameplay failure. Corrupt route/physiology raises by name.

Use the shared combat-activity projector from mapped-monster-escape and settled_rounds cursor from incapacitated-hostile-rounds. Project every unpaid completed interval plus the attempt's six-second round from actual posture evidence. Never use only persisted pre-battle reserve, omit prior deferred rounds or count a paid prefix again. Pass detached post-attempt states to canonical quote_edge/plan_traversal, including fatigue speed changes, exact-zero arrival and normal authorized waivers. Partial physiology is an operational refusal, never an ordinary agility-failure story.

Present allies are the commander's current source team, including existing knocked-out carry-out companions; remote companions neither price nor move. Existing eligibility selects agility actors. Actual self-moving members determine slowest speed and must afford the full route. Carried bodies retain normal condition and applicable physiology without fictitious walking/awakening. A non-knocked-out sleeper keeps ordinary sleep movement restrictions; the carry exemption is exactly the existing knocked-out rule. No unrelated restraint is bypassed.

### Confirmation and candidate selection

request_party_exit captures the validated reverse previous edge/source in the existing commander/session/revision/operation confirmation record; bind its fingerprint in the confirmation digest instead of trusting a client edge. Cancel retains draft/history/time. Execute revalidates current source, previous destination equality, reverse legality and affordability. An unavailable/unaffordable preferred route falls back to all lawful adjacent edges in stable locator/route order with existing operation-scoped deterministic selection. Do not inspect monster-free/safe status, birth buffers/zones or previous opponents. Missing history permits fallback; malformed saved history refuses by name.

Plan viability before rolling/reporting success. No acting ally retains the existing requested-retreat defeat/exam FAIL branch. No legal affordable neighbor runs _failed_party_retreat even with no pursuers. Otherwise retain the existing one-roll slowest-ally/fastest-pursuer contest. Insufficient reserve and no exit are ordinary failed attempts, never free preflight cancellations. One failure round executes normal enemy actions/upkeep, without traversal time/payment/partial movement, leaving a fresh draft if nonterminal.

### One atomic exit and paid edge

Extend the existing confirm_party_exit serialized outer transaction/publication group and _ExitSnapshots to include destination, full travel-window event-source surfaces, history, all present/carried body locations/coordinates, receipts and potential arrival session. Success marks the full party fled from the old roster and settles prior unpaid combat plus one attempt round once through settled_rounds. Old fled participants remain excluded from old encounter gauge regen; no exit heal or revival. Combat physiology pays its real intervals once.

Then execute the preflighted edge through normal movement settlement/discovery/following with an explicit rules-owned carry plan, unavailable to ordinary movement or clients. Paid traversal gets ordinary gauge/fatigue treatment and clock advancement once, using advance_bounded for long edges. Do not retain an unconditional old terminal charge alongside new billing. NPC arrivals never advance recursively.

During traversal the party is at neither idle endpoint for contact. At arrival record history, apply forced-depletion posture at exact zero and immediately evaluate actual occupants. A fresh encounter can include prior enemies that lawfully arrived first, with preserved resources and no immunity. Persist the old confirmation receipt under its closed-session scope; replay cannot mutate a new arrival session. Publish one final mode with no actionable exploration gap; auto-walking stops before another edge.

Guild-exam retreat still records FAIL, preserves opponent cleanup and host receipts, and uses a real lawful edge from the examination room without invented wilderness coordinates. Cleanup, travel and resulting arrival share the same operation.

### Failure and logging

Fault after old-session close, physiology, actual movement/following, arrival contact or receipt write restores the complete original party/session/draft/history, clock and population/journey state, including mutable Attributes/contents/idmapper caches. Re-raise operational errors; no reported success with relocation failure. Add catalog party_retreat_resolved with operation/session, source/destination, failure reason or success, attempt/arrival tick and member IDs; outer-commit only, using named facade imports and existing movement/clock/contact events.

## Risks / Trade-offs

Affordability includes the full unpaid combat prefix and attempt, and successful commit consumes exactly that prefix. The incapacitated-hostile-rounds settled-round cursor is authoritative; do not add another ledger. Confirmation replay stays bound to the old session even when arrival creates a new session.

## Verification

Register new `world.rules.tests.test_party_retreat_travel` in evennia-shards. Extend party exit/movement/exam/text/authoritative-browser tests for post-round insufficiency, affordable fallback, no edge/no pursuer, exact-zero arrival, gate changes after prompt, pooled recycling, teleport invalidation, possession, remote companions and carry-out. Failure pays one enemy round without movement. Success pays unpaid prefix + attempt + exact normal travel once, excludes old combat regen but permits normal travel physiology. Fault/reload/replay after each real writer restores or applies once. Follow a fled enemy and re-engage; retreat into aggression immediately admits a new whole-cell encounter.

Retain real disposable-world `tools/monster_field_behaviour_smoke.py::run`, invoked by `uv run --locked evennia shell --plain -c "from tools.monster_field_behaviour_smoke import run; run()"`. Synthetic registries use real owners without live LLM/network or mocking tested boundaries. Report group movement, live arrival contact, interrupted wait, failed energy admission, paid party retreat, actual enemy flee journey, re-engagement and committed reload. Both command docs and the developer document record actual results and human wording review.

## Implementation evidence contract

Canonical IDs copied from traceability list output for the equivalent merged tree:

- `player-combat-session::successful-retreat-carries-the-entire-present-party-and-counts-one-round`, tasks1.1/3.1/4.1, test_party_retreat_travel.
- `player-combat-session::retreat-contests-the-slowest-acting-ally-against-the-fastest-pursuer`, tasks1.1-2.1, route-admission and unchanged contest controls.
- `player-combat-session::failed-retreat-consumes-all-allied-actions-and-runs-one-ordinary-enemy-upkeep-round`, task2.1, failed energy/no-edge controls.
- `player-combat-session::party-exit-requires-a-commander-session-round-and-operation-bound-confirmation`, task2.1, confirmation/revalidation controls.
- `player-combat-session::combat-time-settles-once-at-terminal-session-outcome`, task3.1, paid-prefix plus traversal accounting.

## Blocking review disposition

The complete initial seven-change set received one blocking rubber-duck critique. All five blocking findings are addressed in these proposal revisions; no feature implementation or verification is claimed.

| Finding | Artifact remedy |
| --- | --- |
| Contradictory main timing/flee contracts | mapped-monster-escape now amends the whole agility requirement; incapacitated-hostile-rounds amends world-clock, party-time-settlement and field-combat-initiation as well as session/mental contracts; both session replacements bill/regenerate only the unpaid suffix |
| Lost composition identity | PopulationPlacement retains composition_key and activity_key through pure planning, stale comparison, actual group creation and forecast; identical-member/different-binding test required |
| Solitary validation used one runtime sample | authoring validates every possible count outcome and site override before publication; maximum total must be1 for solitary policy |
| Missing monster physiology handoff | explicit per-member durable cursors, actual rules projector/writer and disjoint idle/combat/journey intervals; two-deferred-round flee/arrival/idle/reload control required |
| No continuation after normal-round incapacity | separated continuation slice names the ordinary confirmed-round completion hook and reentrancy guard; end-to-end last-ally disabling test required |

Nonblocking type ambiguity is resolved by exact EscapePlan, committed journey-plan keys and detached ActivitySnapshot/zone/site shapes. Sizing feedback produced the eighth independently playable change, incapacitated-hostile-rounds, so contact authority no longer implements paid combat continuation. The remaining movement/journey/forecast slices reuse existing owners and one planner instead of adding parallel services; construction, commit and consumer integration stay together to avoid nonplayable scaffolds.

Requirement shape remains mechanism-based. Activity authoring adds one validation requirement; human ecology, visual quality and player wording stay in the named review document. Existing long agility prose is reduced to a short normative contest/admission sentence with every original scenario retained and the no-pursuer scenario amended. Entity/field inventories remain in design/tasks or scenarios. No requirement is justified solely by pinned shipped data or wording.

## Batch dependency and conflict matrix

| Change | Required active predecessor | Shared-code conflict |
| --- | --- | --- |
| movement-edge-history | none | movement/exits/travel pricing; mapped escape and retreat consume it |
| monster-activity-authoring | none | lore placement and candidate publication; serialize common metadata/docs |
| mapped-monster-escape | movement-edge-history; monster-activity-authoring | activity owner, population lifecycle, resolver/session journals |
| global-monster-activity | mapped-monster-escape | same activity/lifecycle owner, constructor integration and population tests |
| incapacitated-hostile-rounds | global-monster-activity | session cursor, fatigue/clock and ordinary combat continuation |
| hostile-field-admission | incapacitated-hostile-rounds | lifecycle ordering, movement arrival, combat/sleep/clock accounting |
| interruptible-field-contact | hostile-field-admission | lifecycle forecasts, mental time, skips and authoritative travel surfaces |
| paid-party-retreat | interruptible-field-contact | exit confirmation, session rounds/settlement, movement and contact publication |

Every row consumes current persistent identities and existing ownership rather than re-proposing them. Clock/lifecycle rows extend the one landed merged population event source; admission and retreat use the existing whole-cell roster. All rows serialize shard manifests, the developer review document and any command-doc edits. The two root changes have no behavior dependency on one another; the remaining chain has real data/authority prerequisites.

Create `/tmp/mud-field-tests.env` containing `MUD_TEST_SETTINGS=1` outside tracked source. Run one focused method/class at a time using the guarded command shown below; never concatenate the inventory or exceed 100 discovered tests. Register every new Python test module exactly once in `.github/evennia-shards.json`; new managed browser modules/methods belong exactly once in `.github/browser-shards.json`. Full managed-browser and complete traceability evidence remain CI-owned.

`uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb <named-label>`

Use canonical identifiers generated by `uv run --locked python -m tools.spec_traceability list`, never by concatenating names. For added/removed requirements, generate the equivalent merged specification tree outside Git and run the same tool with `--repo-root`; use its output before updating annotations. Preserve substantive assertion roles; delete retired claims without forwarding decorators, copy/data pin tests or waivers. Record requirement/scenario-to-test assertions and exercised evidence in `docs/development/monster-field-behaviour.md`. Human ecology/wording/visual judgment is reviewed there rather than asserted by shipped strings or counts.

At implementation handoff run focused tests, `uv run --locked python -m tools.observability_lint check` alongside changed-logging tests, the existing command-doc contract whenever command docs change, `openspec validate <change> --strict` and `uv run --locked python -m tools.contract_gate`. These are future worker checks, not feature verification during proposal creation. Failure restores every owning durable/live surface and emits no committed success. No compatibility readers, migrations, hidden initialization of an existing save or reset-on-load.
