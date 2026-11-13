# Design: pure applier for dream proposal edits

## Context

- Source design: `docs/superpowers/specs/2026-11-13-dream-proposal-coediting-design.md`,
  sections "Edit Contract", "Application rules" and "Module boundary".
- Reference implementation (JavaScript, behaviour only):
  `docs/design/dream-proposal-coediting/DreamWishPrototype.stories.js`,
  functions `fieldText`, `storeField`, `applyEdits`, `diffProposal`.
- The direction store `world/narrative/authoring.py` owns the bounds
  `MAX_SUMMARY_CHARACTERS = 2000`, `MAX_LIST_ITEMS = 32`,
  `MAX_ITEM_CHARACTERS = 200`, `MAX_REQUIREMENTS = 8`,
  `MAX_REQUIREMENT_TEXT = 200` and
  `REQUIREMENT_KINDS = {"place", "new_character", "private_commission"}`.
  It imports Django models, so the pure module must not import it.
- An existing drift test (`world/narrative/tests/test_dream_dispatch.py`,
  search `REQUIREMENT_KINDS`) already pins a duplicated vocabulary equal to
  the store's. The same pattern is used here.

## Goals / Non-Goals

**Goals:** one importable, side-effect-free module with the exact API below
and its tests.

**Non-Goals:** calling the module from any other file; forbidden-content
checks on edit text (owned by `dream-collaborator-proposal-edits`); any
change to `authoring.py`, `dream_session.py`, `dream_surface.py`,
`server/dream_service.py`, `world/ai/`, prompts, the panel or the web client.

## Decisions

1. **File and imports.** Create `world/narrative/dream_proposal.py`. It
   imports only the standard library (`collections.abc`, `copy`, `json`,
   `typing`). No Django, no Evennia, no `world.*` import, no logging.

2. **Constants (verbatim).**

   ```python
   LIST_FIELDS = ("themes", "atmosphere", "participants", "emphasis", "exclusions")
   PATHS = ("summary", *LIST_FIELDS, "requirements")
   COMMANDS = ("str_replace", "insert", "create")
   REQUIREMENT_KINDS = ("place", "new_character", "private_commission")
   MAX_SUMMARY_CHARACTERS = 2000
   MAX_LIST_ITEMS = 32
   MAX_ITEM_CHARACTERS = 200
   MAX_REQUIREMENTS = 8
   MAX_REQUIREMENT_TEXT = 200
   MAX_EDITS = 16
   MAX_EDIT_TEXT_CHARACTERS = 6500
   MAX_PROPOSAL_BYTES = 16384
   MAX_CHANGES_BYTES = 8192
   ```

   `MAX_EDITS` and `MAX_EDIT_TEXT_CHARACTERS` are new: the source design gives
   no bound for the number of edits or for one edit parameter, and an
   unbounded model field is not acceptable. 6500 covers the largest legal
   field text (32 items of 200 characters plus separators = 6431).

   `MAX_PROPOSAL_BYTES` and `MAX_CHANGES_BYTES` are new aggregate budgets.
   The per-field bounds above admit about 35,600 code points, roughly 107 KiB
   of CJK text, which overflows both the direction store
   (`world/narrative/authoring.py::MAX_DIRECTION_BYTES = 65536`, enforced by
   `save_draft`) and the panel envelope
   (`web/webclient/presentation/protocol.py::MAX_CANONICAL_JSON_BYTES =
   65_536`). A byte is measured on the canonical JSON of the value:
   `len(json.dumps(value, separators=(",", ":"), ensure_ascii=False)
   .encode("utf-8"))`. 16 KiB of proposal plus 8 KiB of change report leave
   the rest of the worst legal dream panel — opening, scene, dialogue, up to
   32 thread labels, artwork, track and sleep — inside the envelope; the
   bound test in `dream-wish-stage-wire` pins that sum rather than trusting
   this arithmetic.

