# Design: the dream collaborator returns proposal edits

## Context

- `world/ai/dream.py` today: `DREAM_EXCHANGE_SCHEMA` (`scene`, `dialogue`,
  `phase`, optional `requirements`), `DreamExchange(scene, dialogue, phase,
  completed, mode, requirements=())`, `_requirement_rows`,
  `build_dream_prompt` (payload keys `player_message`,
  `requirement_contract`, optional `preferences`, `adventure_summary`),
  `generate_dream_exchange`, per-call validators through
  `ChatRequestDescriptor.semantic_validators` (`_make_phase_validator`).
- The guardrail (`world/ai/guardrail.py`, `_validate_output`) collects error
  strings from the JSON schema, the layer validators and the per-call
  validators; any error retries up to the profile budget, then degrades to
  the fallback, which `generate_dream_exchange` maps to `None`.
- The schema is also sent to providers as `response_format` when the profile
  supports it (`world/ai/client.py`), so it stays a flat object schema with no
  `oneOf`.
- `world/narrative/dream_proposal.py` (from `dream-proposal-edit-applier`)
  provides `empty_proposal`, `normalize_proposal`, `numbered_lines`,
  `apply_edits`, `diff`, `ProposalEditError`, `PATHS`, `COMMANDS`,
  `REQUIREMENT_KINDS` and the bounds.
- `world/narrative/dream_surface.py::store_response` copies
  `response.requirements` into the association key `requirements`.
- `server/dream_service.py::act` calls `generate_dream_exchange(tap,
  completed=..., player_message=..., brief=...)`. It is not changed here.

## Goals / Non-Goals

**Goals:** the model contract, prompt and validation for edits; the result
object; keeping the surface's requirement rows fed until the session stores a
working proposal.

**Non-Goals:** storing a working proposal, passing one from the service,
thread choice, stages, any panel or web-client change, text commands. Do not
edit `server/dream_service.py`, `world/narrative/dream_session.py`,
`world/narrative/authoring.py` or anything under `web/`.

## Decisions

1. **Imports.** `world/ai/dream.py` adds
   `from world.narrative import dream_proposal`. The module is pure, so the
   rule "no module under `world/ai/` applies a state change" holds. Delete the
   local `REQUIREMENT_KINDS`, `MAX_REQUIREMENTS`, `MAX_REQUIREMENT_TEXT` and
   `_requirement_rows`; where a test or caller needs them use
   `dream_proposal.REQUIREMENT_KINDS` and the `dream_proposal` bounds.

2. **Schema (verbatim replacement of the `requirements` property).**
   `required` stays `["scene", "dialogue", "phase"]`; `edits` is optional and
   an absent `edits` means no edits.

   ```python
   "edits": {
       "type": "array",
       "maxItems": dream_proposal.MAX_EDITS,
       "items": {
           "type": "object",
           "required": ["command", "path"],
           "additionalProperties": False,
           "properties": {
               "command": {"type": "string", "enum": list(dream_proposal.COMMANDS)},
               "path": {"type": "string", "enum": list(dream_proposal.PATHS)},
               "old_str": {"type": "string", "minLength": 1,
                           "maxLength": dream_proposal.MAX_EDIT_TEXT_CHARACTERS},
               "new_str": {"type": "string",
                           "maxLength": dream_proposal.MAX_EDIT_TEXT_CHARACTERS},
               "insert_line": {"type": "integer", "minimum": 0,
                               "maximum": dream_proposal.MAX_LIST_ITEMS},
               "insert_text": {"type": "string", "minLength": 1,
                               "maxLength": dream_proposal.MAX_EDIT_TEXT_CHARACTERS},
               "file_text": {"type": "string",
                             "maxLength": dream_proposal.MAX_EDIT_TEXT_CHARACTERS},
           },
       },
   },
   ```

   Which parameters belong to which command is enforced by the applier
   (`malformed_edit`), not by the schema.

