## Context

See proposal.md for the motivation. The current code works as follows:

- **Round transaction.** `world/rules/combat_session/rounds.py::_submit_request` runs one round inside one `transaction.atomic()`:
  - `run_round(...)` returns `logs`: every resolved action's `EventLog`, then the upkeep logs from `settle_upkeep`.
  - Next come the friendly-fire and coercion scans and the record update.
  - Last, `_continue_or_settle(...)` returns either `{"outcome": "round", "rounds_elapsed", "logs", "overwhelming_team"}` or the terminal `settle_session(...)` result. The terminal result's `"logs"` are `(*logs, *aftermath_logs)`: the defeat aftermath appends its own logs.
  - Only the actor's `hp_before` is read today, and only for the `combat_round_settled` boundary line.
- **Adapters.** `combat.cast` / `combat.flee` (`web/webclient/actions/combat_actions.py`) and `inventory.use` in an active session (`service_actions.py::_inventory_use_adapter`) call `emit_settlement(actor, result)` and then `settle_to_oob_result(result)`.
  - A round result declares `AFFECTED_PANELS` (`status`, `context_actions`, `art`, `party`, `services`, `objectives`, `quest_log`).
  - A terminal result declares `()`, and the dispatcher turns that into a full snapshot.
  - `inventory.use` always declares `()`.
- **Dispatcher.** `_publish_completion` builds the context through `build_presentation_context(session, actor)`, publishes, and then sends `_normalize_result(value)`. `_normalize_result` rebuilds the result from `outcome` / `code` / `message` / `correlation_id` / `data` only, so any other key never reaches the wire. The internal `no_presentation` flag already relies on this.
- **EventEntry facts:**
  - `actor` / `target` are entity keys (`str(entity.key)`). `reconstruct_battlefield` guarantees they are unique within a session (`DUPLICATE_PARTICIPANT`).
  - The action pipeline (`world/rules/action/event_log.py`) emits `roll` (`data={"raw_roll", "hit"}`) and then `damage` (`data={"amount"}`) on a hit. After a positive-to-non-positive crossing it adds `target_defeated`, or `target_knocked_out` under a nonlethal policy; a nonlethal crossing floors HP at 1 (`world/rules/combat/damage.py`).
  - Upkeep emits `damage` with the applied amount, and `target_defeated` / `target_knocked_out`.
  - **No producer emits an entry of kind `skill`.** `grep -rhoE 'kind="[a-z_]+"' world/rules` finds `kind="skill"` only as `commanded_kind` / `commanded_action_kind` arguments.
- **Identities.** `world/rules/art_view.py::portrait_catalog_key(identity)` returns `str(int(dbref))`. `combat_view.py` fills `ParticipantView.portrait_ref` with it, so the combat panel's `portrait_ref` and the art catalog key are the same string.
- **HP.** The combat panel ships true `hp_current` / `hp_maximum` for every participant, foes included. The value comes from `stored_gauge_pair(entity, "hp")` and involves no ratio or disguise. `disguised-stats-boundary` keeps `get_display_value` / `disguised_stats` out of combat.

## Goals / Non-Goals

**Goals:**
- A beat list that the server builds from `EventEntry` records alone, with no prose parsing. Each `hp_after` is checked against the HP the round recorded before the panel is sent.
- The panel is available in exactly one publication: the one that completes the combat action that produced the round.
- A client validator that mirrors the server's exact schema.

**Non-Goals:**
- Any client consumer: store getters, playback, animation, the fallback path, and `--motion-beat` belong to C13.
- Beats for the overwhelm opening or for fights opened by the typed `cast` command (`combat_initiation.initiate_field_combat`). Neither path goes through `settle_to_oob_result`, so both publish the unavailable form.
- Changing any `EventEntry` producer, template, or text-channel output.

## Decisions

### D1. The round transaction records HP before and after
`_submit_request` reads `{dbref: stored_gauge_pair(entity, "hp")[0]}` for every `battlefield.roster` entity at two points:
- before `run_round`;
- after the scans, before `_continue_or_settle`.

It also records `{roster_key: dbref}`, the session ID, and `new_record.rounds_elapsed`. These go into a frozen `RoundRecord`, together with the round's own `logs` (the `run_round` return, not the terminal aftermath logs). The record is attached as `result["round_record"]` to both the round result and the terminal result. The overwhelm opening attaches nothing.

*Alternative:* snapshot HP in the adapter before the call and read committed HP after it. Rejected for three reasons. A terminal settlement may delete the defeated monster (`finalize_departure`) or the exam opponent (`_delete_exam_opponent`). It restores simulated-battle gauges. It runs the defeat aftermath. All of these break the "after" read for exactly the most important round, the killing blow.

