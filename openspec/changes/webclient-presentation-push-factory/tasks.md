## 0. Ground rules (apply to every task)

- Behavior-preserving refactor only: no payload, protocol, or player-visible change.
- Log event ids stay byte-identical; never add a new event id. After the whole change,
  `tools/observability_freeze.json` must only shrink or stay equal, never gain entries.
- No test file is renamed or moved; `.github/evennia-shards.json` is not edited.
- Every Evennia test run uses `MUD_TEST_SETTINGS=1` passed via the Bash tool's `env` input
  (never as an inline prefix), e.g.
  `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb <label>`.

## 1. Panel pusher factory

- [ ] 1.1 Create `web/webclient/presentation/push.py` with
  `make_panel_pusher(panel_key: str, event_prefix: str) -> Callable[[Any], None]` whose body
  is the shared fan-out currently repeated in `party_push.py`/`dialogue_push.py`/
  `lore_codex_push.py`: watchers lookup → `{prefix}_push_watchers_failed` on failure;
  registry construction → `{prefix}_push_failed` on failure; per-session render +
  `publish_panel_update(session, player, {panel_key: payload}, context=..., expected_epoch=epoch)`
  → `{prefix}_push_failed` (with `"session"` context key) on failure. Import `log_warn` in
  `push.py` via `from world.observability import log_warn`; keep the per-module docstrings'
  seam rationale on the shells. Verify: `uv run --locked python -m compileall -q web/webclient/presentation/push.py`.
- [ ] 1.2 Rewrite `web/webclient/presentation/party_push.py` as a thin shell: keep the module
  docstring, module-level `from world.observability import log_warn` re-import (test patch
  target), and `push_party_update = make_panel_pusher("party", "party")`. The existing test
  patches `web.webclient.presentation.party_push.log_warn` and
  `build_production_registry` — for patchability, the shell passes the module's own bound
  names into the factory (factory takes injectable `watchers_for`,
  `build_production_registry`, `publish_panel_update`, `build_presentation_context`,
  `log_warn` parameters defaulting to the shared imports; shells pass nothing extra unless
  a test patches them — check `test_party_panel.py:481-495` patches
  `party_push.watchers_for`, `party_push.build_production_registry`, `party_push.log_warn`
  and make the shell resolve those names through module globals at call time, e.g.
  the factory body calls `get_dependencies()` supplied by the shell as
  `lambda: (watchers_for, build_production_registry, ...)`, or equivalently the factory
  receives a `deps` provider reading the shell module's globals). Pick the simplest shape
  that keeps every existing patch target live. Verify:
  `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb web.webclient.presentation.tests.test_party_panel`.
- [ ] 1.3 Same shell treatment for `dialogue_push.py` (`("dialogue", "dialogue")`) and
  `lore_codex_push.py` (`("lore_codex", "lore_codex")`). Verify:
  `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb web.webclient.presentation.tests.test_dialogue_panel` and
  `... web.webclient.presentation.tests.test_lore_codex_panel`.
- [ ] 1.4 Leave `art_push.py` on its own signal-subscriber path (it fans out over
  SESSION_HANDLER sessions with a coordinator, not watchers_for — NOT one of the identical
  quadruplets), but do not duplicate any new shared code it doesn't need. Verify:
  `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb web.webclient.presentation.tests.test_art_push`.
- [ ] 1.5 Diff-check the extracted trio: `git diff` must show the three shells containing no
  remaining fan-out logic and the factory containing exactly one copy; confirm the four
  event-id strings appear exactly once each in `push.py` template usage and nowhere else new
  (grep `party_push_failed|dialogue_push_failed|lore_codex_push_watchers_failed` etc.).

## 2. Creation validators

- [ ] 2.1 Create `web/webclient/presentation/protocol_validation.py` with
  `validate_background(value, error_cls, max_length)` and
  `validate_affinity_elements(value, race_key, error_cls, *, empty_as_none: bool)`
  reproducing the UNION of both current behaviors: the presentation copy
  (`presentation/creation.py:427-477`) adds a `MAX_AFFINITY_ELEMENTS` global-bound check the
  actions copy lacks — keep it behind a parameter default `None` so the actions call site
  keeps its exact current accept/reject set (do NOT silently tighten the submit surface).
  Return shape parameter-free: return a `list` and let each shell map (`list` passthrough vs
  `tuple(...)`), and each shell raises with its own `error_cls`
  (`ProtocolValidationError` / `CreationActionError`). Error message texts stay byte-identical
  per site — the messages are already identical between the copies, keep them as-is.
- [ ] 2.2 Point `presentation/creation.py::_validate_background` and
  `_validate_affinity_elements` at the shared helpers (keep the private names as thin
  delegates; `test_creation_panel.py` patches `_validate_affinity` — not these two — so no
  test change is expected). Verify:
  `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb web.webclient.presentation.tests.test_creation_panel`.
- [ ] 2.3 Point `actions/creation_actions.py::_validate_background` and
  `_validate_affinity_elements` at the same helpers with `CreationActionError`,
  `empty_as_none=True`, tuple return, no global bound. Verify:
  `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb web.webclient.actions.tests.test_creation_actions`.
- [ ] 2.4 Add focused Vitest-free unit coverage is NOT needed (Python behavior, already
  covered by both suites). Instead run both suites together plus the actions package:
  `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb web.webclient.actions web.webclient.presentation.tests.test_creation_panel`.

## 3. Protocol field validators

- [ ] 3.1 Move the byte-identical `_require_exit_ref` (and its ASCII check) into
  `protocol_validation.py` as `require_exit_ref(value, field, error_cls)`; `MAX_EXIT_REF_CHARS`
  stays defined where it is today or moves with it — keep the constants importable from
  their current modules if any test imports them (check first:
  `grep "_require_exit_ref\|MAX_EXIT_REF_CHARS" web/webclient -r`). The two copies in
  `presentation/local_map.py:86` and `presentation/exploration.py:116` become delegates or
  direct imports.
- [ ] 3.2 Keep `_require_node_id` in BOTH modules with their divergent semantics — local_map
  lets `decode_node`'s `KnowledgeError` escape; exploration wraps it in
  `ProtocolValidationError`. Factor only the shared shape check into
  `protocol_validation.py::require_node_id_shape(value, field, error_cls, max_chars)`; each
  site wraps it. Add a comment at the shared function: divergence is observable and
  test-pinned; do not unify. Verify:
  `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb web.webclient.presentation.tests.test_local_map` and
  `... web.webclient.presentation.tests.test_exploration_panel`.

## 4. Wave close-out verification

- [ ] 4.1 `uv run --locked python -m tools.spec_traceability check` passes unchanged (no
  requirement moved, no annotation detached).
- [ ] 4.2 `uv run --locked python -m tools.observability_lint check` passes and
  `git diff --stat tools/observability_freeze.json` shows no additions (shrink-only rule).
- [ ] 4.3 Shard contract still green without manifest edits:
  `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb tests.test_evennia_test_optimization_contract`.
- [ ] 4.4 `git diff --check` clean; no change under `docs/game/` (no command surface touched).