3. **`DreamExchange` (verbatim).**

   ```python
   @dataclass(frozen=True)
   class DreamExchange:
       scene: str
       dialogue: str
       phase: str
       completed: int
       mode: str
       proposal: dict = field(default_factory=dream_proposal.empty_proposal)
       changes: dict = field(
           default_factory=lambda: dream_proposal.diff(
               dream_proposal.empty_proposal(), dream_proposal.empty_proposal()
           )
       )
   ```

   `requirements` is removed. Positional construction with five arguments
   (used by existing tests) keeps working.

4. **Per-call validator `edits_apply`.** Add
   `_make_edits_validator(proposal)` returning a validator that reads
   `parsed.get("edits") or []`, calls `dream_proposal.apply_edits(proposal,
   edits)` and returns `[]` on success or
   `[f"dream edits do not apply: {error.code} at edit {error.index}"]` on
   `ProposalEditError`. A non-list `edits` returns
   `["dream edits must be a list"]`. Register it in `extra_validators` next
   to `phase_fidelity` in `generate_dream_exchange`.

5. **Forbidden content covers edit text.** Add
   `_edit_text(parsed) -> str`: the `new_str`, `insert_text` and `file_text`
   string values of every edit mapping, joined with `"\n"` (`old_str` is text
   that already exists and is not scanned). `_validate_no_forbidden_markers`
   scans `(_response_text(parsed) + "\n" + _edit_text(parsed)).casefold()`.
   `_validate_has_cjk`, the non-empty validators and the summary-question
   validator keep reading scene and dialogue only.

6. **Prompt payload.** `build_dream_prompt` gains keyword arguments
   `proposal=None` and `thread_label=""`. The user payload keys become
   exactly: `player_message`, `wish`, `edit_contract`, and when present
   `thread`, `preferences`, `adventure_summary`. `requirement_contract` is
   removed.
   - `wish`: `{path: dream_proposal.numbered_lines(p, path) for path in
     dream_proposal.PATHS}` where `p = dream_proposal.normalize_proposal(
     proposal or {})`.
   - `edit_contract`:
     `{"paths": list(PATHS), "commands": list(COMMANDS),
     "requirement_kinds": list(REQUIREMENT_KINDS),
     "max_edits": MAX_EDITS, "max_summary": MAX_SUMMARY_CHARACTERS,
     "max_list_items": MAX_LIST_ITEMS, "max_item": MAX_ITEM_CHARACTERS,
     "max_requirements": MAX_REQUIREMENTS,
     "max_requirement_text": MAX_REQUIREMENT_TEXT,
     "max_proposal_bytes": MAX_PROPOSAL_BYTES,
     "max_report_bytes": MAX_CHANGES_BYTES}` (all from `dream_proposal`).
   - `thread`: `{"label": _cap_string(str(thread_label).strip(), 160)}`, only
     when the stripped label is non-empty.
   Serialization stays `json.dumps(payload, sort_keys=True,
   ensure_ascii=False)`.

7. **`generate_dream_exchange`.** New keyword arguments `proposal=None` and
   `thread_label=""`. Compute `current =
   dream_proposal.normalize_proposal(proposal or {})` once before building the
   prompt; pass it to `build_dream_prompt` and `_make_edits_validator`. After
   a successful guarded call: `after = dream_proposal.apply_edits(current,
   parsed.get("edits") or [])` and return `DreamExchange(..., proposal=after,
   changes=dream_proposal.diff(current, after))`. The validator already
   proved the set applies, so this second application cannot raise for the
   accepted text. The `dream_exchange_generated` log context is unchanged.

