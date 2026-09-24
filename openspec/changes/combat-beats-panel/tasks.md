## 1. Preconditions

- [ ] 1.1 Re-confirm the facts in design.md Context and stop to report if any differ:
  - `grep -rhoE 'kind="[a-z_]+"' world/rules --include='*.py'` shows no `EventEntry` of kind `skill` (only `commanded_kind` / `commanded_action_kind` arguments).
  - `world/rules/action/event_log.py` builds `damage` with `data={"amount": amount}` after a `roll` entry.
  - `_submit_request` in `world/rules/combat_session/rounds.py` returns the `_continue_or_settle(...)` result.
  - `settle_to_oob_result` is called only from `web/webclient/actions/combat_actions.py` (three adapters) and `service_actions.py::_inventory_use_adapter`: `grep -rn "settle_to_oob_result" --include='*.py' web world commands`.
  - `_normalize_result` in `web/webclient/actions/dispatcher.py` copies only `outcome`, `code`, `message`, `correlation_id`, and `data`.

## 2. Rules: per-entry text and the round record

- [ ] 2.1 `world/rules/event_log.py`: add `render_entry_text(entry: EventEntry) -> str`, the single `text_template.format(actor=..., target=..., data=...)` call, and rewrite `render_plain_text` as `"\n".join(render_entry_text(e) for e in event_log.entries)`. Add a case to `world/rules/tests/test_event_log.py` asserting that `render_plain_text` output is unchanged for a multi-entry log, including one with an empty template. Run `uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_event_log` green.
- [ ] 2.2 Create `world/rules/combat_beats.py` (design D1, D5–D9). It contains:
  - The constants `BEAT_KINDS = ("roll", "damage", "target_defeated", "other")`, `MAX_BEATS = 64`, `MAX_BEAT_TEXT = 256`, and `MAX_ROUND_ID = 160`.
  - Frozen `RoundRecord(session_id, number, logs, identities: Mapping[str, int], hp_before: Mapping[int, int], hp_after: Mapping[int, int])`, with `round_id` returning `f"{session_id}/{number}"`.
  - Frozen `CombatBeat(seq, action, kind, actor, target, amount, hp_after, text)` and `CombatBeatsView(round, beats)`.
  - `CombatBeatsError(ValueError)`.
  - `capture_round_hp(battlefield) -> tuple[dict[str, int], dict[int, int]]`, built on `world.rules.action.stored_gauge_pair`.
  - `build_combat_beats(record) -> CombatBeatsView`. It maps kinds, maps identities through `world.rules.art_view.portrait_catalog_key`, sets `amount` only on damage, and projects HP with the knockout floor. It computes `text = strip_ansi(render_entry_text(entry))` and checks each damage target's last `hp_after` against `record.hp_after`. It raises `CombatBeatsError` on over-bound input, an unknown damage target, or an HP mismatch.
  - A header docstring naming design §10.1 and this change. The module must not import `web.*`, `get_display_value`, or `disguised_stats`.
- [ ] 2.3 `world/rules/combat_session/rounds.py::_submit_request`: on the `opening == "round"` branch only, call `capture_round_hp(battlefield)` before `run_round` and again after the friendly-fire and coercion scans, before `_continue_or_settle`. Build `RoundRecord(record.session_id, new_record.rounds_elapsed, tuple(logs), ...)` and set `result["round_record"]` on the returned dict (round and terminal). The overwhelm branch sets nothing. Update the function docstring.
- [ ] 2.4 Create `world/rules/tests/test_combat_beats.py`, a pure builder test on hand-built `EventLog`s with synthetic keys and no DB. Annotate the tests with the new `webclient-combat-beats::…` IDs after task 6.1 syncs the specs. Cases:
  - the kind mapping order and `seq` / `action` values of the kind-mapping scenario;
  - catalog-key identities, and null for a non-participant;
  - `amount` / `hp_after` only on damage;
  - the 30 → 18 → 0 projection;
  - the knockout floor at 1;
  - a heal-caused mismatch raises;
  - an unknown damage target raises;
  - 65 entries raise, and a 257-code-point line raises;
  - `text` equals the corresponding line of `render_plain_text`, and ANSI codes are stripped;
  - no beat exposes `raw_roll` / `hit`.
  Run `uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_combat_beats` green.
- [ ] 2.5 Create `world/rules/tests/test_combat_round_record.py` using `world/rules/tests/_combat_session_helpers.py` (`open_synthetic_scope`, `synth_innate_overlay`) and `combat_fixtures.BattlefieldIsolation`, like `web/webclient/actions/tests/test_combat_dispatcher.py`. Cases:
  - `submit_player_action` on a non-terminal round returns `round_record` with pre-round HP, end-of-round HP equal to `build_combat_view(actor)` `hp_current` per participant, `number == read_session(actor).rounds_elapsed`, and only the round's logs.
  - A terminal (defeating) round still carries a record whose foe end-of-round HP is 0.
  - A preflight rejection and `forfeit` carry no record.
  Run the module green.

