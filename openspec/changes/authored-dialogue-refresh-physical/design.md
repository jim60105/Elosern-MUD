# Design

## Context

Review found WebClient-only command settlement cannot cover Telnet, another connection or no-session deterministic writes. Observed canonical inventory/equipment, XP and cross-lineage ownership writers provide bounded direct commit hooks; generic presenter refresh cannot replace them.

## Goals / Non-Goals

**Goals:** Committed physical-condition refresh from canonical item, equipment, identity and skill writers. Deliver this runnable slice and its acceptance within one engineer-day.

**Non-Goals:** Unowned runtime/content work, compatibility migrations, new game effects and per-line server stepping.

## Decisions

The shared contract in ../authored-dialogue-contracts/design.md is authoritative. Add `world/rules/dialogue_availability.py::queue_dialogue_refresh(owners, *, cause)` only as a narrow deterministic dialogue callback helper, not a general event bus. The caller supplies canonical owner objects captured before destructive membership/control writes. It registers transaction.on_commit callbacks after successful writes; outside atomic it runs after the successful owning write. Callback re-resolves owner and its currently valid actor/host context before projection or push, never uses precommit eligibility. Rollback discards callbacks and no projection/reading mutation runs early. Multiple callbacks from one outer operation may run, but each re-evaluates the final committed state; observation is monotonic so only the first changed final projection creates a batch, encompassing all newly open topics. Do not promise notification correctness from WebClient observe_command_settlement: it skips non-WebSocket clients and remains a presentation refresh only.

Add `affected_dialogue_owners(entity, *, prior_owner=None)` for changed actors: persistent player -> itself, companion -> bound_owner_of and lawful current possession owner, plus explicitly supplied prior_owner captured before detach. Only legitimate owner identities are returned; no account-wide unrelated characters. For world-time changes, iterate persistent session-bearing PlayerCharacter/NPC rows via their dialogue_session Attribute key, re-resolve valid context and deduplicate owners. For companion presence, membership's owner is enough because CompanionPresent requires its own party membership; host departure additionally runs existing host-session cleanup. These helpers never create a conversation or rewrite a selected scene. Every pusher renders each authenticated watcher own context/epoch using commander_sessions plus resolve_commander filtering and current watchers_for registration.

This change is complete independently: change a synthetic condition through each named real writer, observe its current choices and rollback controls, without selecting a topic again. Reading/unread observation is attached later by unread-notices through the SAME refresh API. No module scan/research task is delegated to implementation; the following source matrix fixes hook placement. Existing gameplay writes/transactions and cache compensation remain their owners.

## Exact physical source-family matrix

| Condition source | Exact existing/new commit hook | Affected owner capture | Acceptance |
|---|---|---|---|
| Carried item, including use/trade/transfer | world/rules/equipment.py::apply_inventory_plan after inventory + ACQUIRE writes, inside caller atomic | plan.entity owner via helper; both transfer plans independently capture their owners | Telnet, another web connection and no-session call all refresh; outer rollback publishes nothing |
| Worn exposure bias | world/rules/equipment.py::toggle_equipment after successful final equipment/gauge write | changed actor owner | wearing/unequipping changes threshold choice with current variant unchanged |
| Base exposure transition | world/rules/sexual_transitions.py::apply_event after its successful complete event cascade | entity owner captured before operation | exposure threshold crossing refreshes once final committed state is visible; fault later in outer operation cancels callbacks |
| Structured social identity | proposed world/rules/social_identity.py::set_social_identities after validated write | entity owner; construction with no live dialogue is no-op | tag add/remove refreshes a live possessed actor; persona prose edit has no effect |
| Skill ownership and proficiency | world/rules/progression/_gates.py::award_practice_xp after stored XP assignment; world/rules/progression/_lineage.py::apply_lineage_auto_seed after ownership assignment; world/rules/cross_lineage_unlock.py live ownership grant boundary | affected learner owner | passive/active ownership and proficiency threshold updates refresh, including study/other-session origin |
| Race | existing construction/import establishes race before any dialogue; opening and selection always re-read actor.race | no speculative new race writer | new-body race is honored; control refresh owns changing actor identity |

The cross-lineage hook is exactly `world.rules.cross_lineage_unlock.grant_owned_skill`, immediately after entity.db.skills assignment and only when it returns a new grant; do not attach to clause_satisfied or duplicate it in evaluate_cross_lineage_unlocks. The source inspection identified this module as the live grant owner; no new skill mutation API is introduced. Any raw GM console Attribute repair is the explicit repository repair exception, outside ordinary gameplay publication; its next canonical sync re-evaluates state, and this change does not add repair telemetry or auto-repair behavior.

## Implementation handoff constraints

Each task is a 45-120 minute unit with its own focused tests/docs. This proposal is capped at one engineer-day and implements no gameplay arithmetic. Use an untracked .env.test containing MUD_TEST_SETTINGS=1 for future Evennia commands. Register new tests in .github/evennia-shards.json and run focused tests plus contract_gate at apply handoff. No tests, lint, builds or formatters run during proposal creation.


## Exact target files

- `world/rules/dialogue_availability.py`
- `world/rules/equipment.py::apply_inventory_plan/toggle_equipment`
- `world/rules/sexual_transitions.py::apply_event`
- `world/rules/social_identity.py::set_social_identities`
- `world/rules/progression/_gates.py::award_practice_xp`
- `world/rules/progression/_lineage.py::apply_lineage_auto_seed`
- `world/rules/cross_lineage_unlock.py`

## Risks / Trade-offs

Extends dialogue_availability.py and physical writers only. Progression/lifecycle refresh follows to reuse callback/owner helpers. Shared manifests need serial integration; no gameplay arithmetic changes. Keep authored source validation separate from runtime eligibility. A failed post-commit push recovers on the next canonical sync, without reversing a successful owning commit. Read the approved design and dependency artifacts before edits; no interface decision is left open.

## Focused verification at implementation time

```text
uv run --locked --env-file=.env.test evennia test --settings test_settings.py --keepdb world.rules.tests.test_dialogue_refresh_physical
uv run --locked python -m tools.contract_gate
```

Run only focused test labels/methods within the repository time limits. Full managed browser and evidence suites remain CI-owned. These commands are planned acceptance, not results from proposal creation.
