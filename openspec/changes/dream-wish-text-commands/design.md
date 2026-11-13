# Design: text commands for the dream wish

## Context

- `commands/dream.py`: `_USAGE`, `render_state(state)`, `CmdDream.func`.
  `func` parses `action, _, text = args.partition(" ")`, routes `enter` /
  `decline` to `answer_sleep_dream`, and routes `say`, `draft`, `confirm`,
  `awaken` to `server.dream_service.act(...)`, printing the refusal message
  and then `render_state(current)` when the dream is still open.
- After `dream-wish-stage-wire`, `dream_state` carries `stage`, `proposal`
  (`summary`, five lists, `requirements`), `changes` (`None` or
  `{"summary": None|"formed"|"changed", "lists": {field: {"added",
  "removed"}}, "requirements": {"added", "removed"}}`), `thread_id`,
  `thread_choices` (`[{"id", "label"}]`), `can_choose_thread`, `can_input`,
  `can_finalize`, `can_edit`, `can_confirm`, `can_draft`, and
  `act` accepts the actions `choose_thread` (keyword `thread_id`) and
  `finalize`.
- `tests/test_command_docs.py` holds the syntax manifest entry `"dream"` and
  checks it against `docs/game/command-reference.md`.

## Goals / Non-Goals

**Goals:** the two new sub-commands, the new state rendering, the change
summary after `say`, matching documents.

**Non-Goals:** any change under `server/`, `world/` (except the test module)
or `web/`; text editing of lists or requirement rows other than the existing
JSON form; the farewell line (`dream-farewell-beat`); the web paragraph of
`docs/game/command-reference.md` that describes the browser stage
(`dream-wish-stage-panel` owns it).

## Decisions

1. **Usage (verbatim).**

   ```python
   _USAGE = (
       "用法：dream [enter|decline|thread [編號|new]|say <文字>|finalize|"
       "draft [願望]|confirm [願望]|awaken]"
   )
   ```

   Manifest syntax string in `tests/test_command_docs.py` and the 語法 row of
   `docs/game/command-reference.md`:
   `dream、dream enter、dream decline、dream thread [編號|new]、dream say <文字>、dream finalize、dream draft [願望]、dream confirm [願望]、dream awaken`.

2. **Routing in `CmdDream.func`.** The accepted action set becomes
   `{"thread", "say", "finalize", "draft", "confirm", "awaken"}`; `awaken`
   and `finalize` with extra text print `_USAGE`.
   - `thread` with no text: print `render_threads(state)` and return (no
     `act` call).
   - `thread <arg>`: `new` (case-insensitive) → `thread_id=None`; a decimal
     number `n` with `1 <= n <= len(state["thread_choices"])` → that entry's
     `id`; a string equal to an offered `id` → that `id`; anything else →
     print `找不到這條故事線。輸入 dream thread 查看可選的編號。` and return
     without calling `act`. Then
     `act(caller, "choose_thread", session_id=..., revision=...,
     thread_id=<value>, session=self.session)`.
   - `finalize`: `act(caller, "finalize", session_id=..., revision=...,
     session=self.session)`.
   - The completion callback is unchanged except that after a `say` whose
     result outcome is `success` it prints
     `render_state(current, changes_last=True)`.

