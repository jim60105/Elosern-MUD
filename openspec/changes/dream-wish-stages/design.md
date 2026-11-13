# Design: conversing and finalized stages for the dream session

## Context

After `dream-working-proposal`:

- `actor.db.dream_surface` holds `proposal`, `changes`, `thread_id`,
  `thread_locked`; `dream_surface.wish_state`, `working_direction`,
  `offered_threads`, `choose_thread`, `lock_thread`, `store_response` exist.
- `server/dream_service.py::act` handles `say`, `choose_thread`, `draft`,
  `confirm`, `awaken`. `draft`/`confirm` accept a supplied `direction` (dict
  or text) in any state; `confirm` checks
  `reviewed_version_matches(payload, draft=shown)` and passes
  `direction=payload` to `lifecycle.confirm_session`.
- `world/narrative/dream_session.py`: `progress()` derives
  `free_text_allowed` from state and count; `choices()`; `begin_turn`;
  `settle_exchange`; `resume_saved_session`; `preserve_draft`;
  `confirm_session(direction=None)` confirms the already preserved draft and
  only runs the reviewed-version gate when a direction is passed.
- `authoring.save_draft` stamps `requirement_version` on every saved
  requirement-bearing direction; `validate_direction` refuses requirements
  without a version; `confirm_draft` re-validates and submits once.
- The panel is schema 3 (`web/webclient/presentation/dream.py`,
  `protocol/constants.js`, `protocol/panels/dream.js`), validated with exact
  field lists.

## Goals / Non-Goals

**Goals:** the stage, `finalize`, stage gating of every action, the resume
rule, and the additive schema-4 wire.

**Non-Goals:** `DreamPanel.vue` behaviour (only its test and story fixtures
gain the new keys so they stay valid payloads); removing schema-3 keys
(`dream-wish-stage-panel`); text commands and `commands/dream.py`
(`dream-wish-text-commands`); the farewell; `world/narrative/authoring.py`;
`world/ai/`; the exchange budget, sleep settlement and dispatch work.

## Decisions

1. **Model and migration.** `DreamSession.stage =
   models.CharField(max_length=16, default="conversing")`. Create
   `world/narrative/migrations/0013_dream_session_stage.py` with one
   `AddField` (dependency `0012_dream_dispatch`). No data migration.

2. **Lifecycle (`dream_session.py`).**
   - Constants `STAGE_CONVERSING = "conversing"`, `STAGE_FINALIZED =
     "finalized"`, `REASON_FINALIZED = "finalized"`.
   - `progress()`: `free_text_allowed = open_state and not at_cap and
     session.stage == STAGE_CONVERSING`.
   - `choices()`: `can_confirm = open_state and session.stage ==
     STAGE_FINALIZED`.
   - `begin_turn`: its two existing closed checks also refuse a finalized
     session (reason `REASON_FINALIZED`, same `DreamSessionClosedError`).
   - `settle_exchange`: when `exchange_number == MAX_EXCHANGES` set
     `locked.stage = STAGE_FINALIZED` and add `"stage"` to that save's
     `update_fields`.
   - New `finalize_session(session_id, owner_id, *, tick=0) -> DreamSession`:
     owner-scoped, inside `transaction.atomic()` on the locked row. Not open →
     `_reject("dream_session_closed", reason=REASON_CLOSED, ...)` and
     `DreamSessionClosedError`. `pending_submission_id` set →
     `_reject("dream_session_turn_conflict", reason=REASON_OUTSTANDING_TURN,
     ...)` and `DreamOutstandingTurnError`. Already finalized → return the row
     unchanged. Otherwise set the stage, increment `revision`, save
     `["stage", "revision", "updated_at"]` and
     `_announce("dream_session_finalized", {session_id, owner, completed,
     tick})`.
   - `resume_saved_session(..., reopen_conversation=False)`: after its
     existing reopen step, when `reopen_conversation` is true, the outcome is
     not confirmed, the stage is finalized and `completed_exchanges <
     MAX_EXCHANGES`, set the stage to conversing (increment `revision`, save,
     include `stage` in the existing `dream_session_resumed` event context).

3. **Later sleep (`dream_surface.enter_for_owner`).** Read
   `old = association(owner)` before the resume call and pass
   `reopen_conversation=(not old or old.get("sleep_id") != receipt.sleep_id)`
   to `lifecycle.resume_saved_session`.

4. **Surface.** Add
   `store_proposal(actor, proposal, *, thread_id) -> None` to
   `dream_surface.py`: writes `proposal =
   dream_proposal.normalize_proposal(proposal)`, `changes = None`,
   `thread_id`, `failure = False`.

