## 1. Server: suggestions contract on the v5 panel

- [x] 1.1 Bump `CONTEXT_ACTIONS_SCHEMA_VERSION` to 5 in `web/webclient/presentation/combat_panel.py` and re-verify the version pin against the affordance-contract change's v4 (this change depends on it; land after it).
- [x] 1.2 Add the shared option caps and enums to the presentation layer (Python): `OPTIONS_STATUSES = ("generating", "ready", "degraded", "unavailable")`, `OPTIONS_CARD_KINDS = ("known_action", "freeform")`, `MAX_OPTION_CARDS = 5`, `MAX_OPTION_LABEL = 24`, `MAX_OPTION_HINT = 60`, `MAX_OPTION_PARAMS = 4` — mirroring the generative schema caps.
- [x] 1.3 Implement `validate_suggestions(value)` in `web/webclient/presentation/` (shared module imported by `combat_panel.py`): exact per-status key set (`status` alone for `generating`/`unavailable`; `status` + `cards` for `ready`/`degraded`), card exact keys, `action_code ∈ ACTION_CODE_ALLOWLIST` (freeform pin `"explore.talk_freeform"`), CJK label 1..24 code points, optional hint ≤ 60, `params` = the matching canonical affordance's validator-normalized payload (1..4 keys; safe ints/bounded strings plus the literal boolean `true` for the `explore.look` room-survey form; any other boolean rejected) or exactly the freeform `{"npc_id": positive int}` binding, counts `ready` 3–5 / `degraded` 0–5.
- [x] 1.4 Fold `suggestions` into `validate_context_actions`: exact field set gains `suggestions`; the common unavailable form keeps exactly `schema_version`/`available`/`reason` and MUST reject a `suggestions` field (add a synchronous test that the shared unavailable builder in `presentation/registry.py` was not altered); keep `.py` unit tests for every rejection (unknown status, extra/missing keys, out-of-bound cards/labels/hints/params, wrong freeform shape, boolean room-survey acceptance + other-boolean rejection).
- [x] 1.5 Add the read-side snapshot to `web/webclient/presentation/context.py`: frozen `OptionsSnapshot` (`fingerprint: str | None`, `status: str`, `generation_token: int`, `displayed: tuple[FrozenCard, ...] | None`) and `PresentationContext.options_state: OptionsSnapshot | None = None` (default preserves all existing constructors/tests); implement `options_snapshot(session)` in `web/webclient/presentation/ingress.py` that reads `session.ndb.options_state` (absent → `None`) and deep-copies displayed cards into immutable card representations.

## 2. Server: state-backed exploration presenter

- [x] 2.1 In the v5 exploration `context_actions` producer (the affordance-contract change's presenter seam), build the current affordances tuple **once**, serialize that same tuple into the form's `affordances`, and pass it to `default_cards(affordances, ...)` (the dependency change's signature; `objective_npc_ids` defaulted) — emit `suggestions` per design D-3: absent/`unavailable` snapshot → `{"status": "unavailable"}`; `generating` → status alone; `ready` → snapshot `displayed` cards; `degraded` → `default_cards(affordances)`; `ready` without a valid `displayed` set → `"unavailable"` plus a bounded `log_err` diagnostic (no fabricated cards).
- [x] 2.2 Combat producer: emit exactly `{"status": "unavailable"}` in both ready and recovery combat forms; assert it never reads `options_state`.
- [x] 2.3 Wire the `options_snapshot(session)` factory into every existing `PresentationContext` construction site: `dispatcher.py` lines 273 and 329 (`_settle_internal_error`, `_publish_completion`) and `ingress.py` line 125 (`synchronize_session`); all yield `None` until the trigger-service change populates session state.
- [x] 2.4 Add a depth-regression test: the deepest legitimate envelope leaf stays at combat skills depth 11 (≤ `MAX_DEPTH = 12`) once `suggestions.cards[].params` (leaf depth 7) is present.

## 3. Client mirror

- [x] 3.1 `web/static/webclient/js/elosern/protocol.js`: `PANEL_ALLOWLIST.context_actions` → 5.
- [x] 3.2 Add `OPTIONS_*` JS constants and `validateSuggestions` to `protocol.js` with identical per-status/card/count semantics (incl. the `{"room": true}` boolean acceptance and other-boolean rejection); wire it into `validateContextActionsPanel` for the combat and exploration forms, and make the unavailable branch **explicitly reject** a `suggestions` field (exact `schema_version`/`available`/`reason` only).
- [x] 3.3 Update every existing v4 fixture/expected payload in `protocol.js`, `protocol.test.js`, and `combat_menu.js` to v5 (combat: add `suggestions: {status: "unavailable"}`; keep one v4→v5 comparison fixture pinning combat field byte-identity).

## 4. Parity contract

- [x] 4.1 Add `tests/test_context_actions_parity_contract.py` following the `test_exploration_parity_contract.py` convention: Python/JS `OPTIONS_*` constant pairs and shared fragments (`"generating"`, `"ready"`, `"degraded"`, `"unavailable"`, `"known_action"`, `"freeform"`, `"explore.talk_freeform"`) must co-exist identically.

## 5. Suite updates and verification

- [x] 5.1 Update Python presentation tests (`test_combat_panel.py`, `test_protocol.py`, related panel/browser suites) so every `context_actions` fixture is v5-schema-valid and the surrounding expectations (epoch/revision, combat dock behavior) remain green.
- [x] 5.2 Add unit tests for the exploration suggestions render paths (absent snapshot, generating, ready-from-snapshot, degraded-from-`default_cards`, corrupted-ready fallback) and the combat unavailable pin.
- [x] 5.3 Run the owned test entry points: `uv run --locked evennia test --settings settings.py web.webclient.presentation.tests.test_combat_panel web.webclient.presentation.tests.test_protocol web.webclient.presentation.tests.test_coordinator tests.test_context_actions_parity_contract`, the Node suite (`node --test web/static/webclient/js/tests/*.test.js`), and `uv run --locked python -m tools.spec_traceability check`; keep `git diff --check` clean.
- [x] 5.4 Traceability handoff: after spec sync, add `covers_requirement` annotations with literal IDs from `uv run --locked python -m tools.spec_traceability list`, run both required test entry points under the same `OPENSPEC_TEST_EVIDENCE` path, then run `uv run --locked python -m tools.spec_traceability verify --evidence`.

## 6. Documentation

- [x] 6.1 No player command changes (`options.dismiss` is not part of this change); confirm `tests/test_command_docs.py` is untouched and green for the touched packages.
- [x] 6.2 Apply the roadmap amendment recorded in design.md: update the overview doc's §4 change-7 row (`context-actions-v3` → `context-actions-suggestions`, v5 wording) and the webclient design doc's version references, so the design set and the post-archive main specs cannot drift.
