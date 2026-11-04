# Design

## Context

Current settle_forced_sleep_opening declares hostile zero-round defeat, _continue_or_settle returns a normal paused result when no ally can act, and _settle_terminal_fatigue settles allied posture only at termination. Persistent identity, whole-cell rosters and historical population protection are already landed. Global activity and mapped escape provide explicit monster physiology cursors and the shared read-only combat projector.

## Goals / Non-Goals

Change only playable existing hostile combat continuation and its exact accounting. Proactive field admission and forecasting are later consumers. Keep voluntary initiation/movement sleep gates, ordinary interactive deferred time, the six-second round and cap100, designated exam FAIL and requested-retreat no-acting-ally defeat.

## Decisions

### Durable paid interval contract

Add strict serialized `settled_rounds: int` to CombatSessionRecord and every builder/fixture, requiring 0 <= settled_rounds <= rounds_elapsed. Ordinary interactive rounds remain deferred. Before automatic continuation, pay all unpaid completed rounds once; each subsequent automatic round pays exactly six seconds through settle_combat_result. The clock/mental/gauge settlement interval is [started_tick+settled_rounds*6, started_tick+rounds_elapsed*6). Advance the cursor only with the paid interval's durable commit. Terminal settlement pays only this remaining unpaid suffix, including gauge regeneration and actual posture intervals; lifetime total remains rounds_elapsed*6. Preserve all round evidence needed for attribution and historical protection. Do not introduce another world-time ledger.

Mapped monster participants use the preceding rules settle_monster_combat_through writer and per-member map-owned cursor at the same paid endpoint. Generic clock/gauge sources exclude intervals already settled by that owner; allied mental accounting uses the session cursor. Fled monsters already in journeys are never charged old combat again. Dead/deleted/defeated bodies receive no revival.

### Real automatic rounds and required invocation hooks

Expose `continue_incapacitated_hostile_rounds(commander: Any) -> dict[str,Any]` in combat_session/rounds.py. Run only for a valid nonterminal hostile encounter with get_required_combat_actors empty. Use normal run_round with an empty allied provider, enemy deterministic policy/initiative/ActionResolver/upkeep and _finalize_resolved_round. Stop immediately when an ally can act, on ordinary terminal result or cap. No synthetic allied action and no defeat caused solely by sleep.

Invoke from two writer paths. First, hostile canonical engagement replaces settle_forced_sleep_opening with continuation after session creation. Second, after every successfully confirmed ordinary round, _finalize_resolved_round/_continue_or_settle returns to the owning round orchestrator; that orchestrator re-reads current eligibility and invokes continuation before final publication if it lost the last actionable ally. This includes ordinary engage/cast-opened encounters. Implement a writer-local reentrancy guard so each automatic iteration finalizes once without recursively invoking the outer continuation hook. A finalizer returns a continuation-needed disposition; the outer serialized writer consumes it after the round savepoint, never a view/edit/reconnect read. Requested retreat's explicit no-acting-ally terminal branch remains separate.

Never advance recursively from a clock event source. Future hostile field admission returns an interactive event/session; its rules owner calls continuation after the accepted WorldClock.advance has returned and persisted its endpoint, inside the same outer durable/publication operation. Already engaged parties cannot admit another session during prefix settlement.

### Threshold and receipts

Extend canonical fatigue interval context with `allow_hostile_round_wake: bool = False`. Only actual paid hostile enemy-only rounds set it for forced sleepers. Preserve the existing72000 threshold, receipt identity and observer callbacks. Keep ordinary live interactive fatigue deferred and voluntary sleep gates intact. A waking companion ends automatic play under existing control authority even if commander sleeps. Retain exam-only forced-opening FAIL helper under a narrow name and migrate guild_exams callers; do not run ordinary hostile aftermath for exam admission.

### Atomicity, documentation and logging

Round effects, unpaid-prefix clock/physiology, settled_rounds, session/draft, skip-safety, historical protection and mutable Evennia caches share the existing outer round/admission transaction. Rollback restores all surfaces; replay never resolves or pays a prefix twice. Publish final actionable/terminal mode once. Add committed `combat_incapacitated_continued` catalog event with session/revision/settled-round range and member IDs through named world.observability imports; reuse actual round/clock events. Update both docs/game/commands.md and docs/game/command-reference.md and developer human-review/evidence document.

## Risks / Trade-offs

This separate slice reduces hostile-field-admission to contact authority and hooks. It must amend all terminal-only contracts together, which are player-combat-session, mental-reserve, world-clock CmdCast scenarios, party-time-settlement wake policy and field-combat-initiation opening-time scenarios. Terminal remainder means unpaid seconds, never accumulated seconds already paid.

## Verification