The "after" point is the committed end-of-round HP:
- For a non-terminal round nothing writes HP between it and the presenter, so it equals `status` HP and the combat panel's `hp_current` at the same revision. A test pins this.
- For a terminal round it is the HP the round really reached. Settlement may change HP afterwards (exam restoration), and C13 snaps to the committed `status` when playback ends (design §10.2).

### D2. The record travels by an internal result slot into the read context
`settle_to_oob_result` copies `result["round_record"]` into `oob["combat_round"]` on success outcomes. `_publish_completion` passes `value.get("combat_round")` to `build_presentation_context(session, actor, combat_round=...)`, and only when it is a `RoundRecord` instance. `PresentationContext.combat_round` defaults to `None`. `_normalize_result` already drops the slot; a test pins that the wire result has no `combat_round`, no `logs`, and no `round_record`.

The presenter stays a pure function of its frozen context, and the registry isolation contract is unchanged. The `webclient-oob-protocol` "Presenter registration…" delta records that the context may carry this completion-only record.

*Alternative:* store the last round in `session.ndb`, as `options_state` does. Rejected. It adds lifetime state that every other publication would have to clear, and it would make replay after reconnect possible, which D4 forbids.

### D3. Availability: only the completing publication, terminal rounds included
The panel is available if and only if the context carries a `RoundRecord`, which means only in the publication that completes `combat.cast`, `combat.flee`, or an in-session `inventory.use`.
- A non-terminal round names `combat_beats` in `AFFECTED_PANELS`, so the beats ride the same `ui_update` as `status`.
- A terminal round's full snapshot also carries the available panel, even though its `mode` is already `exploration`.

Every other publication renders the common unavailable form (`UNAVAILABLE_REASON`, non-internal). That covers `ui_sync` / reconnect, text-command refresh, stale / error completions, rejected results, forfeit (it has no round), pushes, and any full snapshot. The same applies when the context carries no record.

*Deviation from design §10.1's "available only in combat mode":* keying on mode would drop every terminal round, including the defeating blow and a successful flee. That is the round whose choreography matters most, and its snapshot already carries mode `exploration`. Keying on the completing publication keeps the intent: the panel never appears in ordinary exploration traffic. **C13 must play a terminal round's beats before its combat → exploration transition (C11c `data-mode-change`).** The coordinator should carry this into C13.

### D4. Reconnect carries the unavailable form; `round` stops a second choreography
A reconnect `ui_sync` builds a context without a record, so `combat_beats` is unavailable. This follows design §12 ("No transition or combat beat replays"). It also avoids durable or `ndb` state, and the round's text is already in the log.

`round` is `"<session_id>/<rounds_elapsed after the round>"`, for example `hostile:42:1200/3`, at most 160 code points. It is unique per settled round, because `session_id` embeds actor and tick and the round number rises. Within an epoch a client plays one `round` at most once, even if a later publication re-delivers the same panel object. A duplicate `request_id` replays only the cached result, never presentation.

*Alternative:* ship the last round's beats in the reconnect snapshot and rely on `round` alone. Rejected. The client's "last played round" memory is reset with the epoch, so the round would play again.

### D5. Closed kind set `roll`, `damage`, `target_defeated`, `other`, plus the `action` ordinal
Design §10.1 lists `skill`, but no entry of kind `skill` exists (see Context), and inventing one would add a beat with no source line. Every other entry kind maps to `other`, including `target_knocked_out`, `action_skipped`, `resource_spend`, `trait_delta`, `heal`, and `item_used`.

So that C13 can still play the "actor steps toward centre" gesture, each beat carries `action`: the 0-based ordinal of its source `EventLog` within the round. The first beat of each `action` group is where that group's `actor` acts. Adding a kind (for example `skill` or `target_knocked_out`) needs a spec change.

### D6. `actor` / `target` are catalog keys or null
A beat's `actor` / `target` is `portrait_catalog_key(dbref)` when the entry's key maps to a round participant. It is null otherwise: a missing target, or a name outside the roster. These are the same strings as the combat panel's `portrait_ref` and the art catalog keys. A `damage` beat whose target is not a participant fails the build, because its HP cannot be projected.

### D7. `hp_after`: damage-only projection with the knockout floor, checked
For each participant, keep a running value that starts from `hp_before`. Each `damage` beat sets `hp = max(floor, hp - amount)`. The floor is 1 when the round contains a `target_knocked_out` entry naming that target, else 0. That beat's `hp_after` is the new value. Every non-damage beat has `hp_after: null` and `amount: null`.

