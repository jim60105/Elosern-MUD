## 0. Ground rules (apply to every task)

- Behavior-preserving refactor; the ONE bounded rejection-shape widening is design D1 and is
  verified, not assumed. No new log event ids. No test file renamed;
  `.github/evennia-shards.json` untouched.
- Evennia tests run with `MUD_TEST_SETTINGS=1` via the Bash tool's `env` input, e.g.
  `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb <label>`.
- `world.art` and `world.ai` are shard-covered package-wide by `quests-skills-art-ai-lore`;
  `web.art_media` is exercised via `web.webclient.tests` (test_art_media.py).

## 1. Art path confinement

- [ ] 1.1 Grep for tests pinning the OLD weak shape before flipping:
  `grep -rn "_resolved_under_root\|_write_temp\|NUL\|symlink" world/art/tests/test_worker.py web/webclient/tests/test_art_media.py world/art/tests/test_gallery.py`.
  Record which assertions exist. Only if a test pins a NUL identity raising `ValueError`
  through the worker, adjust it to the bounded `WorkerStoreError` (design D1 case 1) and say
  so in the commit message; otherwise touch no test here.
- [ ] 1.2 `world/art/worker.py`: delete `_store_root`/`_resolved_under_root` (lines 111-124);
  import `resolved_under_store_root` from `world.art.paths`; rewrite `_write_temp`'s gate
  (line 137-141) to `if resolved_under_store_root(identity) is None:` and the delete-site
  gate (line 371-373) to the identity-string form. `_store_root()` may stay if other lines
  still join paths with it (check `grep -n "_store_root()" world/art/worker.py`). Verify:
  `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.art.tests.test_worker` and
  `... world.art.tests.test_sd_worker`.
- [ ] 1.3 `web/art_media.py`: delete `_store_root`/`_resolved_under_root` (lines 68-80); the
  PLAIN committed-record fallback branch at 173-176 inside `art_media()` (NOT `_serve_gallery`,
  which at 125-131 already routes through `resolved_under_store_root`) becomes
  `resolved = resolved_under_store_root(identity)` (the manual `target.is_symlink()` 404 at 174
  is subsumed by the strict helper — delete it); defaults/gallery branches already use
  `resolved_under_root`/`resolved_under_store_root`, leave them. Keep the module import line
  tidy (the names are already imported at line 27).
  Verify: `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb web.webclient.tests.test_art_media`.
- [ ] 1.4 Security-regression pin: confirm `world/art/tests/test_gallery.py`'s symlink/NUL
  cases (lines ~131-179) pass untouched, and run
  `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.art.tests.test_gallery`
  plus `... world.art.tests.test_gallery_fallback`.

## 2. AI guardrail hooks helper

- [ ] 2.1 Add `GuardrailHooks` (frozen dataclass, `install()` / `uninstall_own()`) to
  `world/ai/guardrail.py` exactly per design D2, reusing `_require_layer`,
  `register_degrade_fallback`, `register_semantic_validator`, and the
  `GuardrailRegistrationError` rollback semantics (identity-only removal; foreign hooks
  untouched). Verify the helper itself under
  `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.ai.tests.test_guardrail`.
- [ ] 2.2 Migrate `world/ai/narrator.py`: delete `_uninstall_fallback`, `_uninstall_validator`,
  `_uninstall_all_own_hooks`; `register_narrator` keeps its callable check, `_is_registered()`
  no-op, try/except → `hooks.uninstall_own()` → re-raise, and `_template_renderer`
  assignment. Verify:
  `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.ai.tests.test_narrator`.
- [ ] 2.3 Migrate `world/ai/npc_dialogue.py`, `world/ai/scene_flavor.py`,
  `world/ai/character_creation.py`, `world/ai/scenario_director.py` the same way, keeping
  each layer's schema-registration interleaving inside its own `register_*`. Verify:
  `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.ai.tests.test_npc_dialogue_registration`,
  `... world.ai.tests.test_scene_flavor`, `... world.ai.tests.test_character_creation`,
  `... world.ai.tests.test_scenario_director_registration`.
- [ ] 2.4 Startup seams stay green (they call `register_*` through
  `server.conf.at_server_startstop`): run
  `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.ai.tests.test_ai_observability`.

## 3. `_reject_mutable_containers` single copy

- [ ] 3.1 Create `world/ai/immutable.py` with `reject_mutable_containers(value, path)` —
  byte-identical behavior of `action_options.py:134-149` (same `TypeError` message). In
  `world/ai/action_options.py` and `world/ai/scenario_director.py`, replace the local defs
  with `from world.ai.immutable import reject_mutable_containers as _reject_mutable_containers`.
  Verify: `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.ai.tests.test_action_options_schema` and
  `... world.ai.tests.test_scenario_director_proposals`.

## 4. Wave close-out verification

- [ ] 4.1 `uv run --locked python -m tools.spec_traceability check` unchanged-passes.
- [ ] 4.2 `uv run --locked python -m tools.observability_lint check` passes; no new
  `tools/observability_freeze.json` entries (`git diff` on it is empty).
- [ ] 4.3 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb tests.test_evennia_test_optimization_contract`
  green with no manifest edit.
- [ ] 4.4 `git diff --check` clean.
