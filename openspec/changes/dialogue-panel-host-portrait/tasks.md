## 1. Preconditions

- [x] 1.1 Confirm C9a (`explore-talk-open-action`) and C9b (`webclient-talk-open-dock`) are archived (`ls openspec/changes/archive | grep -e explore-talk-open-action -e webclient-talk-open-dock` lists both), and confirm the starting state: `grep -n "portrait_ref must be null" web/webclient/presentation/dialogue.py web/static/webclient/js/elosern/protocol/panels/misc.js` matches the dialogue host validators, and `grep -n "DIALOGUE_SCHEMA_VERSION = 1" web/webclient/presentation/dialogue.py web/static/webclient/js/elosern/protocol/constants.js` matches both. Stop and report if either differs.

## 2. Server

- [x] 2.1 `web/webclient/presentation/dialogue.py`:
  - `DIALOGUE_SCHEMA_VERSION = 2`; add `MAX_DIALOGUE_PORTRAIT_REF = 32` (design D2) and export it.
  - `_validate_host` accepts `portrait_ref` `None` or a `str` that `isdecimal()` and has at most `MAX_DIALOGUE_PORTRAIT_REF` characters, rejecting a non-string, a non-decimal string, and an over-bound string with the combat rule's messages.
  - `dialogue_presenter`: after `_resolve_live_host`, call `world.rules.art_view.build_art_view(actor)` inside `try/except ArtViewError`; set `portrait_ref` to `portrait_catalog_key(int(npc.pk))` when `int(npc.pk)` is among `view.entities` identities, else `None` (design D1).
  - Rewrite the module docstring's host-triple sentence (the host's `portrait_ref` is the art catalog key when the host is in the art view).
- [x] 2.2 `web/webclient/presentation/tests/test_dialogue_panel.py`:
  - Re-anchor the `@covers_requirement` at line 165 to `webclient-dialogue-session::the-dialogue-panel-is-an-exact-read-only-version-2-presentation-panel`; the exact-vocabulary case expects `portrait_ref == portrait_catalog_key(self.host.pk)`.
  - Add, under the same annotation: the key equals a key of the `art` panel's `portrait_catalog` rendered from the same registry and context; a host outside the art view yields `null` with the panel still available — an `LLMNPC` stand-in without a dialogue component or portrait policy, a scripted host dropped by the `MAX_PORTRAIT_CATALOG` cap in a room of 32 lower-identity eligible entities (design.md's named risk), and `build_art_view` patched to raise `ArtViewError`; the presenter still writes nothing (extend `test_presenter_is_read_only` to the art view call).
  - `test_drift_rejects`: move the `"42"` host case to the accepted set; add numeric `42`, `"4a"`, and a 33-digit string to the rejected set; add a case pinning `MAX_DIALOGUE_PORTRAIT_REF == combat_panel.MAX_PARTICIPANT_REF`.
  - Run `uv run --locked evennia test --settings test_settings.py --keepdb web.webclient.presentation.tests.test_dialogue_panel`; green.

## 3. Protocol mirror

- [x] 3.1 `web/static/webclient/js/elosern/protocol/constants.js`: `DIALOGUE_SCHEMA_VERSION = 2`, and `PANEL_ALLOWLIST.dialogue` to `2` — the allowlist value IS the registered schema version (`envelope.js` `validatePanels` passes it to `validatePanel`, and the unavailable form re-checks it), and `tests/test_panel_schema_version_parity_contract.py` reads it as the third of its four equality sites. `web/static/webclient/js/elosern/protocol/panels/misc.js`: the dialogue host validator (the block at lines 253–266) accepts `null` or `/^[0-9]+$/` with at most 32 characters, with the combat mirror's messages; update the header comment at line 228 ("a null portrait_ref"). The party-row validator above it keeps its null rule.
- [x] 3.2 `web/static/webclient/js/tests/protocol_dialogue.test.js`: fixtures to `schema_version: 2`; `validDialoguePanel({ schema_version: 1 })` becomes the version drift case; the `"42"` host moves to the valid cases; add numeric, non-decimal, and 33-digit rejections. The `Protocol.PANEL_ALLOWLIST.dialogue` assertion, the `__proto__` `JSON.parse` fixture, the incomplete-panel snapshot case, and both snapshot unavailable forms move to `2` so each keeps failing (or passing) for its intended reason. Run `node --test web/static/webclient/js/tests/*.test.js`; green.

