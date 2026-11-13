# Dream Proposal Co-Editing Design

Date: 2026-11-13

## Problem

Dream collaboration is meant to shape a story direction together with the
goddess. Today it does not:

- Each `say` stores the player's raw message as the direction
  (`server/dream_service.py`, `surface.store_direction(actor, message)`). The
  last thing the player said becomes the proposal.
- The model returns only `scene`, `dialogue`, `phase` and `requirements`. It
  never writes the proposal.
- The prompt carries the current message and the previously *confirmed*
  preferences. It carries neither this session's draft nor earlier exchanges,
  and no exchange content is persisted.

The 念頭 sheet already is a form (summary, thread, five tag lists, read-only
experience requirements), but the player fills it alone.

## Goal

The proposal is built step by step during the conversation. The player gives
instructions, the model edits the form, and the player hand-edits it once
before submitting.

## Out of Scope

- The saved and dispatched direction format (`DIRECTION_KEYS`), requirement
  version checks, dispatch work, the six-exchange budget and sleep settlement.
- Text-client editing of tags and requirements. The text client keeps its
  current ability to replace the summary only.
- Real tool-call round trips with the model.

## Decisions

| Topic | Decision |
|---|---|
| Fields the model edits | Summary, the five tag lists, experience requirements |
| Thread choice | Player only, chosen before the first exchange, then locked |
| Manual editing | Two stages; no return to conversation once finalized |
| Proposal display while conversing | Keepsake card with a changed-fields line, plus a read-only full view |
| Edit mechanism | Edit commands in the `str_replace` family, carried in the single JSON response |
| Departure | A short deterministic farewell beat and a UI transition before the exit flow |

## Player-Facing Wording

The proposal is a wish (願望) made to the goddess. The wording keeps to what
the scene contains: the player speaks, the goddess listens and adjusts the
wish. Nothing in the scene writes, so no term borrows from pens or paper.

| Concept | Wording |
|---|---|
| The proposal | 願望 |
| Conversing stage | 訴說 |
| Finalized stage | 斟酌 |
| Her change line | 女神為你改了 / 女神這次沒有更動願望 |
| Summary first written / changed | 成形 / 更動 |
| List item added / removed | 新添 / 劃去 |
| Read-only view | 願望全貌 |
| Finalize | 停止訴說，親自修改 |
| Edit form | 親自修改願望 |
| Save draft | 把願望收著 |
| Confirm | 許下這個願望 |

The prototype under `docs/design/dream-proposal-coediting/` (Storybook
`Design/DreamWish`) is the visual reference for this document.

## Stages

The server records one stage per session.

1. **Conversing.** The player speaks; the model answers with scene and
   dialogue and edits the proposal. The proposal is read-only for the player.
   Any player-supplied direction content is refused.
2. **Finalized.** Entered by the `finalize` action or when the sixth exchange
   completes. Free text is closed for good. The form is editable. Confirm,
   save draft and awaken remain.

One rule covers both entries: **manual editing is allowed exactly when free
text is closed.**

A saved session resumed on a later sleep returns to conversing if exchanges
remain, with the saved draft as the starting proposal. "No return" holds
within one night's dream only.

### Thread choice

After the opening narration and before the first message, the player picks
"a new story" (default) or one of the offered threads. The first `say` locks
the choice for the session, including later resumes. The chosen thread's
player-visible summary label enters the prompt.

If the chosen thread has ended by confirmation time, existing validation
refuses it. The finalized form then allows one change only: back to "a new
story".

## Working Proposal

The dream surface association holds a structured working proposal instead of
one direction string:

- `summary`, `themes`, `atmosphere`, `participants`, `emphasis`,
  `exclusions`, `requirements`
- `thread_id` (or none)
- `changes`: what the last settled exchange changed. For each changed list
  field, the items added and the items removed; for the summary, whether it
  first took shape or was changed

It is the model's only memory of the collaboration. Each prompt includes the
current proposal with line numbers. No transcript is stored.

A new session starts with an empty proposal. The previously confirmed
preferences stay in the prompt as background, as today.

## Edit Contract

The model response gains `edits`, which replaces the whole-list
`requirements` field:

