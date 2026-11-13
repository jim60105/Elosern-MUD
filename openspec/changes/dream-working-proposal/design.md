# Design: the dream session keeps a working proposal

## Context

- `world/narrative/dream_surface.py`: the association is the Evennia
  Attribute `actor.db.dream_surface` (a dict). `enter_for_owner` rebuilds it
  and keeps `scene`, `dialogue`, `direction` from the previous association of
  the same session (`retained`). `store_direction`, `store_response`,
  `store_failure`, `dream_state` read and write it. `dream_state` builds the
  thread list inline and publishes `direction_parts` and `requirements`.
- `server/dream_service.py::act`: `say` calls `lifecycle.begin_turn` then
  `surface.store_direction(actor, message)`; after generation it checks the
  stale conditions, settles and calls `surface.store_response`. `draft`,
  `confirm` and `awaken` build `payload` from the supplied `direction`, else
  the saved draft, else `{"kind": "new_story", "summary": saved["direction"]}`,
  and call `surface.store_direction(actor, summary)` after saving.
- `world/ai/dream.py::generate_dream_exchange` accepts `proposal` and
  `thread_label` and returns `DreamExchange.proposal` / `.changes`
  (`dream-collaborator-proposal-edits`).
- `world/narrative/dream_proposal.py` provides `empty_proposal`,
  `normalize_proposal`, `is_empty`, `LIST_FIELDS`.
- `web/webclient/actions/dream_actions.py` registers `dream.say`,
  `dream.draft`, `dream.confirm`, `dream.awaken`.

## Goals / Non-Goals

**Goals:** the working proposal in the association, `say` wired to it,
`choose_thread`, drafts sourced from it.

**Non-Goals:** stages, `finalize`, refusing supplied directions, any change to
how a supplied direction is validated, saved or confirmed, the panel wire
(stays schema 3 with the same keys), `DreamPanel.vue`, text commands
(`commands/dream.py` is not edited), `world/narrative/dream_session.py`,
`world/narrative/authoring.py`, `world/ai/`.

## Decisions

1. **Association keys.** Remove `direction` and `requirements`. Add:
   `proposal` (canonical dict from `dream_proposal`), `changes` (`None` or
   the dict from `dream_proposal.diff`), `thread_id` (`None` or `str`),
   `thread_locked` (`bool`). In `enter_for_owner` the new association takes
   them from `retained` with defaults `dream_proposal.empty_proposal()`,
   `None`, `None`, `False`.

2. **Surface functions (verbatim signatures), in `dream_surface.py`.**

   ```python
   def offered_threads(actor) -> list[dict]      # [{"id", "label"}], at most 32
   def wish_state(actor) -> dict | None          # {"proposal","changes","thread_id","thread_locked"}
   def working_direction(actor) -> dict
   def choose_thread(actor, thread_id) -> None
   def lock_thread(actor) -> None
   def store_response(actor, response) -> None   # changed
   ```

   - `offered_threads`: the loop now inline in `dream_state` (non-terminal
     threads accessible to the owner, newest first, label
     `factual_summary.strip()[:160] or "未命名的故事線"`, capped at 32), moved
     unchanged. `dream_state` calls it when the session is open.
   - `wish_state`: `None` when there is no association; otherwise the four
     values, each read with the defaults of decision 1 so an association
     written before this change still reads.
   - `working_direction`: `{"kind": "thread_direction" if thread_id else
     "new_story", "thread_id": thread_id, "summary": proposal["summary"],
     "requirements": [dict(row) ...]}` plus each of the five list fields that
     is non-empty.
   - `choose_thread`: writes `thread_id`; no validation (the service
     validates).
   - `lock_thread`: sets `thread_locked` to `True`.
   - `store_response`: writes `scene`, `dialogue`,
     `proposal = dream_proposal.normalize_proposal(response.proposal)`,
     `changes = response.changes`, `failure = False`.
   - Delete `store_direction`.

3. **`dream_state` keeps the schema-3 keys.** Read
   `proposal = wish_state(actor)["proposal"]`.
   `displayed_direction = (draft_direction or {}).get("summary", proposal["summary"])`.
   `requirements = (draft_direction or {}).get("requirements") or
   [dict(row) for row in proposal["requirements"]]`. No key is added or
   removed.