5. **Service gating in `act`.** The action set gains `finalize`. Let
   `stage = current.stage`, `wish = surface.wish_state(actor)`,
   `supplied = direction if isinstance(direction, dict) else direction.strip()`.
   All refusals below emit the existing
   `log_warn("dream_surface_rejected", ...)` with `reason` equal to the code
   and write nothing. Player-facing messages are verbatim.

   | Condition | Code | Message |
   |---|---|---|
   | `say` or `finalize` while finalized | `dream_finalized` | 你已停止訴說，願望改由你親自修改。 |
   | `finalize` with `current.pending_submission_id` set | `dream_pending_response` | 女神還在回應，請稍候再停止訴說。 |
   | `confirm` while conversing | `not_finalized` | 請先停止訴說，再許下願望。 |
   | `draft` while conversing with `supplied` truthy | `direction_locked` | 訴說期間願望由女神修改；停止訴說後才能親自修改。 |
   | finalized form names another thread (decision 6) | `thread_locked` | 說出第一句話後，願望的歸屬便不能再改。 |
   | finalized form is not a valid proposal (decision 6) | `invalid_direction` | 願望的內容不完整或超出限制。 |
   | `confirm` with an empty summary | `empty_direction` | 請先讓願望成形，再許下願望。 |

   - `finalize`: `lifecycle.finalize_session(session_id, owner, tick=tick)`,
     then `lifecycle.preserve_draft(session_id, owner,
     surface.working_direction(actor), tick=tick)`, send the message
     `你停止了訴說。接下來由你親自修改願望。` with `actor.msg`, emit
     `log_info("dream_surface_action", ...)` and return
     `_result("success", "dream_finalize", <that message>)`.
   - Sixth exchange: in the settle transaction, after
     `surface.store_response`, when `completed + 1 >= lifecycle.MAX_EXCHANGES`
     call `lifecycle.preserve_draft(session_id, owner,
     surface.working_direction(actor), tick=tick)`.
   - The settle transaction's stale check also treats
     `latest.stage != lifecycle.STAGE_CONVERSING` as stale.

6. **Service: `draft`, `confirm`, `awaken` (replaces the payload logic).**
   - Finalized with `supplied` truthy:
     - dict: keep the existing shape checks (`check_json_safety`, keys within
       `DIRECTION_KEYS`, summary type and length, `MAX_DIRECTION_BYTES`).
       `form_thread = supplied.get("thread_id") or None`. It must equal
       `wish["thread_id"]`, or be `None` while `wish["thread_id"]` is not the
       `id` of any entry of `surface.offered_threads(actor)`; otherwise
       `thread_locked`. `proposal = dream_proposal.normalize_proposal(supplied)`;
       `ProposalEditError` → `invalid_direction`.
       `passthrough = {key: supplied[key] for key in ("effects", "revisions")
       if key in supplied}`.
     - text: keep the existing 2000-character check; `proposal` is the
       working proposal with `summary` replaced by the text;
       `form_thread = wish["thread_id"]`; `passthrough = {}`.
     - `surface.store_proposal(actor, proposal, thread_id=form_thread)`.
   - Otherwise `passthrough = {}` and nothing is stored.
   - `payload = {**surface.working_direction(actor), **passthrough}`.
   - `draft`: `lifecycle.preserve_draft(session_id, owner, payload,
     tick=tick)` with the existing `AuthoringError` refusal, then
     `surface.bump_revision_if_unchanged(actor, revision)`.
   - `confirm` (finalized only): empty `payload["summary"].strip()` →
     `empty_direction`. `draft = lifecycle.preserve_draft(...)`;
     `validation = validate_direction(draft.direction, owner_id=owner)`;
     invalid → `surface.bump_revision_if_unchanged(actor, revision)` and the
     existing `invalid_direction` refusal with the joined reasons. Valid →
     `lifecycle.confirm_session(session_id, owner, tick=tick)` (no
     `direction`), then the existing `authorize_departure_continuation` and
     `dispatch_status` on-commit delivery. Remove the service's
     `reviewed_version_matches` check and its `stale_requirements` refusal;
     the form the player submits is the shown version and `save_draft` stamps
     it. `lifecycle.confirm_session`'s own gate for a passed direction is not
     touched.
   - `awaken`: replace the "no draft yet and a non-empty summary" condition
     with: session open, stage conversing and
     `not dream_proposal.is_empty(wish["proposal"])` →
     `lifecycle.preserve_draft(session_id, owner,
     surface.working_direction(actor), tick=tick)`. A finalized session saves
     nothing here.
   - The shared tail message for a saved draft becomes `願望已替你收著。`
     (was `故事方向已存為私人草稿。`).