## 3. Transport: result slot, context, dispatcher

- [ ] 3.1 `world/rules/combat_result.py`:
  - `settle_to_oob_result` copies `result["round_record"]`, when present on a success outcome, to `oob["combat_round"]`. Note in its docstring that the slot is internal and dropped by `_normalize_result`.
  - Append `"combat_beats"` to `AFFECTED_PANELS` and extend its comment.
  - Update `world/rules/tests/test_combat_result.py::test_oob_round_result_declares_affected_panels` to the new tuple, and add a case asserting that the `combat_round` slot is set only when a record is present.
  Run `uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_combat_result` green.
- [ ] 3.2 `web/webclient/presentation/context.py`: add `combat_round: Any = field(default=None)` to `PresentationContext`, documented as the completing action's frozen `RoundRecord` (design D2). `web/webclient/presentation/ingress.py::build_presentation_context`: add the keyword `combat_round=None` and pass it through; update the docstring (only the dispatcher completion passes it). `web/webclient/actions/dispatcher.py::_publish_completion`: when `isinstance(value.get("combat_round"), RoundRecord)`, pass it to `build_presentation_context`. Verify with `grep -n "combat_round" web/webclient/actions/dispatcher.py web/webclient/presentation/ingress.py` that no other call site passes it.

## 4. Presenter and registry

- [ ] 4.1 Create `web/webclient/presentation/combat_beats.py`:
  - `COMBAT_BEATS_SCHEMA_VERSION = 1` and `COMBAT_BEATS_MAX_BYTES = 12_288`, re-exporting the rules bounds.
  - `validate_combat_beats(payload)`, an exact validator raising `ProtocolValidationError`. It checks the field sets, `round` length, the beat count, contiguous `seq`, non-decreasing `action`, the closed kinds, catalog-key identities (decimal, ≤ 32 chars, like `combat_panel._validate_participant`), damage and non-damage invariants, `text` ≤ 256 code points, and the byte budget via `json_byte_size`.
  - `combat_beats_presenter(context)`. When `context.combat_round` is `None` it raises `PanelUnavailableError`. Otherwise it calls `build_combat_beats`; on `CombatBeatsError` it logs `log_warn("combat_beats_unavailable", context={"char": ..., "reason": <bounded code>})` and raises `PanelUnavailableError`. It then serializes and validates the payload.
  - Register it in `web/webclient/presentation/registry.py::build_production_registry` as `name="combat_beats", schema_version=COMBAT_BEATS_SCHEMA_VERSION, unavailable_reason=UNAVAILABLE_REASON`.
  Run `uv run --locked python -m tools.observability_lint check` green.
- [ ] 4.2 Create `web/webclient/presentation/tests/test_combat_beats_panel.py`. Cases:
  - the exact available form from a hand-built `RoundRecord`;
  - the unavailable form (non-internal, no `correlation_id`, registered version) with no record, on an HP mismatch, and past each bound;
  - the validator rejects an unknown kind, an extra field, a non-contiguous `seq`, a damage beat with null `hp_after`, a non-damage beat with an `amount`, and a non-decimal identity;
  - the byte budget;
  - rendering leaves the actor's traits and combat record unchanged;
  - a source scan of `world/rules/combat_beats.py` and `web/webclient/presentation/combat_beats.py` finds neither `get_display_value` nor `disguised_stats`;
  - a foe with `db.disguised_stats` set yields a true-HP `hp_after` equal to the combat view's `hp_current`.
  Update `test_combat_panel/test_presenter.py::test_production_registry_contains_every_registered_panel` to include `combat_beats`. Run both modules green.

## 5. Dispatcher integration and the client protocol mirror

- [ ] 5.1 `web/webclient/actions/tests/test_combat_dispatcher.py`: add these cases.
  - (a) A non-terminal `combat.cast` sends one update containing `status`, `context_actions`, `art`, and an available `combat_beats` at the same revision. Its `round` is `"<session_id>/1"`. Each damage target's last `hp_after` equals that update's `context_actions` participant `hp_current`. The sent `ui_action_result` has none of the keys `combat_round`, `round_record`, or `logs`.
  - (b) A defeating cast sends a full snapshot with mode `exploration` and an available `combat_beats` whose last beats include `target_defeated`.
  - (c) A later `ui_sync` / `synchronize_session` snapshot and a forfeit snapshot carry the unavailable form.
  - (d) The existing duplicate-request case also asserts that no second presentation is sent.
  In `test_inventory_actions.py::test_in_combat_use_occupies_the_round_and_publishes_full_snapshot`, assert that the snapshot carries `combat_beats` for that round. Add a case where the healed player is also damaged in the round, asserting the unavailable form (design D7).
  Run `uv run --locked evennia test --settings test_settings.py --keepdb web.webclient.actions.tests.test_combat_dispatcher web.webclient.actions.tests.test_inventory_actions` green.