Register world.rules.tests.test_hostile_incapacitated_rounds once in evennia-shards. Real forced reserve71928 receives one normal enemy attack/upkeep and paid six seconds to72000 before player choices resume. An end-to-end normally confirmed round applies a real temporary blocking effect to the final actionable ally and the normal orchestrator automatically continues until eligibility or terminal state. Verify awake companion, defeat/cap, unpaid prefix, terminal remainder, restart replay and late fatigue/cursor/session failure. Tests must exercise actual entry/round consumer paths, not only call the helper directly. Existing exam FAIL and voluntary sleep rejection remain.

## Generated canonical evidence anchors

These literal identifiers come from `uv run --locked python -m tools.spec_traceability --repo-root /tmp/mud-field-proposed-specs list --json-output /tmp/mud-field-proposed-ids.json` after the review corrections were merged into the scratch specification tree. Each scenario is implemented by its corresponding actual writer/consumer assertion, never a duplicate decorator without evidence.

- `player-combat-session::incapacitated-hostile-parties-receive-normal-enemy-rounds`, tasks1.1-3.1, test_hostile_incapacitated_rounds plus the substantive existing clock/party/opening tests.
- `player-combat-session::combat-time-settles-once-at-terminal-session-outcome`, tasks1.1-3.1, test_hostile_incapacitated_rounds plus the substantive existing clock/party/opening tests.
- `player-combat-session::no-eligible-actors-leaves-command-collection-paused-with-explicit-party-exits`, tasks1.1-3.1, test_hostile_incapacitated_rounds plus the substantive existing clock/party/opening tests.
- `player-combat-session::live-rounds-do-not-simulate-natural-fatigue-or-awakening`, tasks1.1-3.1, test_hostile_incapacitated_rounds plus the substantive existing clock/party/opening tests.
- `player-combat-session::terminal-mental-accounting-records-actual-round-boundary-posture-intervals`, tasks1.1-3.1, test_hostile_incapacitated_rounds plus the substantive existing clock/party/opening tests.
- `player-combat-session::terminal-physiology-cannot-reverse-defeat-and-prompts-follow-aftermath`, tasks1.1-3.1, test_hostile_incapacitated_rounds plus the substantive existing clock/party/opening tests.
- `mental-reserve::posture-and-forced-sleep-hysteresis-are-body-scoped`, tasks1.1-3.1, test_hostile_incapacitated_rounds plus the substantive existing clock/party/opening tests.
- `world-clock::cmdcast-advances-command-time-only-outside-a-persistent-combat-session`, tasks1.1-3.1, test_hostile_incapacitated_rounds plus the substantive existing clock/party/opening tests.
- `party-time-settlement::every-settled-sleeper-completes-its-own-accepted-wake-plan`, tasks1.1-3.1, test_hostile_incapacitated_rounds plus the substantive existing clock/party/opening tests.
- `field-combat-initiation::the-opening-cast-charges-combat-time-never-command-time`, tasks1.1-3.1, test_hostile_incapacitated_rounds plus the substantive existing clock/party/opening tests.

Retire `player-combat-session::all-forced-sleep-engagement-enters-ordinary-zero-round-defeat`, obtained from the current-tree list output. Replace hostile sleep-only defeat assertions with actual enemy-round/threshold assertions while retaining examination FAIL controls.

## Implementation evidence contract

Create `/tmp/mud-field-tests.env` containing `MUD_TEST_SETTINGS=1` outside tracked source. Run one focused method/class at a time using the guarded command shown below; never concatenate the inventory or exceed 100 discovered tests. Register every new Python test module exactly once in `.github/evennia-shards.json`; new managed browser modules/methods belong exactly once in `.github/browser-shards.json`. Full managed-browser and complete traceability evidence remain CI-owned.

`uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb <named-label>`

Use canonical identifiers generated by `uv run --locked python -m tools.spec_traceability list`, never by concatenating names. For added/removed requirements, generate the equivalent merged specification tree outside Git and run the same tool with `--repo-root`; use its output before updating annotations. Preserve substantive assertion roles; delete retired claims without forwarding decorators, copy/data pin tests or waivers. Record requirement/scenario-to-test assertions and exercised evidence in `docs/development/monster-field-behaviour.md`. Human ecology/wording/visual judgment is reviewed there rather than asserted by shipped strings or counts.

At implementation handoff run focused tests, `uv run --locked python -m tools.observability_lint check` alongside changed-logging tests, the existing command-doc contract whenever command docs change, `openspec validate <change> --strict` and `uv run --locked python -m tools.contract_gate`. These are future worker checks, not feature verification during proposal creation. Failure restores every owning durable/live surface and emits no committed success. No compatibility readers, migrations, hidden initialization of an existing save or reset-on-load.