7. **Read model (`dream_state`).** Add keys: `stage` (`session.stage`),
   `proposal` (copy of the working proposal), `changes`, `thread_id`,
   `can_choose_thread` (open, conversing, not `thread_locked`, no pending
   response), `can_finalize` (open, conversing, no pending response),
   `can_edit` (open and finalized), `drafted` (`bool(session.draft_id)`).
   Change `can_confirm` to open and finalized. `can_input` follows
   `progress()`. Keep the schema-3 keys: `direction_parts` from
   `proposal["summary"]`, `requirements` from `proposal["requirements"]`,
   `requirement_version` and `draft_preferences` from the saved draft as
   today.

8. **Wire schema 4.** `DREAM_SCHEMA_VERSION = 4` in
   `web/webclient/presentation/dream.py` and `dream: 4` in
   `protocol/constants.js`. In `protocol/panels/dream.js` add the eight keys
   to the exact field list and validate:
   - `stage` is `"conversing"` or `"finalized"`;
   - `proposal` has exactly `summary`, `themes`, `atmosphere`, `participants`,
     `emphasis`, `exclusions`, `requirements`; `summary` is a string of at
     most 2000 code points; each list has at most 32 non-blank strings of at
     most 200 code points; `requirements` passes the existing row check with
     at most 8 rows;
   - `changes` is `null` or has exactly `summary` (`null`, `"formed"` or
     `"changed"`), `lists` (exactly the five list keys, each exactly `added`
     and `removed`, arrays of strings within the list bounds) and
     `requirements` (exactly `added` and `removed`, arrays of rows within the
     row bounds);
   - `thread_id` is `null` or a string of 1..128 characters;
   - `can_choose_thread`, `can_finalize`, `can_edit`, `drafted` are booleans;
   - invariants (throw on violation): `can_input` requires `stage ===
     "conversing"`; `can_finalize` and `can_choose_thread` require `open`,
     `stage === "conversing"` and `!pending`; `can_edit` and `can_confirm`
     require `open` and `stage === "finalized"`; `open && remaining === 0`
     requires `stage === "finalized"`.

9. **Web action.** `dream_actions.validate("finalize", payload)` requires
   exactly `session_id` and `revision`. Register `dream.finalize`. Echo
   `"dream.finalize": function () { return "dream finalize"; }` with its test
   case and manifest id; add it to the registry enumeration test.

10. **Tests.**
    - `world/narrative/tests/test_dream_session.py`: `finalize_session`
      (success, pending refusal, closed refusal, idempotent), `progress` /
      `choices` by stage, `settle_exchange` finalizing at six,
      `resume_saved_session(reopen_conversation=True)` with exchanges
      remaining and at the cap, and that
      `confirm_session(direction=...)` still refuses a stale version
      (existing test, kept).
    - `world/narrative/tests/test_dream_surface.py`: one test per scenario of
      the `dream-session-lifecycle` and `dream-authoring` deltas, through
      `service.act` and the web action adapter. Existing tests that confirm
      or submit a direction before the cap now call `finalize` (and
      `choose_thread` before the first `say` when they use a thread) first;
      `test_confirmation_requires_the_shown_requirement_version` and
      `test_an_edited_summary_cannot_freeze_the_shown_requirement_version`
      are replaced by the "An edited proposal confirms what was submitted"
      test. Keep every existing `covers_requirement` ID on a test that still
      establishes it.
    - `web/static/webclient/js/tests/protocol_dream.test.js`: schema 4
      accept case and one reject case per rule of decision 8.
    - Fixtures only: add the eight keys (conversing, empty proposal,
      `changes: null`, `thread_id: null`, flags consistent with decision 8)
      to the `state()` fixture of `web/webclient-app/tests/dream.test.js`, to
      `fixture()` of `stories/World/DreamPanel.stories.js`, and change the
      literal schema `3` to `4` in both test files. Do not change any
      component or assertion about component behaviour.
    - `web/webclient/presentation/tests/test_dream_artwork.py`: the version
      assertion follows the constant.

## Risks / Trade-offs

- [The unchanged browser panel sends a direction with every draft and
  confirms without finalizing] → both are refused with a reason until
  `dream-wish-stage-panel`; awaken, say and at-cap confirmation keep working.
- [Schema bumped twice in the batch] → each bump is one constant on each side
  plus fixtures; keeping the old panel untouched until its replacement costs
  less than porting it twice.
- [A confirmation refused by validation still stores the submitted form] →
  intended: the spec keeps an invalid direction as the unconfirmed draft.
