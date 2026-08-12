## 1. Core compression change

- [x] 1.1 Remove the kind-based filtering in `compress_event_logs()` (`world/rules/overwhelm.py`): every `EventEntry` of every input `EventLog` is preserved in original order via `dataclasses.replace()`; only an input `EventLog` with zero entries is dropped; the summary prepend and its `rounds`/`hits`/`total_damage` computation stay unchanged
- [x] 1.2 Add optional `commanded_actor=None` / `commanded_skill=None` / `commanded_window=None` keyword arguments to `compress_event_logs()`; when all three are provided, prepend exactly one `commanded_action` entry to the first `EventLog` **within `commanded_window`** whose `actor` and `skill_key` both match (applied at most once, no marker when nothing in the window matches or any argument is omitted): `actor=commanded_actor`, `target=None`, `data={"skill": <label>}` with the label resolved via `SKILL_REGISTRY.get(skill_key, ...)` falling back to the raw key (never raising), `text_template="你施展了「{data[skill]}」。"`; import `SKILL_REGISTRY` from `world.skills.registry` (read-only, established direction)
- [x] 1.3 Add the optional `commanded_actor` / `commanded_skill` keyword arguments to `resolve_overwhelm()`; capture the first `combat.run_round()` call's returned logs as the round-1 window and forward it with both arguments to `compress_event_logs()`; confirm the function still performs no combat math outside `run_round()` and that omitting the arguments changes nothing but the absence of the marker

## 2. Session facade plumbing

- [x] 2.1 In `submit_player_action()` (`world/rules/combat_session.py`), pass `commanded_actor=str(actor.key)` and `commanded_skill=skill_key` on the player-overwhelming branch only; the non-compressed branch and all other call sites stay untouched

## 3. Unit tests

- [x] 3.1 Rewrite `world/rules/tests/test_overwhelm_compression.py` for the preservation contract: a successful `roll` entry survives alongside its paired `damage` entry in original order; a miss roll survives unchanged; an input `EventLog` with zero entries is dropped; the returned entry count equals the input count plus one (summary), plus one more when a marker is applied; the summary entry's data is unchanged
- [x] 3.2 Add marker tests: the first log matching `(commanded_actor, commanded_skill)` inside the provided `commanded_window` gains the `commanded_action` entry and logs outside the window are not marked; no matching log in the window yields no marker (explicitly including the invalidated-`basic_attack` case where a round-2 auto basic attack matches actor+skill but lies outside the window); default calls yield no marker; an unknown `commanded_skill` falls back to the raw key without raising; `render_plain_text()` of the marked log opens with `你施展了「基本攻擊」。`
- [x] 3.3 Add an equivalence test using two independently built, identical starting `Battlefield` fixtures: `resolve_overwhelm()` with and without `commanded_actor`/`commanded_skill` under the same seed produce identical `rounds_elapsed`, `total_seconds`, `verdict_after`, `battle_over`, final HP, and damage entries — differing only by the marker entry

## 4. Integration tests

- [x] 4.1 Add a fixed-dice integration test reproducing the reported scenario: in a player-overwhelming session the player commands `basic_attack` on themselves, the compressed rendered log contains the marker line, the commanded self-attack's miss roll line, and the auto basic attack's roll line immediately before its damage line on the enemy — documenting both the readable attribution and that self-targeting damage stays legal (the commanded action resolves against the actor)
- [x] 4.2 Confirm the friendly-fire overwhelm test (`test_friendly_fire.py` OverwhelmCompressionTests), party, disengage, monster-behaviour, and quest-planning overwhelm integration tests still pass unchanged (they consume only `damage`/defeat/state, all preserved byte-for-byte)
- [x] 4.3 Add a narrator-boundary sanity test: a maximum-size compressed log (12 rounds, 16 participants, every action hitting) degrades gracefully through `narrate_event_logs`'s bounded-serialization path to the deterministic template renderer without raising

## 5. Spec and traceability updates

- [x] 5.1 Update `covers_requirement` annotations: remove references to the removed main requirement ID `event-log-compression::compress-event-logs-drops-redundant-hit-rolls-and-preserves-miss-and-damage-records`; after the delta specs are synced into `openspec/specs/` (archive/sync workflow), annotate the tests that establish the new requirements with their canonical IDs from `uv run --locked python -m tools.spec_traceability list` (`compress-event-logs-preserves-every-attack-record-without-kind-based-filtering`, `compress-event-logs-marks-the-player-s-commanded-action-with-a-commanded-action-entry`) and keep the existing IDs on the summary/rendering/player-combat-session/single-shot-resolution tests
- [x] 5.2 Run `uv run --locked python -m tools.spec_traceability check` after the sync and confirm zero errors and zero uncovered requirements
- [x] 5.3 Confirm no player-facing command surface changed (no key, alias, syntax, or availability change): no update to `docs/game/commands.md` / `docs/game/command-reference.md` is needed; run `tests/test_command_docs.py` to prove it

## 6. Verification

- [x] 6.1 Run the affected Evennia tests: `world.rules.tests.test_overwhelm_compression`, `world.rules.tests.test_overwhelm_resolution`, `world.rules.tests.test_combat_session`, `world.rules.tests.test_friendly_fire`, `world.rules.tests.test_combat_party`, `world.rules.tests.test_disengage_integration`, `world.rules.tests.test_monster_behaviour_integration`, `world.quests.tests.test_integration`, and `tests.test_command_docs`
- [x] 6.2 Run the full non-browser Evennia suite (`MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --noinput --parallel 4 commands server typeclasses world web.webclient`), `uv run --locked python -m compileall -q world typeclasses commands server`, and keep `git diff --check` clean
- [x] 6.3 Run `openspec validate overwhelm-log-attribution --strict` and confirm the change is apply-ready and all artifacts are consistent
- [ ] 6.4 Final handoff gate after the archive/sync workflow: run the three required test entry points with the same `OPENSPEC_TEST_EVIDENCE` path (Evennia suite, managed browser suite, top-level `unittest discover -s tests`), then `uv run --locked python -m tools.spec_traceability verify --evidence "$traceability_evidence"` and `openspec validate --all --strict`
