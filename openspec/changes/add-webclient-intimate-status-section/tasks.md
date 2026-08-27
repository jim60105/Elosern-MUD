## 1. Server: read model

- [ ] 1.1 In `world/rules/status_query.py`, inspect `_LevelRef`'s exact attributes before writing the reader, so the new code reads its level string correctly.
- [ ] 1.2 Add a `_sexual_counter(entity, field)` no-create-safe reader for `climax_today`, reading the materialized entry's computed value the same way `_require_static_trait` prefers `raw.get("current", raw.get("base"))` (not `.base` alone — matches `SexualState.climax_today`'s canonical `.value` semantics), falling back to the baseline's `climax_today` (default `0`) when only a baseline exists, `None` when nothing exists at all, and `StatusQueryError` on a malformed present record.
- [ ] 1.3 Add an `IntimateView` frozen dataclass (`arousal`, `wetness`, `shame`, `exposure`, `climax_phase`: `str`; `climax_today`: `int`) and a `_read_intimate(entity) -> IntimateView | None` that calls `_sexual_level()` for the five level fields and `_sexual_counter()` for `climax_today`. **Do not trust `_sexual_level()`'s return value as-is**: `_read_intimate()` must itself reject (raise `StatusQueryError`) any returned value that is not exactly one of `None` (record absent), a `_LevelRef` whose `.level` is a member of that field's vocabulary tuple, or a `str` that is itself a member of that vocabulary tuple — `_sexual_level()` has an undocumented fourth branch that can return a raw, unvalidated value (including a Python `bool` misread as an ordinal) verbatim; see design.md's Decisions section. Return `None` for the whole view the moment any field resolves to "absent" (no partial `IntimateView`).
- [ ] 1.4 Add `intimate: IntimateView | None` to `CharacterReadModel` and populate it in `build_character_read_model()`.
- [ ] 1.5 Add test cases to `world/rules/tests/test_status_query.py`: materialized record, baseline-only record, no record at all (`None`), a malformed-and-rejected record (bad vocabulary value — raises `StatusQueryError`, caught by the presenter as `PanelUnavailableError`), and specifically a case where a stored `value` is a `bool` (e.g. `True`) or an out-of-range int, asserting `_read_intimate()` rejects it rather than silently accepting it as ordinal `1`/`0`.

## 2. Server: presenter and schema

- [ ] 2.1 Bump `CHARACTER_SCHEMA_VERSION` from 3 to 4 in `web/webclient/presentation/character.py`.
- [ ] 2.2 Add `_validate_intimate(value)` to `character.py`: `None` is valid; otherwise `_require_exact_fields` on `{arousal, wetness, shame, exposure, climax_phase, climax_today}`, each level field checked against its exact vocabulary tuple (import from `world/lore/sexual_vocab.py`), `climax_today` via `_require_int(minimum=0, maximum=MAX_SAFE_INTEGER)`.
- [ ] 2.3 Add `intimate` to `validate_character()`'s exact-fields set and to `_serialize()`'s returned dict (serializing `model.intimate` through a small dict-builder, or `None`).
- [ ] 2.4 Update `web/webclient/presentation/tests/test_character_panel.py`: schema_version now rejects `3`, accepts `4`; `intimate` present/absent/each malformed-field-shape rejection.
- [ ] 2.5 Update `web/webclient/presentation/tests/test_registry.py`'s `test_character_unavailable_payload_stamps_the_registered_version` to assert schema version `4`.

## 3. Client: component and stories

- [ ] 3.1 In `CharacterStatusDrawer.vue`, add a computed `intimate` reading `props.character?.intimate ?? null` (only meaningful when `characterAvailable`), and a `<details>`/`<summary>` section rendered `v-if="intimate"`, positioned after the 偽裝 section (per design.md's placement decision) and before 錢包.
- [ ] 3.2 Render the six rows (`arousal`/`wetness`/`shame`/`exposure`/`climax_phase` as level-word `statrow`s using the shared two-column tile styling, `climax_today` as `{n} 次`) plus the static hint line "詞彙封閉；數值依設定折線/級別顯示" verbatim from the 設計稿.
- [ ] 3.3 Add stories to `web/webclient-app/stories/Data/CharacterStatusDrawer.stories.js`: one with `character.intimate` populated (verify collapsed by default, expandable), one with `character.intimate: null` (verify the section is entirely absent from the rendered DOM).
- [ ] 3.4 Add `intimate` to `CHARACTER_PANEL_SAMPLE` in `web/webclient-app/stories/fixtures.js`; add a second fixture variant (or reuse `CHARACTER_PANEL_UNDISGUISED_SAMPLE`) with `intimate: null`.
- [ ] 3.5 Update `web/webclient-app/tests/data/character_status_drawer.test.js`: section renders when `intimate` is present, is absent from the DOM when `null`, six values render verbatim, hint copy renders verbatim.
- [ ] 3.6 Remove the intimate-block assertion from `web/webclient-app/tests/overlays/deferred_surfaces_absent.test.js`, keeping the remaining deferred-surface assertions (Party panel, event-log toasts, game-help browser, persistent objective tracker) unchanged.

## 4. Roadmap amendments and cross-proposal reconciliation

- [ ] 4.1 In `docs/superpowers/specs/2026-08-25-webclient-hud-redesign-roadmap-design.md` §2.4 and §3 Non-Goals, add a dated correction note removing 親密狀態 from the "no backing read model" / "no ... 親密狀態 block" language, referencing this change, mirroring §1's existing "Correction" convention used elsewhere in this roadmap family.
- [ ] 4.2 In `docs/superpowers/specs/2026-08-19-webclient-vue-migration-roadmap-design.md` §7, add the same dated correction removing the "intimate / adult status collapsible" line from the deferred-surfaces list.
- [ ] 4.3 Before archiving this change, diff `specs/webclient-contextual-hud/spec.md`'s copied section-order/`屬性`-filter/abbreviated-label text (originally drafted from `fix-webclient-character-status-drawer-order`) against that sibling change's actual final text at the time it archives, and reconcile any wording that changed during the sibling's own revision — this proposal's copy was a snapshot taken before the sibling finished revising and may be stale (design.md's Risks section).

## 5. Verification

- [ ] 5.1 `uv run pytest world/rules/tests/test_status_query.py web/webclient/presentation/tests/test_character_panel.py web/webclient/presentation/tests/test_registry.py` (or the project's standard Python test invocation) green.
- [ ] 5.2 `npm test` (Vitest) green.
- [ ] 5.3 `npm run build-storybook` and `npm run showcase-coverage` green.
- [ ] 5.4 `openspec validate add-webclient-intimate-status-section --strict` passes.
