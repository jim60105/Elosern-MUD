# Tasks: defeat-aftermath-core

## 1. Settings + seam

- [x] 1.1 `server/conf/settings.py`: `DEFEAT_ADULT_SCENES = True` (documented as the adult-hook guard); `world/rules/defeat_aftermath.py` skeleton: `run_defeat_aftermath(battlefield, session, result)` called from `settle_session`'s defeat branch inside the existing `transaction.atomic()`, ending with a guarded no-op violation hook registry (`if settings.DEFEAT_ADULT_SCENES: _HOOK(...)`)
- [x] 1.2 Phase order inside the writer: HP floor 1 + knockout mark → violation hook (guarded) → violator departure → weak debuff grant → EventLog + defeat lines + `defeat_aftermath` info event; session clearing stays last in `settle_session` (unchanged position)

## 2. HP floor + never-revive test rewrite

- [x] 2.1 Player defeat path: stored HP := 1, player added to the session's knockout record; exam (`exam_failed`) path untouched
- [x] 2.2 Rewrite `test_solo_defeat_settlement_never_revives_the_player` and `test_restored_dead_player_session_never_revives_the_player`: player settles at 1, settlement applies no regen past the floor; keep as regression

## 3. Violator departure

- [x] 3.1 Quest-binding scan: settling player's `db.quest_log` records → `objective_target_ids` set (read-only via `world/quests/runtime.py` accessors)
- [x] 3.2 Departure loop over living foe-team members: `population_key` set → despawn (marker + bookkeeping cleared in-transaction via `world/maps/wilderness_population.depart_population_monster`; physical `delete()` scheduled on the outermost commit via `transaction.on_commit`, delete failure reverts the departure); quest-bound pk → retain (precedence over the marker); foreign → untouched; EventLog `violator_depart` per departure
- [x] 3.3 Test the retained-winner consequence: skip-safety still refuses rest in the room; movement is unguarded (pin current behavior, no edit)

## 4. Weak debuff + rulebook

- [x] 4.1 `rulebook/buffs.yaml`: `defeat_weak` row (bounds ceilings on atk_phys/agility/defense, world-second duration); mount through the existing buff-attach path at settlement; `status_display.yaml` metadata entry keeps the fail-closed coverage green
- [x] 4.2 `rulebook/defeat_aftermath.yaml` + loader: sections `pg_lines`, `weak_debuff` validated by the core; unknown sections ignored with one `log_warn` (forward-compat); malformed owned section fails load

## 5. Rendering + observability

- [x] 5.1 EventLog kinds `defeat_settle` / `violator_depart` / `weak_granted` with zh-tw template lines in `player_messages.py` (replaces the bare defeat line on this path only)
- [x] 5.2 `defeat_aftermath` boundary info event `{char, room, tick, hp_after}`; run `tools.observability_lint check` in the same batch

## 6. Zero-uncaused-write battery

- [x] 6.1 `world/rules/tests/test_defeat_aftermath_core.py`: declared-write manifest (code, not prose) — fixture with active quest + bound companions + guild rank + copper; assert affinity/wallet/inventory/quest-progress/guild-rank/protected-bindings byte-identical except manifest-listed clock-caused mutations; assert despawn/retain/foreign outcomes; assert one info event; assert manifest section-ownership
- [x] 6.2 Rollback injection: fault after the writer's last write, before commit → monster, buff, HP, EventLog, session clearing all absent; retry settles fully exactly once
- [x] 6.3 Register the new test module in exactly one `.github/evennia-shards.json` shard; `covers_requirement` annotations for every main-spec requirement the change touches — the new `defeat-aftermath-core::*` delta IDs are intentionally withheld until this change's archive/sync lands them in `openspec/specs/` (the `test_rules_observability` precedent); `uv run --locked python -m tools.spec_traceability check` green
- [x] 6.4 Focused run green: `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_defeat_aftermath_core typeclasses world web.webclient` (combat-session subset); `git diff --check` clean