3. **Renderers (verbatim signatures), all pure, in `commands/dream.py`.**

   ```python
   def render_changes(changes) -> str
   def render_wish(state) -> str
   def render_threads(state) -> str
   def render_state(state, *, changes_last=False) -> str
   ```

   Labels: lists `themes` 主題, `atmosphere` 氛圍, `participants` 人物,
   `emphasis` 描寫, `exclusions` 避開; requirement kinds `place` 指定的地點,
   `new_character` 需要的新角色, `private_commission` 私人委託.
   - `render_changes`: `None` → `""`. No change at all →
     `女神這次沒有更動願望。`. Otherwise `女神為你改了：` followed by parts
     joined with `；` and a final `。`: `願望成形` or `願望更動` for the
     summary; for each list or the requirements (label `需求`) with any change
     `<label>` + `新添「a」「b」` when items were added + `劃去「c」` when items
     were removed (a requirement row prints its text). One line, no newline.
   - `render_wish`: one line per item, skipping empty lists:
     `此刻的願望：<summary>` (or `此刻的願望：尚未成形。`), `<label>：a、b` for
     each non-empty list, `這個願望需要：<kind label>「text」、…` when rows
     exist, and `歸屬：一段新的故事` / `歸屬：延續：<label>` (the offered
     entry whose `id` equals `thread_id`) / `歸屬：先前選定的故事線` (a
     `thread_id` that is no longer offered).
   - `render_threads`: `0 或 new：一段新的故事` then `<n>：<label>` per
     offered thread (numbering from 1); when `can_choose_thread` is false the
     only line is `願望的歸屬已經定下：` + the same thread text as
     `render_wish`.
   - `render_state`: `None` → the existing no-dream line. Otherwise, in this
     order and skipping empty parts: `opening`, `scene`, `dialogue`,
     `剩餘訴說次數：<remaining>。`, the pending line
     `女神正在回應，你仍可把願望收著或醒來。`, the failure line
     `回應暫時無法生成，這次不算數；你仍可把願望收著或醒來。`,
     `render_wish(state)`, `render_changes(state["changes"])` (only while
     `stage == "conversing"`), then hints: when `can_choose_thread` and
     threads are offered `dream thread [編號|new]：決定願望的歸屬（說出第一句話後便不能再改）`;
     when `can_input` `dream say <想說的話>`; when `can_finalize`
     `dream finalize：停止訴說，親自修改願望`; when `can_edit`
     `dream draft [願望]：把願望收著 ／ dream confirm [願望]：許下這個願望`
     and `願望也可使用 JSON，指定各欄位。`; when `can_draft` and not `can_edit`
     `dream draft：把願望收著`; last `state["ending"] or "dream awaken"`.
     With `changes_last=True` the `render_changes` line is omitted from its
     place and appended as the final line (when it is non-empty).
   - The renderers read none of `direction_parts`, `draft_preferences`,
     `requirements`, `requirement_version`.

4. **Documents.** `docs/game/command-reference.md`, section `### dream`:
   update the 語法 row (decision 1) and rewrite the 說明 row and the two
   paragraphs that start `故事方向也可使用 JSON` and `確認時，文字與網頁客戶端`
   so that they state these facts and no retired one:
   - the wish is edited by the goddess during the conversation; a message
     never becomes the wish by itself; `dream` shows the whole wish, its
     thread and the last change including removed items;
   - `dream thread [編號|new]` works until the first `dream say` is accepted;
   - `dream finalize` stops the conversation for this dream, is refused while
     a response is pending, and happens automatically after the sixth
     exchange; a later sleep returns to the conversation when exchanges
     remain;
   - `dream draft` (no argument) works in both stages; `dream draft <文字>`,
     `dream confirm [文字]` and the JSON form work only after finalize; text
     replaces the summary only; the JSON form carries the whole form and may
     not change the thread except to a new story when the chosen thread has
     ended;
   - confirmation saves and confirms what was submitted; remove every
     statement about `requirement_version`, 已檢視的版本, 尚未檢視 and 記下念頭.
   Leave the paragraph that starts `網頁客戶端的等待畫面` unchanged.
   `docs/game/commands.md`: update the `dream` table row and the two prose
   paragraphs that describe `dream say/draft/confirm` to the same facts.

5. **Tests** in `world/narrative/tests/test_dream_surface.py`
   (`DreamSurfaceTests`, driving `CmdDream` as the existing text tests do):
   one test per scenario of the delta spec except "Documentation parity",
   which is the existing `tests.test_command_docs` module. Renderer tests
   assert structure with synthetic items (for example that an added and a
   removed synthetic item both occur in `render_changes` output and that the
   no-change output differs from the changed one); they do not assert the
   shipped wording. Update existing tests that assert retired text of
   `render_state` (`尚未檢視`, `已檢視的版本`).

## Risks / Trade-offs

- [The text client cannot edit lists or requirement rows except through the
  JSON form] → as the source design states ("Out of Scope").
- [Wording is not machine-checked] → human review named in proposal.md.