3. **Proposal shape (canonical).** A plain `dict` with exactly these keys:
   `summary: str`, the five `LIST_FIELDS` each `list[str]`, and
   `requirements: list[dict]` whose rows are exactly `{"kind": str, "text": str}`.

4. **Error type (verbatim).**

   ```python
   class ProposalEditError(ValueError):
       def __init__(self, code: str, index: int | None = None):
           self.code = code
           self.index = index
           super().__init__(f"{code} at edit {index}" if index is not None else code)
   ```

   Closed code set: `malformed_proposal`, `malformed_edit`, `too_many_edits`,
   `unknown_command`, `unknown_path`, `no_match`, `multiple_matches`,
   `insert_out_of_range`, `malformed_requirement`, `summary_too_long`,
   `too_many_items`, `item_too_long`, `too_many_requirements`,
   `requirement_too_long`, `proposal_too_large`, `changes_too_large`. Export
   them as the tuple `ERROR_CODES`.
   `index` is the zero-based position of the failing edit.

5. **Public functions (verbatim signatures).**

   ```python
   def empty_proposal() -> dict
   def normalize_proposal(value) -> dict
   def is_empty(proposal) -> bool
   def field_text(proposal, path: str) -> str
   def numbered_lines(proposal, path: str) -> list[dict]
   def apply_edits(proposal, edits) -> dict
   def diff(before, after) -> dict
   ```

   - `empty_proposal()`: `summary` is `""`, every list is `[]`.
   - `normalize_proposal(value)`: accepts any mapping; reads only the seven
     keys (missing key = empty; other keys ignored); `summary` must be `str`,
     each list field a `list` of `str`, `requirements` a `list` of mappings
     with exactly the keys `kind` and `text` (both `str`, `kind` in
     `REQUIREMENT_KINDS`, `text` non-empty after trimming); applies the same
     normalization and bounds as decision 7, including the aggregate
     `MAX_PROPOSAL_BYTES` check; raises
     `ProposalEditError("malformed_proposal")` for a wrong type or row and
     the bound's own code for a bound (`proposal_too_large` included, with
     `index=None`). Returns a new canonical dict.
   - `is_empty(proposal)`: true when the summary is `""` and all six
     collections are empty.
   - `field_text`: `summary` → the summary; a list field → items joined with
     `"\n"`; `requirements` → rows rendered `f"{kind}: {text}"` joined with
     `"\n"`. Unknown path raises `ProposalEditError("unknown_path")`.
   - `numbered_lines`: `[{"line": 1, "text": ...}, ...]` over
     `field_text(...).split("\n")`, numbering from 1; an empty field text
     returns `[]`.
   - `apply_edits`: decision 6.
   - `diff`: decision 8.

6. **`apply_edits(proposal, edits)`.**
   - `edits` must be a `list` or `tuple`, else `malformed_edit` with
     `index=None`; more than `MAX_EDITS` → `too_many_edits` with `index=None`.
   - Work on `copy.deepcopy(normalize_proposal(proposal))`; never mutate the
     argument; return the copy only when every edit succeeded.
   - Each edit must be a mapping whose `command` is a `str` in `COMMANDS`
     (else `unknown_command`) and whose `path` is a `str` in `PATHS` (else
     `unknown_path`). Its key set must be exactly:
     `str_replace` → `{command, path, old_str, new_str}`;
     `insert` → `{command, path, insert_line, insert_text}`;
     `create` → `{command, path, file_text}`. A missing or extra key, a
     non-`str` text parameter, a text parameter longer than
     `MAX_EDIT_TEXT_CHARACTERS`, an empty `old_str`, or an `insert_line` that
     is not an `int` (a `bool` is not an `int` here) → `malformed_edit`.
   - Let `text = field_text(working, path)`.
     - `create`: `text = file_text`.
     - `str_replace`: `count = text.count(old_str)`; `0` → `no_match`;
       `> 1` → `multiple_matches`; else `text = text.replace(old_str, new_str, 1)`.
     - `insert`: `lines = text.split("\n") if text else []`; `insert_line`
       outside `0..len(lines)` → `insert_out_of_range`; otherwise
       `lines.insert(insert_line, insert_text)` and re-join with `"\n"`.
       `insert_line` 0 puts the text first; `n` puts it after line `n`.
   - Store the text back with decision 7. Any error carries the edit's index.