8. **System prompt.** In `prompts/dream.yaml`, replace the two lines that
   start `你只能輸出一個 JSON 物件` and `{"scene": ...}` with the block below,
   and replace every `協商故事方向` / `協商創作方向` / `協商出的方向` with the
   wish wording shown. Placeholders (`{phase}`, `{climax_phase}`,
   `{exchange_number}`, `{remaining}`, `{mode}`) are unchanged. Literal braces
   in the example are written the way the existing example line writes them.

   ```text
   玩家正在向你訴說一個願望：醒來之後希望故事朝哪裡發展。使用者訊息的 wish 是這個願望目前的全貌，分成 summary、themes、atmosphere、participants、emphasis、exclusions、requirements 七個欄位，每個欄位都是一份小文字檔，逐行附上行號；行號只供你指位置，不屬於文字內容。
   你只能輸出一個 JSON 物件，欄位為 scene、dialogue、phase，以及用來修改願望的 edits 陣列：
   {"scene": "露骨場景散文", "dialogue": "對談者台詞", "phase": "興奮階段", "edits": [{"command": "create", "path": "summary", "file_text": "…"}]}
   edits 依序套用，可用的指令只有三種：str_replace（path、old_str、new_str；old_str 必須在該欄位中恰好出現一次）、insert（path、insert_line、insert_text；插在指定行號之後，0 表示最前面）、create（path、file_text；整個欄位改寫）。
   themes、atmosphere、participants、emphasis、exclusions 每行一個項目；requirements 每行一筆，格式為「種類: 內容」，種類只能是 edit_contract.requirement_kinds 列出的值。只在玩家這次說的話需要時才修改願望；不需要修改時 edits 給空陣列。玩家的原話本身不是願望，願望只由你的 edits 寫成。
   若使用者訊息帶有 thread，代表這個願望屬於那條既有的故事線，願望內容要與它相容。
   ```

   The sentences about `summary` mode read `summary 表示以對話總結這次談出的願望且不得提出任何新問題`, and the last line reads
   `場景中的台詞與敘述只能談願望的內容，不得宣稱…` with the rest of that line
   unchanged. This wording is human-reviewed (see proposal.md).

9. **Bridge in the surface.** In
   `world/narrative/dream_surface.py::store_response` replace the
   `value["requirements"] = [...]` statement with
   `value["requirements"] = [dict(row) for row in response.proposal["requirements"]]`.
   Nothing else in that file changes.

10. **Tests.**
    - `world/ai/tests/test_dream_presentation.py`: update
      `test_user_payload_carries_only_permitted_context` to the key set of
      decision 6; add tests for every scenario of the delta spec (numbered
      lines, thread label present and absent, no transcript keys, valid edits,
      no edits, invalid-then-valid retry with `FakeLLMClient` returning two
      recorded responses and asserting the call count, exhausted retries →
      `None`, forbidden marker inside `new_str`, legacy `requirements` field
      rejected). Use synthetic strings. Decorate the prompt tests with the
      existing ID
      `dream-explicit-presentation::collaborator-has-separate-spoiler-filtered-capability-access`.
    - `world/narrative/tests/test_dream_dispatch.py`: the drift test near
      `collaborator.REQUIREMENT_KINDS` now compares
      `world.narrative.dream_proposal` constants with `authoring`.
    - `world/narrative/tests/test_dream_surface.py`: in
      `test_collaborator_requirements_reach_the_surface_and_the_text_line`
      replace the recorded `"requirements": [...]` field with
      `"edits": [{"command": "create", "path": "requirements", "file_text":
      "place: 南門\nnew_character: 一個女孩\nprivate_commission: 帶她找媽媽"}]`;
      the assertions stay. Fix any other test in that module that builds a
      response with `requirements`.
    - `web/tests/browser/seed/dream_fixture.py`: if it records a response
      with `requirements`, convert it the same way.

## Risks / Trade-offs

- [Until `dream-working-proposal` lands the model edits an empty proposal on
  every turn] → intended interim; the surface shows the same requirement rows
  it showed before, and nothing else reads the result.
- [A model that ignores line-number metadata may copy numbers into text] →
  numbers are separate JSON fields, never inside the text.