```json
{
  "scene": "...",
  "dialogue": "...",
  "phase": "...",
  "edits": [
    {"command": "str_replace", "path": "summary",
     "old_str": "...", "new_str": "..."},
    {"command": "insert", "path": "themes", "insert_line": 2, "insert_text": "..."},
    {"command": "create", "path": "atmosphere", "file_text": "..."}
  ]
}
```

Each proposal field is treated as a small text file.

| Command | Parameters | Meaning |
|---|---|---|
| `str_replace` | `path`, `old_str`, `new_str` | `old_str` must occur exactly once in the field |
| `insert` | `path`, `insert_line`, `insert_text` | Insert after the given line; `0` is the start |
| `create` | `path`, `file_text` | Overwrite the whole field |

`path` is one of the seven field names. Tag fields hold one item per line.
`requirements` holds one row per line as `kind: text`, where `kind` is one of
the existing requirement kinds.

The shape follows the search-and-replace editing convention shared by common
agent edit tools, so it does not depend on one vendor's training. It was
chosen over a line-based patch format because a Chinese summary is often one
long line, where a line diff degenerates into a full rewrite. It was chosen
over index-based JSON Patch because list indices shift across sequential
operations.

### Application rules

- Edits apply in order to a copy. All succeed or none do.
- A `str_replace` with zero or multiple matches, an unknown `path` or
  command, a malformed requirement line, or a result outside the existing
  bounds (summary 2000 characters, 32 items per tag list, 8 requirements,
  per-item text limits) makes the response invalid.
- Edit text passes the same forbidden-content validators as dialogue.
- After application, list fields are normalized: lines trimmed, blank lines
  dropped, duplicates removed.
- An empty `edits` array is valid; the change line reads "no change this
  turn".
- The server computes `changes` by comparing the proposal before and after.
  Removed items are named explicitly, because a removal leaves nothing on
  screen to notice.

An invalid response goes through the existing validation retry. When retries
are exhausted the turn fails, consumes no exchange and leaves the proposal
unchanged.

### Module boundary

The applier is a pure module (working name `world/narrative/dream_proposal.py`):
old proposal plus edits in; new proposal plus its changes, or one concrete
error, out. It touches no database and no session. This keeps it testable in
isolation and keeps weight off `dream_session.py`.

## Server Actions

| Action | Available | Effect |
|---|---|---|
| `choose_thread` (new) | Before the first `say` | Sets new story or one accessible thread |
| `say` | Conversing | Runs one exchange and applies its edits; no longer stores the message as direction |
| `finalize` (new) | Conversing, no pending response | Closes free text, saves the proposal as a draft and stamps the requirement version |
| `draft` | Any open stage | Conversing: saves the working proposal, refuses supplied content. Finalized: saves the submitted form |
| `confirm` | Finalized | Unchanged validation and submission |
| `awaken` | Always | Unchanged |

The stage flag lives on `DreamSession` (one new field and migration), because
the session lifecycle already owns whether free text is allowed.

Because `finalize` stamps the requirement version, the "not yet reviewed, save
first" notice on requirements is no longer needed.

The panel state gains the stage, the structured proposal, `changes`,
the thread choice and the flags for choosing a thread, finalizing and
editing. The client protocol validator is updated to match.

## Browser Surface

The dream is a slow, text-first scene played with keyboard or mouse. Nothing
is time-critical, so the design optimizes for noticing what the model changed
and for not losing work to an irreversible step. The points below come from
task analysis of this flow, not from playtesting.

### Thread choice

- The choice sits inline above the reply bar, with "a new story" preselected.
  The player can simply start typing; the common case costs no extra step.
- One line states that the choice locks once the first message is sent.
- With no thread to offer, the choice is not shown at all.
- After the lock, the keepsake card's existing 歸屬 line is the persistent
  indicator.

### Keepsake card

The four numbered rows keep their positions across stages, so keyboard habits
carry over. Only the labels change.

| Row | Conversing | Finalized |
|---|---|---|
| 1 | View the whole proposal (read-only) | Edit the proposal |
| 2 | End the conversation and finalize | Carry this proposal and wake |
| 3 | Save draft, keep dreaming | Save draft |
| ✕ | Awaken | Awaken |

