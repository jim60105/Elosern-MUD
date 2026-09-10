## 1. Make the ordinary round the default

- [x] 1.1 Add keyword-only `opening: Literal["round", "overwhelm"] = "round"` and `first_actor: str | None = None` to `_submit_request()` in `world/rules/combat_session.py`
- [x] 1.2 Replace the `if overwhelming == player_team` branch with a dispatch on `opening`, keeping both bodies otherwise unchanged and both inside the existing outer `transaction.atomic()`
- [x] 1.3 Drop the `overwhelming` and `player_team` parameters from `_submit_request()`'s signature; the caller no longer supplies a verdict
- [x] 1.4 Pass `first_actor` into `combat.run_round()` on the `"round"` path and into `resolve_overwhelm()` on the `"overwhelm"` path
- [x] 1.5 Keep the `combat_round_settled` boundary event bound to the `opening == "round"` path only, and update its comment to say so in those terms
- [x] 1.6 Replace the long dispatch comment with one explaining that compression is opt-in and that `submit_opening_action()` is its only sanctioned requester
- [x] 1.7 Confirm `simulated`, `nonlethal_keys`, `journal_sink`, and `notifications_sink` are forwarded identically on both paths

## 2. Strip compression from the in-session entries

- [x] 2.1 Remove the `classify_overwhelm()` call and the `player_team` computation from `submit_player_action()`; call `_submit_request()` without `opening`
- [x] 2.2 Remove the same from `submit_player_item_use()`
- [x] 2.3 Update both docstrings: one preflight-valid submission is one ordinary round, whatever the verdict; compression is reachable only by opening a fight from exploration
- [x] 2.4 Leave the informational `overwhelming_team` value in `engage()`'s and `_continue_or_settle()`'s returned dicts untouched — it is a pure query

## 3. Multi-enemy engagement

- [x] 3.1 Add `engage_group(actor, targets)` carrying every step `engage()` performs today: `PlayerCharacter` check, no-active-session check, per-target living-hostile-`Monster`-in-room check, `combat_companions()` collection, record construction with one dbref per target in deterministic order, `reconstruct_battlefield()`, `_persist()`, `register_active_battlefield()`, `clear_dialogue_session()`, and the returned record plus informational verdict
- [x] 3.2 Reduce `engage(actor, target)` to a delegation to `engage_group(actor, [target])`, keeping its signature, return shape, and raised `CombatSessionError` reasons identical
- [x] 3.3 Reject the whole group with no persisted session when any single target fails validation
- [x] 3.4 Verify `commands/combat.py:48` and the webclient `_engage_adapter` need no edit

## 4. The opening-action seam

- [x] 4.1 Add `submit_opening_action(actor, skill_key, targets, scale)` reading the session, reconstructing the battlefield, running `revalidate_submission()` and `ActionResolver.preflight()` exactly as `submit_player_action()` does
- [x] 4.2 Compute `opening="overwhelm"` if and only if `classify_overwhelm(battlefield)` equals the actor's team **and** `overwhelm.commanded_damage_reaches_enemy(battlefield, actor_key, skill_key, resolved_target_keys)` is true; otherwise `"round"`
- [x] 4.3 Reject an approved AREA shorthand (`all-enemies` / `all-allies` / `all`) before initiative, and reject any target absent from the reconstructed roster, so a shorthand can never reach the predicate and silently return `False` — which would disable one-shot settlement with no diagnostic
- [x] 4.4 Resolve the submitted targets to concrete roster keys before calling the predicate, since it takes concrete keys only
- [x] 4.5 Always pass `first_actor=str(actor.key)`, for both selections
- [x] 4.6 Accept skills only, and pass `commanded_kind="skill"` through to compression's log marker
- [x] 4.7 Document that this is the sole production requester of compression

## 5. Tests

- [x] 5.1 Assert an in-session skill submission under a player-overwhelming verdict resolves exactly one round and never calls `resolve_overwhelm()`
- [x] 5.2 Assert the same for an in-session item use under a player-overwhelming verdict
- [x] 5.3 Assert by inspection that neither public in-session entry passes `opening` or calls `classify_overwhelm()` for dispatch
- [x] 5.4 Assert both `opening` values forward the same `simulated`, `nonlethal_keys`, journal sink, and notification sink
- [x] 5.5 Assert `submit_opening_action()` selects compression only for a damaging skill aimed at an enemy under a player-direction verdict, and one ordinary round for a non-damaging skill, a contested verdict, and a foe-overwhelming verdict
- [x] 5.6 Assert the player resolves first in the opening round under both selections, using a fixed seed for a battlefield whose ordinary initiative would not place them first
- [x] 5.7 Assert the compressed log still carries exactly one first-round `commanded_action` entry with the `skill` kind and the submitted key
- [x] 5.8 Assert `resolve_overwhelm()` has exactly one production call site
- [x] 5.9 `engage_group()`: a two-enemy session persists both dbrefs in deterministic order, reconstructs both onto the opposing team, resolves a round, and settles; one invalid target rejects the whole group with nothing persisted and no battlefield registered
- [x] 5.10 `engage()`: return shape, `enemy_ids` length, and error reasons are unchanged from before this change
- [x] 5.11 Exercise a two-enemy session through `_primary_opponent_id()`, the friendly-fire and coercion scans, the knocked-out persistence, and terminal settlement, so any single-enemy assumption surfaces here
- [x] 5.12 Update the overwhelm resolution equivalence tests to drive compression through `submit_opening_action()` instead of the ordinary submission path, threading the same `first_actor` into the manually driven `run_round()` comparison loop's FIRST iteration and `None` into the rest — otherwise the equivalence contract compares a first-strike compressed run against an ordinary-initiative manual run and fails for the wrong reason
- [x] 5.13 Assert `submit_opening_action()` rejects an AREA shorthand and an off-roster target before initiative, with no round run and nothing spent
- [x] 5.14 Annotate every new test with `covers_requirement` from `uv run --locked python -m tools.spec_traceability list`
- [x] 5.15 Prefer extending existing `world/rules/tests/` modules so `.github/evennia-shards.json` stays untouched; if a new module is unavoidable, register it in exactly one shard in this change

## 6. Verification

- [x] 6.1 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.rules` (satisfied by focused per-module runs of every combat-session, overwhelm, friendly-fire, and item-turn module per AGENTS.md's focused-test rule; full-package label exceeds the 10-minute local limit)
- [x] 6.2 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb commands web.webclient` (satisfied by focused consumer runs: `commands.tests.test_combat_actions`, webclient combat actions/dispatcher/panel — 151/151)
- [x] 6.3 `uv run --locked python -m tools.observability_lint check`
- [x] 6.4 `uv run --locked python -m tools.spec_traceability check`
- [x] 6.5 `uv run --locked python -m compileall -q world commands web`
- [x] 6.6 `openspec validate combat-session-opening-dispatch --strict`
