## Why

After an admitted combat action, the server emits every `EventLog` as text and then publishes `status`, `context_actions`, and `art` at one newer revision. The browser can see the round's end state, but it cannot tell which hit caused which HP loss, and it must not parse prose to find out (`webclient-combat-menu` "Combat results update canonical panels and preserve narrative logs"). Design §10.1 (`docs/superpowers/specs/2026-09-23-webclient-avg-stage-redesign-design.md`) asks for structured, server-authored combat beats, so that C13 (`webclient-combat-beat-playback`) can play a round beat by beat. This change delivers the server side and the protocol only.

**Implementation profile:** logic. The change adds a rules helper, a presenter, a validator, dispatcher wiring, and a JS protocol mirror. Every part is checked by Python and Node tests, and no part renders anything.

## What Changes

- New rules module `world/rules/combat_beats.py`:
  - `RoundRecord` is a frozen record of one settled ordinary round. It holds the session ID, the round number, the round's own `EventLog`s, a map from roster key to dbref, and each participant's stored HP before and after the round.
  - `build_combat_beats(record)` derives the beats and returns a frozen `CombatBeatsView`. It raises `CombatBeatsError` when a bound is exceeded, when a `damage` beat names a target that is not a participant, or when the projected HP disagrees with the recorded HP.
- `world/rules/event_log.py`: add `render_entry_text(entry)`, which renders one entry. `render_plain_text` becomes a `"\n"` join over it and its output is unchanged.
- `world/rules/combat_session/rounds.py` `_submit_request`: on the default `opening == "round"` path, read every roster participant's stored HP before `run_round` and again after the round's scans, before `_continue_or_settle`. Attach the resulting `RoundRecord` to the returned result as `result["round_record"]`, on terminal results too. The overwhelm opening attaches nothing.
- `world/rules/combat_result.py`:
  - `settle_to_oob_result` copies `result["round_record"]` into the internal slot `combat_round` of the adapter result. The slot never reaches the wire.
  - `combat_beats` joins `AFFECTED_PANELS`.
- `web/webclient/presentation/context.py` / `ingress.py`: `PresentationContext` gains `combat_round: RoundRecord | None = None`, and `build_presentation_context` gains a keyword `combat_round=None`.
- `web/webclient/actions/dispatcher.py` `_publish_completion`: pass the adapter result's internal `combat_round` (only a `RoundRecord` instance) into `build_presentation_context`. `_normalize_result` already drops unknown keys; a new test pins that the slot is dropped.
- New presenter module `web/webclient/presentation/combat_beats.py`:
  - `COMBAT_BEATS_SCHEMA_VERSION = 1`, `combat_beats_presenter`, and the exact validator `validate_combat_beats`.
  - The panel is registered in `registry.py` as `combat_beats` with the common `UNAVAILABLE_REASON`.
  - Payload: `round` plus at most 64 `beats`. Each beat has exactly `seq`, `action`, `kind` (`roll` | `damage` | `target_defeated` | `other`), `actor`, `target`, `amount`, `hp_after`, and `text`.
- JS protocol mirror:
  - `web/static/webclient/js/elosern/protocol/panels/combat_beats.js` with `validateCombatBeatsPanel`.
  - Its constants go in `constants.js`: `combat_beats: 1` in `PANEL_ALLOWLIST`, plus `COMBAT_BEATS_*` bounds.
  - It is wired into the `envelope.js` `PANEL_VALIDATORS` and exported from `protocol.js`.
  - `web/webclient-app/stores/elosern/shared.js` `PANEL_ALLOWLIST` gains `"combat_beats"`. The store only commits the panel; nothing reads it yet.
- Tests:
  - New `world/rules/tests/test_combat_beats.py`, `world/rules/tests/test_combat_round_record.py`, `web/webclient/presentation/tests/test_combat_beats_panel.py`, and `web/static/webclient/js/tests/protocol_combat_beats.test.js`.
  - New dispatcher cases in `web/webclient/actions/tests/test_combat_dispatcher.py` and `test_inventory_actions.py`, and one browser case in `web/tests/browser/test_browser_combat_panels.py`.
  - Updated pins in `world/rules/tests/test_combat_result.py`, `web/webclient/presentation/tests/test_combat_panel/test_presenter.py`, `tests/test_panel_schema_version_parity_contract.py`, and `web/webclient-app/tests/store/store_slices.test.js`.
- The closed kind set departs from the design table. No `skill` entry kind exists in `world/rules` (the design listed one), so `skill` is not in the set, and each beat instead carries the `action` ordinal of its `EventLog` (design.md D5).

## Capabilities

### New Capabilities

- `webclient-combat-beats`: the read-only `combat_beats` panel. It covers the exact schema and bounds, derivation from the settled round's `EventEntry` records, server-side `hp_after` projection and its check against recorded HP, when the panel is published and when it is unavailable (including reconnect), the disclosure boundary, and the client protocol mirror.

### Modified Capabilities

- `webclient-combat-menu`: "Combat results update canonical panels and preserve narrative logs". The completing publication also carries `combat_beats` at the same revision as `status`.
- `webclient-oob-protocol`: "Presenter registration and execution are isolated and read-only". The read context may carry the completing action's frozen round record, which only the dispatcher's completion publication supplies. `combat_beats` joins the registered set without changing the envelope.

## Impact

- New files:
  - `world/rules/combat_beats.py`
  - `web/webclient/presentation/combat_beats.py`
  - `web/static/webclient/js/elosern/protocol/panels/combat_beats.js`
  - `world/rules/tests/test_combat_beats.py`
  - `world/rules/tests/test_combat_round_record.py`
  - `web/webclient/presentation/tests/test_combat_beats_panel.py`
  - `web/static/webclient/js/tests/protocol_combat_beats.test.js`
- Edited server files:
  - `world/rules/event_log.py`
  - `world/rules/combat_session/rounds.py`
  - `world/rules/combat_result.py`
  - `web/webclient/presentation/{context,ingress,registry}.py`
  - `web/webclient/actions/dispatcher.py`
- Edited client files, protocol and allowlist only:
  - `web/static/webclient/js/elosern/protocol/{constants,envelope}.js`
  - `web/static/webclient/js/elosern/protocol.js`
  - `web/webclient-app/stores/elosern/shared.js`
- Edited tests:
  - `world/rules/tests/test_combat_result.py`
  - `web/webclient/presentation/tests/test_combat_panel/test_presenter.py`
  - `web/webclient/actions/tests/test_combat_dispatcher.py`
  - `web/webclient/actions/tests/test_inventory_actions.py`
  - `tests/test_panel_schema_version_parity_contract.py`
  - `web/webclient/tests/test_node_suite_evidence.py`
  - `web/webclient-app/tests/store/store_slices.test.js`
  - `web/tests/browser/test_browser_combat_panels.py`
- Protocol: a new registered panel. The envelope schemas, `MAX_PANEL_COUNT` (32; 20 panels after this change), and every other panel stay unchanged.
- No persistence, migration, or Telnet change. Typed commands and Telnet keep `emit_narrative` / `settle_to_messages` unchanged.
- Out of scope:
  - All client rendering, the beat queue, `--motion-beat`, the HP animation, and the fallback path: `webclient-combat-beat-playback` (C13).
  - Beats for the overwhelm opening and for fights opened by the typed `cast` command (`world/rules/combat_initiation.py`): these publish the unavailable form, and C13 falls back to paging the text.
- Dependencies: none on the client series. Archive order: after C11c (`webclient-mode-transitions`), before C13 (`webclient-combat-beat-playback`).