Row 2 never chains: finalize opens a confirmation whose default focus is
"stay", so a repeated key press cannot finalize and submit in one motion.

The change line under the summary excerpt:

- updates only after the goddess's line has finished revealing, so it does
  not compete with the text the player is reading;
- stays until the next exchange settles, and is announced through the live
  region;
- names fields in words with a glyph, not by color alone;
- reads "no change this turn" for an empty edit set.

### Read-only view

- Titled as read-only, with one line saying the goddess holds the pen while
  the conversation lasts and the player edits after finalizing.
- Fields render as plain text, not as disabled inputs, which read as broken
  and lose contrast.
- Changed fields are marked. Added list items carry a marker; removed items
  are listed by name under their field.
- It offers the finalize action, so the player need not go back to the card.

### Finalize

- The confirmation states that the conversation cannot be resumed and how
  many exchanges would be given up. Default focus is "stay".
- At the cap the end bar offers finalize directly, with no confirmation,
  since no exchange remains to lose.
- The existing 念頭 sheet opens in editable mode. Summary and tags edit as
  today. Requirement rows can be added (kind chosen from the closed set),
  edited and removed, with a count against the limit and errors shown on the
  offending row. The thread is shown, not editable, except for the fallback
  above.

### Awaken check

The check's copy changes with the new model: the current proposal, not the
last message, is what gets kept as a draft. Unsaved manual edits in the
finalized stage are still warned about.

The DreamPanel Storybook story gains a state for each of the above, and the
component manifest is updated.

## Farewell

When the player confirms or awakens, the dream plays a short closing beat
before the existing exit flow.

- The closing line is **server-authored fixed text, not generated**. Departure
  must work with model services unavailable. Its wording is keyed by outcome
  (confirmed, draft kept, left with nothing) and by the existing ending phase
  of the dream track.
- The departure commits on the server first, as today. The farewell is
  presentation only and gates no committed state; sleep continuation proceeds
  regardless.
- In the browser, the panel enters a `farewell` state: the goddess's closing
  line types into the message band like any other beat and waits for Enter
  or a click, with the key hint reading "wake". The stage then blooms and
  fades and the panel releases to the exit flow. Under reduced motion the
  transition is omitted and the line is shown in full.
- The closing line also reaches the message log, so a player who skips it can
  read it afterwards.
- All dream controls are inert during the farewell.
- A reconnect during the farewell does not replay it; the client shows the
  waking surface.
- The text client prints the same closing line in place of the current
  ending sentence.

## Text Commands

- New: `dream thread [number|new]`, `dream finalize`.
- `dream` shows the full proposal and the last changes, including removed items.
- `dream say` output ends with a one-line change summary.
- `dream draft <summary>` and `dream confirm <summary>` keep their present
  meaning and work only after finalize.

## Error Handling

| Situation | Result |
|---|---|
| Invalid edits | Retry; on exhaustion the turn does not count and the proposal is unchanged; the existing "no answer" notice shows |
| Supplied direction content while conversing | Refused with a reason, no write |
| `choose_thread` after the first `say` | Refused, no write |
| `finalize` while a response is pending | Refused, no write |
| `confirm` before finalize | Refused, no write |
| Response arrives after finalize or awaken | Existing stale-response path; edits are not applied |
| Reconnect | Stage, proposal, last changes and thread are restored from the server |

## Testing

Tests assert logic only, add no game data and assert no wall-clock time.

- **Applier:** each command's success path, match-count errors, unknown path,
  malformed requirement line, atomic rollback, normalization, bounds.
- **Prompt:** the current proposal and chosen thread label are included; no
  transcript is.
- **Service:** a message never becomes the direction; stage gating of every
  action; thread lock; resume returns to conversing; a confirmed direction has
  the same stored shape as today; a stale response applies no edits.
- **Farewell:** each outcome selects its line with no model call; departure
  commits independently of the presentation.
- **Frontend:** change line timing and wording, removed items shown,
  read-only view, row labels per stage, finalize confirmation focus, edit
  gating, thread choice, farewell state, reduced motion, protocol validator.

## Affected Specifications

`dream-session-lifecycle`, `dream-authoring`, `dream-sleep-surface`,
`webclient-dream-stage`, `dream-explicit-presentation`.