7. **Storing a field (normalization and bounds), run after every edit.**
   - `summary`: `text.strip()`; longer than `MAX_SUMMARY_CHARACTERS` →
     `summary_too_long`. Lengths are `len(str)` (code points).
   - A list field: split on `"\n"`, strip each line, drop empty lines, drop
     later duplicates; any item longer than `MAX_ITEM_CHARACTERS` →
     `item_too_long`; more than `MAX_LIST_ITEMS` items → `too_many_items`.
   - `requirements`: split and strip the same way; each non-empty line is
     split at its first `":"` or `"："` (a Chinese-writing model often emits
     the full-width colon; the stored shape and the rendering stay canonical
     `kind: text`); no colon, a left part (stripped) not in
     `REQUIREMENT_KINDS`, or an empty right part (stripped) →
     `malformed_requirement`; text longer than `MAX_REQUIREMENT_TEXT` →
     `requirement_too_long`; drop later rows equal in both kind and text;
     more than `MAX_REQUIREMENTS` rows → `too_many_requirements`.
   - Bounds are checked after every edit, not only at the end. An edit set
     whose intermediate state is out of bounds is invalid. This follows the
     reference implementation (it re-stores the field after each edit) and
     keeps every intermediate state a valid proposal.
   - The aggregate check runs with the per-field bounds: after storing a
     field, the canonical bytes of the working proposal must not exceed
     `MAX_PROPOSAL_BYTES` (else `proposal_too_large`). The change report is a
     property of the whole set, so `apply_edits` ends by comparing the
     normalized input with the result and rejecting a report larger than
     `MAX_CHANGES_BYTES` (`changes_too_large`, `index=None`).

8. **`diff(before, after)` (verbatim result shape).**

   ```python
   {
       "summary": None | "formed" | "changed",
       "lists": {field: {"added": [...], "removed": [...]} for field in LIST_FIELDS},
       "requirements": {"added": [row, ...], "removed": [row, ...]},
   }
   ```

   `summary`: `None` when equal; `"formed"` when `before["summary"]` is `""`
   and `after["summary"]` is not; otherwise `"changed"`. `added` keeps the
   order of `after`, `removed` the order of `before`. Rows compare by both
   `kind` and `text`. All five list keys are always present. Returned rows
   are copies. `diff` itself is unbounded; `apply_edits` applies
   `MAX_CHANGES_BYTES` to its result.

9. **Tests.** `world/narrative/tests/test_dream_proposal.py`, classes based
   on `unittest.TestCase`, synthetic strings only (no shipped content). One
   test method per scenario of `specs/dream-proposal-editing/spec.md`. The
   scenario "Bounds match the direction store" imports
   `world.narrative.authoring` and asserts the five bounds are equal and
   `set(REQUIREMENT_KINDS) == authoring.REQUIREMENT_KINDS`. Expected values
   in tests are written out by hand, never produced by calling the module.
   Register the module in `.github/evennia-shards.json` in the shard that
   already holds `world.narrative.tests.test_dream_session`. Add the
   full-width-colon case, the aggregate proposal bound at and just over its
   byte limit, and the over-large change report to the same module; build
   the over-limit inputs from repeated synthetic characters so the test does
   not depend on shipped content.

## Risks / Trade-offs

- [Duplicated bounds can drift from the store] → the equality test in
  decision 9 fails on drift.
- [Checking bounds after every edit rejects a set that is only temporarily
  over a bound] → accepted; the model retries, and it keeps one rule.
- [The aggregate byte budget makes the per-field maxima unreachable together:
  a full 32-item CJK list plus a full summary exceeds 16 KiB] → intended; the
  panel and the draft store cannot carry both, so the model spreads a large
  wish over several turns and the invalid set goes through the existing
  retry.
