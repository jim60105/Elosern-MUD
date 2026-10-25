# Design

## Context

Observed first physical refresh slice owns narrow callbacks. Existing NPC move hooks currently clear only sessions naming the moving host; they do not refresh an unrelated conversation that depends on that NPC as a present companion. Quest-completion observers alone omit noncompletion lifecycle states.

## Goals / Non-Goals

**Goals:** Committed owner progression, companion presence, world-time and control refresh. Deliver this runnable slice and its acceptance within one engineer-day.

**Non-Goals:** Unowned runtime/content work, compatibility migrations, new game effects and per-line server stepping.

## Decisions

Shared contract v2 applies this matrix equally to static/generated sources. Existing transition_story_dialogue expected revision and committed escort/reunion provenance remain authoritative. Phase change/cancelled package/changed role binding retires context/delivery/receipts before projection/replay and suppresses obsolete notices. Stable host/topic reading persists. Generated-packages wires actual production phase/package invalidation through this same path.

The shared contract in ../authored-dialogue-contracts/design.md is authoritative. Add `world/rules/dialogue_availability.py::queue_dialogue_refresh(owners, *, cause)` only as a narrow deterministic dialogue callback helper, not a general event bus. The caller supplies canonical owner objects captured before destructive membership/control writes. It registers transaction.on_commit callbacks after successful writes; outside atomic it runs after the successful owning write. Callback re-resolves owner and its currently valid actor/host context before projection or push, never uses precommit eligibility. Rollback discards callbacks and no projection/reading mutation runs early. Multiple callbacks from one outer operation may run, but each re-evaluates the final committed state; observation is monotonic so only the first changed final projection creates a batch, encompassing all newly open topics. Do not promise notification correctness from WebClient observe_command_settlement: it skips non-WebSocket clients and remains a presentation refresh only.

Add `affected_dialogue_owners(entity, *, prior_owner=None)` for changed actors: persistent player -> itself, companion -> bound_owner_of and lawful current possession owner, plus explicitly supplied prior_owner captured before detach. Only legitimate owner identities are returned; no account-wide unrelated characters. For world-time changes, iterate persistent session-bearing PlayerCharacter/NPC rows via their dialogue_session Attribute key, re-resolve valid context and deduplicate owners. For companion presence, membership's owner is enough because CompanionPresent requires its own party membership; host departure additionally runs existing host-session cleanup. These helpers never create a conversation or rewrite a selected scene. Every pusher renders each authenticated watcher own context/epoch using commander_sessions plus resolve_commander filtering and current watchers_for registration.

This change is complete independently: change a synthetic condition through each named real writer, observe its current choices and rollback controls, without selecting a topic again. Reading/unread observation is attached later by unread-notices through the SAME refresh API. No module scan/research task is delegated to implementation; the following source matrix fixes hook placement. Existing gameplay writes/transactions and cache compensation remain their owners.

## Exact progression/lifecycle source-family matrix

| Condition source | Exact commit hook | Owner capture and publication | Acceptance |
|---|---|---|---|
| Guild registration/rank | world/rules/guild.py::register_adventurer after successful registration; guild_exams.py::settle_exam_outcome after passed rank assignment (existing register_exam_pass_observer may call same helper) | owner actor supplied explicitly, callback after outermost commit | registration and rank promotion independently open a topic; failed promotion produces no update |
| Quest all lifecycle states | world/quests/transitions.py::apply_quest_log_delta after final log replacement, plus existing _schedule_transition_events boundary for runtime accepted/abandoned transitions | quest actor owner helper | accepted/in-progress/completed/failed/invalidated and absence transitions refresh, not completion-only observer |
| Reward claimed | world/rules/guild.py::write_reward_claims after validated assignment inside caller transaction | owner actor | both counter and auto claim refresh exactly the named completed record after commit |
| Host affinity | world/rules/affinity.py::apply_affinity_change and seed_affinity after successful save; raise_affinity_cap alone does not change stage eligibility | explicit player argument, host is known | other-connection relationship write updates choices; failure/rollback never opens a topic |
| Companion membership | world/rules/party.py::_write_binding for join/leave/general/temporary mutations and purge_npc_memberships | capture player/prior owner before detach; callback resolves final membership | removal/reason expiry/auto-leave refreshes another-host conversation too |
| Companion presence and deletion | typeclasses/npcs.py::at_post_move and at_object_delete | bound_owner_of before purge and actor/host cleanup; capture source/destination and prior owner | unrelated bound companion leaving/returning changes CompanionPresent while conversation host stays present |
| World time | world/rules/clock.py::WorldClock.advance after tick persistence, inside its atomic | deduplicated owners of valid session-bearing bodies, independent of action scope | midnight/daypart boundary refresh reaches owner not participating in the initiating action |
| Phase | world/quests/story_dialogue.py phase refresh through existing world/rules/dialogue.py::refresh_dialogue_phase | current valid owner context | new phase retires old delivery/receipts before new projection |
| Control/release | world/rules/possession.py::enter_possession/release_possession after verified transition | explicit player captured before old body detaches | old actor context retires; new body's lawful current view republishes without copying obsolete scene |

For quest states, hook `_schedule_transition_events` because it observes the old/new record sets used by every committed lifecycle writer, while apply_quest_log_delta covers nested inventory/automatic settlement. Both may queue the same owner; final-state re-evaluation plus monotonic observation prevents duplicate first-unlock batches. Never use only register_quest_completion_observer, which misses accepted/failed/abandoned states. All typeclass hooks use on_commit as their existing host cleanup does; no immediate push from a membership transaction that can still roll back.

## Implementation handoff constraints

Each task is a 45-120 minute unit with its own focused tests/docs. This proposal is capped at one engineer-day and implements no gameplay arithmetic. Use an untracked .env.test containing MUD_TEST_SETTINGS=1 for future Evennia commands. Register new tests in .github/evennia-shards.json and run focused tests plus contract_gate at apply handoff. No tests, lint, builds or formatters run during proposal creation.


## Exact target files

- `world/rules/dialogue_availability.py`
- `world/rules/guild.py::register_adventurer/write_reward_claims`
- `world/rules/guild_exams.py::settle_exam_outcome`
- `world/quests/transitions.py::_schedule_transition_events/apply_quest_log_delta`
- `world/rules/affinity.py::apply_affinity_change/seed_affinity`
- `world/rules/party.py::_write_binding/purge_npc_memberships`
- `typeclasses/npcs.py::at_post_move/at_object_delete`
- `world/rules/clock.py::WorldClock.advance`
- `world/quests/story_dialogue.py`
- `world/rules/possession.py`

This slice reuses `queue_dialogue_refresh` and `affected_dialogue_owners` exactly as `authored-dialogue-refresh-physical` defines them; it adds the world-time and control capture paths and its own source-family rows, and it never redefines or duplicates those two helpers.

## Risks / Trade-offs

Follows physical callback helper and touches lifecycle writers only. Notification observation depends on this slice so no first-unlock source is missed. Shared source conflicts with possession/reading are already ordered by upstream availability dependencies. Keep authored source validation separate from runtime eligibility. A failed post-commit push recovers on the next canonical sync, without reversing a successful owning commit. Read the approved design and dependency artifacts before edits; no interface decision is left open.

## Focused verification at implementation time

```text
uv run --locked --env-file=.env.test evennia test --settings test_settings.py --keepdb world.rules.tests.test_dialogue_refresh_lifecycle
uv run --locked python -m tools.contract_gate
```

Run only focused test labels/methods within the repository time limits. Full managed browser and evidence suites remain CI-owned. These commands are planned acceptance, not results from proposal creation.