## 4. Client fixtures and comment

- [x] 4.1 Bump `schema_version` to `2` in every dialogue fixture: `grep -rln 'kind: "dialogue"' web/webclient-app/tests web/webclient-app/stories` lists `tests/message_window_dialogue.test.js`, `tests/dialogue_view_model.test.js`, `tests/dialogue_store.test.js`, `tests/message_window.test.js`, `tests/message_window_typing.test.js`, `tests/store/store_slices.test.js`, `tests/store/declarative_frames.test.js`, `tests/store/digit_row_picks.test.js`, `stories/Core/MessageWindow.stories.js`, and `stories/Core/AppShell.stories.js`. The two unavailable-form fixtures (`tests/dialogue_store.test.js`, `tests/dialogue_view_model.test.js`) move too: the registry builds the unavailable form from the panel's schema version. The two dialogue panels injected by `web/tests/browser/test_browser_contextual_hud_stage.py` move for the same consistency (they reach the store through `store.receive`, so no validator sees them). In `tests/dialogue_view_model.test.js`, add one case where `portrait_ref: "41"` yields `host.portraitRef === "41"`.
- [x] 4.2 `web/webclient-app/stores/dialogue-view.js`: the header comment says `portraitRef` is the host's art catalog key or null. Run `pnpm test` (repository root); green.

## 5. Specs and traceability

- [x] 5.1 Sync this change's delta into `openspec/specs/webclient-dialogue-session/spec.md`. Confirm the new ID with `uv run --locked python -m tools.spec_traceability list`, and check that `grep -rn "the-dialogue-panel-is-an-exact-read-only-version-1" web tests world` returns nothing.

## 6. Validation

- [x] 6.1 Run `node --test web/static/webclient/js/tests/*.test.js`, `pnpm test`, `pnpm run build`, `pnpm run build-storybook` (repository root), `uv run --locked python -m tools.test_data_lint check`, `uv run --locked python -m tools.spec_traceability check`, and `uv run --locked evennia test --settings test_settings.py --keepdb web.webclient.presentation.tests.test_dialogue_panel web.webclient.presentation.tests.test_art_panel tests.test_panel_schema_version_parity_contract`; all green.
- [x] 6.2 Run `openspec validate dialogue-panel-host-portrait --strict` and `git diff --check`; both clean.

### Verification record (2026-09-26)

- `evennia test … test_dialogue_panel test_art_panel tests.test_panel_schema_version_parity_contract`
  → Ran 61 tests, OK (`test_dialogue_panel` alone: 31 tests, OK).
- `node --test web/static/webclient/js/tests/*.test.js` → 461 pass, 0 fail.
- `pnpm test` → 108 files, 1135 tests, all pass.
- `pnpm run build` and `pnpm run build-storybook` → both completed.
- `tools.test_data_lint check` → 0 violations; `tools.observability_lint check` → 0 violations.
- `tools.spec_traceability check` → 1707 requirements, 1707 covered, 0 uncovered, 0 errors.
- `openspec validate dialogue-panel-host-portrait --strict` → valid; `openspec validate --all --strict`
  → 268 passed, 0 failed; `git diff --check` → clean.
- CI-owned and therefore NOT run or checked locally: the full non-browser Evennia suite, the
  managed browser sweep, and `tools.spec_traceability verify --evidence`. This change names no
  browser work, so no managed browser class was run.