4. **Service: `say`.** After `lifecycle.begin_turn(...)`: call
   `surface.lock_thread(actor)`; do not store the message. Still inside that
   transaction capture `snapshot = surface.wish_state(actor)["proposal"]` and
   `thread_label` = the `label` of the entry of `surface.offered_threads(actor)`
   whose `id` equals the chosen `thread_id`, else `""`. Pass
   `proposal=snapshot, thread_label=thread_label` to
   `generate_dream_exchange`. In the settle transaction add one stale
   condition to the existing `if`: `surface.wish_state(actor)["proposal"] !=
   snapshot`. The stale and failure paths are otherwise unchanged; neither
   writes the proposal.

5. **Service: `choose_thread`.** `act` gains the keyword argument
   `thread_id=None` and the action name `choose_thread`. Inside the existing
   transaction, after the open-state check:
   - `surface.wish_state(actor)["thread_locked"]` → return
     `_result("rejected", "thread_locked", "說出第一句話後，願望的歸屬便不能再改。")`.
   - `thread_id is not None` and not the `id` of an entry of
     `surface.offered_threads(actor)` → return
     `_result("rejected", "unknown_thread", REASON_MESSAGES["unknown_thread"])`.
   - otherwise `surface.choose_thread(actor, thread_id)`,
     `surface.bump_revision_if_unchanged(actor, revision)`, emit
     `log_info("dream_surface_action", context={**boundary, "tick": tick})` and
     return `_result("success", "dream_choose_thread", "已選定願望的歸屬。")`.
   Each refusal emits the existing `log_warn("dream_surface_rejected", ...)`
   with `reason` equal to the result code. `choose_thread` returns before the
   `draft`/`confirm`/`awaken` branch and never reaches generation.

6. **Service: drafts read the working proposal.**
   - Replace the final fallback of `payload` (`{"kind": "new_story",
     "summary": saved.get("direction", "")}`) with
     `surface.working_direction(actor)`.
   - For `action == "draft"` with nothing supplied (`direction` is not a dict
     and is blank), `payload` is `surface.working_direction(actor)` even when
     a draft exists.
   - Remove the three `surface.store_direction(actor, summary)` calls.
   - Everything else in the `draft`, `confirm` and `awaken` branches is
     unchanged (supplied directions, the reviewed-version check, validation,
     the automatic draft on awakening when no draft exists and the summary is
     non-empty).

7. **Web action.** In `dream_actions.py`: `validate("choose_thread", payload)`
   requires exactly `session_id`, `revision`, `thread_id`; `thread_id` is
   `None` or a `str` of 1..128 characters, else
   `ProtocolValidationError("invalid dream thread")`; it returns
   `{"session_id", "revision", "thread_id"}`. Register `dream.choose_thread`
   in `register_actions`. The adapter needs no change (`**payload`).
   `command_echo.js`: add
   `"dream.choose_thread": function (payload) { return "dream thread " + (payload.thread_id === null ? "new" : payload.thread_id); }`
   with its case in `command_echo.test.js` and its id in
   `command_echo_coverage_manifest.json`. Add `"dream.choose_thread"` to the
   enumeration in `web/webclient/actions/tests/test_dispatcher/test_registry.py`.

8. **Tests** go in `world/narrative/tests/test_dream_surface.py`
   (`DreamSurfaceTests`, using its `enter`, `request`, `delivered` helpers and
   `FakeLLMClient` recorded responses with `edits`). One test per scenario of
   the delta spec. To assert what a request carried, read the recorded call
   from the fake client (`client.calls`) and parse the user message JSON; its
   `wish` and `thread` keys are defined by
   `dream-collaborator-proposal-edits`. Add a web-action test for
   `validate("choose_thread", ...)` accept and reject cases. Repair existing
   tests that read `association["direction"]`, call `store_direction` or
   expect the message as `direction_parts`. Synthetic strings only.

## Risks / Trade-offs

- [A direction supplied by the unchanged browser sheet is saved to the draft
  but not to the working proposal, so the model does not see hand edits] →
  interim of this batch; `dream-wish-stages` refuses supplied content while
  conversing and makes the working proposal the only source.
- [A bare `confirm` of a working proposal that carries requirements and has
  no saved draft is refused once and saved, as an unreviewed requirement set
  is today] → unchanged rule; `dream-wish-stages` replaces the flow.