After the build, for every target of at least one `damage` beat, the last `hp_after` must equal the recorded end-of-round HP. Otherwise the build raises, and the presenter raises `PanelUnavailableError`, which yields the non-internal unavailable form and a `log_warn("combat_beats_hp_mismatch", context={...})` line.

This check catches HP changes that carry no damage entry: `heal`, `self_heal`, drain `gauge_transfer`, `damage_divert`, silent unattributed upkeep ticks, and item heals. Those rounds fall back (design §10.2) and are never shown with wrong numbers.

**Visibility:** `hp_after` is shipped for foes as a number, the same rule as the participant frame. `context_actions` already ships every participant's true numeric HP at the same revision, and no ratio rule exists. A value from the same `stored_gauge_pair` source discloses nothing new.

### D8. Bounds reject; nothing is truncated
- At most 64 beats (`COMBAT_BEATS_MAX_BEATS`).
- `text` at most 256 code points (`COMBAT_BEATS_MAX_TEXT`).
- `round` at most 160 code points.
- The panel's canonical JSON is at most 12,288 bytes (`COMBAT_BEATS_MAX_BYTES`). A typical beat is about 130 bytes, so 64 beats fit, and the budget keeps a terminal full snapshot well under the 65,536-byte envelope.

Past any bound, the round is unavailable. Truncating would break the "last `hp_after`" check and would cut a round mid-exchange. Large party rounds (many AoE rolls) may fall back; that is accepted.

### D9. `text` is the rendered line of the entry
`world/rules/event_log.py` gains `render_entry_text(entry)`, whose body is the one `format` call from `render_plain_text`. `render_plain_text` becomes `"\n".join(render_entry_text(e) for e in log.entries)`, and its output is byte-identical. A beat's `text` is `strip_ansi(render_entry_text(entry))`, where `strip_ansi` comes from `evennia.utils.ansi`. It is plain text, one-to-one with a line the text channel already delivered, and may be empty when a template is empty. The payload carries no `data` field beyond the damage `amount`, so `raw_roll`, `hit`, agility values, buff keys, and similar data never become structured wire data.

### D10. Where things live
- **Rules side:** `world/rules/combat_beats.py`. It holds `RoundRecord`, `CombatBeat`, `CombatBeatsView`, `CombatBeatsError`, `BEAT_KINDS`, `capture_round_hp(battlefield)`, and `build_combat_beats(record)`. It imports neither the presentation layer nor the disguise accessor.
- **Presenter side:** `web/webclient/presentation/combat_beats.py`. It serializes the view, calls the exact `validate_combat_beats` (bounds, closed kinds, `seq` = 0..n-1 contiguous, `action` non-decreasing, damage invariants, catalog-key shape, byte budget), and returns the payload.
- **JS mirror:** `panels/combat_beats.js`, with the same checks, named `validateCombatBeatsPanel` so that `tests/test_panel_schema_version_parity_contract.py::_js_recheck_value` finds its `payload.schema_version !== COMBAT_BEATS_SCHEMA_VERSION` re-check.

### D11. Archive order
**This change archives after C11c (`webclient-mode-transitions`) and before C13 (`webclient-combat-beat-playback`).** It has no client-series dependency and modifies no requirement that any other open series change touches. `grep -rl "Combat results update canonical panels\|Presenter registration and execution" openspec/changes` (outside `archive/`) finds nothing. If either base requirement changes before archive, re-sync the MODIFIED blocks and keep only this change's added sentences and scenarios.

## Risks / Trade-offs

- [Rounds with heals, drains, diverts, or silent ticks lose choreography] → This is intended (D7). The fallback shows the text and the committed values. Widening the projection needs a spec change.
- [Terminal round beats arrive with mode `exploration`] → D3 records the requirement on C13; until C13 lands, nothing consumes the panel.
- [A `RoundRecord` holds live `EventLog`s in memory during one publication] → It is frozen, built per action, and released with the context; nothing persists it.
- [Existing tests pin `AFFECTED_PANELS` and the registered panel set] → `test_combat_result.py` and `test_combat_panel/test_presenter.py` are updated in the same step. The three-list parity test (`test_panel_registration_is_mirrored_in_all_three_lists`) enforces the client allowlists.
- [Test-data lint flags shipped content in new tests] → New tests use the synthetic kit (`world.tests.synthetic_data`, `t_`-keyed skills, `_combat_session_helpers`), and `tools.test_data_lint check` runs in validation.