- [ ] 5.2 Client protocol mirror:
  - `web/static/webclient/js/elosern/protocol/constants.js`: add `COMBAT_BEATS_SCHEMA_VERSION = 1`, `COMBAT_BEATS_MAX_BEATS = 64`, `COMBAT_BEATS_MAX_TEXT = 256`, `COMBAT_BEATS_MAX_ROUND = 160`, `COMBAT_BEATS_MAX_BYTES = 12288`, `COMBAT_BEATS_KINDS`, and `combat_beats: 1` in `PANEL_ALLOWLIST`, and export them.
  - Create `protocol/panels/combat_beats.js` with `validateCombatBeatsPanel(payload)`. It carries the `payload.schema_version !== COMBAT_BEATS_SCHEMA_VERSION` re-check and the same rules as 4.1.
  - Wire it into `envelope.js` `PANEL_VALIDATORS` and export it from `web/static/webclient/js/elosern/protocol.js`.
  - `web/webclient-app/stores/elosern/shared.js`: add `"combat_beats"` to `PANEL_ALLOWLIST`. Mirror the addition in the local list of `web/webclient-app/tests/store/store_slices.test.js`.
- [ ] 5.3 Create `web/static/webclient/js/tests/protocol_combat_beats.test.js`. Cases:
  - an available form and an empty-beats form validate;
  - the unavailable form validates;
  - each rejection from 4.2 fails;
  - a snapshot carrying `combat_beats` passes `validateUiSnapshot`, and one with a bad beat is rejected.
  Use synthetic names only. In `web/webclient/tests/test_node_suite_evidence.py`, add `test_combat_beats_node_suite_passes`, running that file and annotated with `webclient-combat-beats::the-client-protocol-mirrors-the-combat-beats-schema`. Run `node --test web/static/webclient/js/tests/*.test.js` green.
- [ ] 5.4 `tests/test_panel_schema_version_parity_contract.py`: add `("combat_beats", "combat_beats.py")` to `_PANEL_MODULES`. Add `test_combat_beats_bounds_are_pinned`, asserting that the Python `MAX_BEATS` / `MAX_BEAT_TEXT` / `MAX_ROUND_ID` / `COMBAT_BEATS_MAX_BYTES` / `BEAT_KINDS` equal the JS `COMBAT_BEATS_*` values. Run `uv run --locked evennia test --settings test_settings.py --keepdb tests.test_panel_schema_version_parity_contract` green.
- [ ] 5.5 `web/tests/browser/test_browser_combat_panels.py`: extend `test_combat_rebuilds_keyboard_menu_after_round` (already annotated for the combat-results requirement), or add a sibling test annotated `webclient-combat-beats::the-beats-panel-is-published-only-with-the-combat-action-that-produced-it`. After the first round it reads `window.__elosernBridge.store.view.panels.combat_beats` and asserts `available === true`, a `round` ending in `/1`, and at least one `roll` beat whose `target` equals the monster participant's `portrait_ref`. Run `uv run --locked python -m unittest web.tests.browser.test_browser_combat_panels` green.

## 6. Specs and traceability

- [ ] 6.1 Sync this change's deltas into `openspec/specs/` (new `webclient-combat-beats/spec.md`, and the `webclient-combat-menu` and `webclient-oob-protocol` blocks). Then annotate the tests from 2.4, 2.5, 4.2, 5.1, and 5.3 with `@covers_requirement` IDs taken from `uv run --locked python -m tools.spec_traceability list`, so that every new requirement and the new scenarios are covered. The `webclient-oob-protocol` round-record scenario is covered by 5.1(c). Run `uv run --locked python -m tools.spec_traceability check` green.

## 7. Validation

- [ ] 7.1 Run each of these green:
  - `node --test web/static/webclient/js/tests/*.test.js`
  - `pnpm test`
  - `pnpm run build`
  - `uv run --locked python -m tools.test_data_lint check`
  - `uv run --locked python -m tools.spec_traceability check`
  - `uv run --locked python -m tools.observability_lint check`
  - `uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_event_log world.rules.tests.test_combat_beats world.rules.tests.test_combat_round_record world.rules.tests.test_combat_result world.rules.tests.test_combat_session_recovery world.rules.tests.test_combat_session_flow web.webclient.presentation.tests.test_combat_beats_panel web.webclient.presentation.tests.test_combat_panel web.webclient.presentation.tests.test_registry web.webclient.presentation.tests.test_coordinator web.webclient.actions.tests.test_combat_dispatcher web.webclient.actions.tests.test_combat_actions web.webclient.actions.tests.test_inventory_actions web.webclient.tests.test_node_suite_evidence tests.test_panel_schema_version_parity_contract`
  - `uv run --locked python -m unittest web.tests.browser.test_browser_combat_panels`
- [ ] 7.2 Run `openspec validate combat-beats-panel --strict` and `git diff --check`; both clean.
