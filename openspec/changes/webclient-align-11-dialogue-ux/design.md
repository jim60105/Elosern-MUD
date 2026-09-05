# Design: webclient-align-11-dialogue-ux

## Context

`webclient-align-08-dialogue-surface` built the dialogue surface as one derived view model
(`stores/dialogue-view.js`) presented twice: the narrative caption's dialogue variant and the
dock's `dialogue.root` form. In play this is broken:

- Entering dialogue mode tears the dock stack down to a single `對話選項` tab. Every other dock
  affordance disappears, the pane duplicates the caption's pick rows exactly, and the only
  in-surface actions are the picks themselves — there is no exit row. The player's only way
  back to a normal dock is leaving the room (the `settle_movement` clear seam).
- The caption is a `max-height:32vh` scroll card. Picks stack below the reply, so a busy panel
  pushes the speaker's line out of view; clicking lower picks scrolls the conversation away.
  The panel spec allows up to sixteen choices.
- `.narrative-head` is `position:sticky` INSIDE the scroll viewport, so stream content renders
  in the strip between the card border and the head — visible bleed-through above the sticky bar.

Server facts (verified): `DIALOGUE_MAX_CHOICES = MAX_SCRIPTED_KEYWORDS = 16` in
`web/webclient/presentation/dialogue.py` (the UMD mirror `protocol.js` carries
`DIALOGUE_MAX_CHOICES = 16`); the session's ONLY-writer list in
`openspec/specs/webclient-dialogue-session/spec.md` has no explicit-exit seam; the mode-root
teardown (`stores/elosern.js` `MODE_ROOT_DESCRIPTORS`) maps `dialogue` → `dialogue.root`;
`dialogueFormPresented()` gates the digit-pick remap and the ArrowRight command-line borrow.

## Goals / Non-Goals

**Goals:**

- One dialogue surface: the narrative caption owns the exchange (box + picks + freeform + exit).
- An explicit, deterministic way to end a conversation that does not require walking away.
- The dock never hijacks itself: while mode is `dialogue` it keeps its ordinary exploration
  root, so movement/interact/suggestions stay one keystroke away and "walking away" remains the
  implicit exit.
- The current exchange always fits the caption: at most four picks (matching the 1–4 digit
  legend), compacted into a two-column grid, with the head outside the scroll viewport.

**Non-Goals:**

- No change to `db.dialogue_session` shape, affinity, or the scripted tables.
- No new player text command (`talk` unchanged; the exit is a UI action only).
- No change to the interact-target keyword list (still bounded by `MAX_SCRIPTED_KEYWORDS = 16`
  in the exploration panel — overflow keywords stay reachable there).
- No server-side "dialogue preference" or per-NPC exit prose.
- No party-drawer capability change: `PartyDrawer.vue` keeps its own mode gates untouched
  (Rubber-duck scope decision) — this change's "ordinary affordances stay usable" claim is
  scoped to the action dock and its router lifecycle, not every visible surface.

## Decisions

### D1 — Exit via a new `explore.dialogue_leave` UI action (not a client-only fold, not a text command)

Candidate A was a client-side "collapse the box" toggle — rejected: the committed mode/session
would still say `dialogue`, the dock/feed would flip back on the next commit, and the session
state would lie about the fiction. Candidate B was a `talk stop` text command — rejected: the
player surface we are fixing is pointer/keyboard UI, and the command docs surface stays frozen.
Chosen: register `explore.dialogue_leave` with payload exactly `{npc_id}` (positive int, same
validator idiom as `validate_talk_scripted_payload`). The adapter re-resolves the actor's
LIVE session through `live_dialogue_session`; no live session, or one naming a different NPC,
rejects with stable code `dialogue_inactive` before any write. Success calls the sole-writer
`clear_dialogue_session(character)` (the helper the spec already owns), pushes the presentation
update (same as the other clear seams), and returns a deterministic success message
(`你結束了對話。`). The session spec's ONLY-writer list gains exactly this seam. The clear lands
through the normal commit path, so mode flips back to `exploration` atomically — no client-side
optimistic UI.

### D2 — The dock keeps the exploration root in dialogue mode; the `dialogue.root` family is deleted

`rootDescriptorFor` drops the dialogue-first branch (dialogue mode is neither combat nor
creation, so the existing heuristic serves `exploration.root`). Consequences, all desired:
mode-switch teardown re-homes the stack to `exploration.root` (the frame-resolution spec
text drops `dialogue.root` from the root vocabulary); the `對話選項` tab, its pane, the
`dialogueForm` flag, the `dialogueFormPresented()` gate, `handleDialogueItem`'s descriptor
check, and the DockTabBar dialogue legend branch all delete cleanly (clean cutover — no flag
kept "just in case"). The feed keeps dispatching picks through `dispatchAction` exactly as
before (the emits wiring in AppClient is unchanged for picks).

Alternative considered: keep the dock mirror but add an exit tab. Rejected — the user's
complaints #1 and #2 are the mirror itself (duplicated rows, lost affordances); a mirror with
an exit button still hides the move rows, which is what made leaving the room feel like the
only door.

### D3 — Digit keys retarget from dock rows to caption picks while the variant presents

The store's `focusPress` digit path currently remaps slots when the DOCK presents the dialogue
form. After D2 the dock's rows are the exploration root, so digits must not double-bind
(1 = first move row AND first pick would be incoherent). Chosen: while committed mode is
`dialogue` AND the panel is available AND the caption renders at least one pick, digits `1`–`4`
activate the caption pick rows (the same `handleDialogueItem`-equivalent dispatch entry,
one derived source); the `⌨` free row and the new exit row take no digit slot; when the panel
is unavailable or renders no picks, digits fall through to the dock/command-line path
unchanged. The legend keeps its regular wording (`數字鍵 1–4 · Enter 執行 · Esc 返回`) — the
dialogue branch is deleted, per the legend's own honesty rule; the digits stay truthfully
"pick the first four rows", the rows just live in the caption while it presents. ArrowRight's
dock borrow is deleted with the form; freeform entry keeps two paths: the caption `⌨` row and
typing `talk <npc> <話語>` directly (the borrow seam `borrowDialogueCommand` stays for the
caption row — it keys off the committed panel, not the router descriptor).

### D4 — Choice cap 16 → 4 as a dialogue-panel-owned bound

`web/webclient/presentation/dialogue.py`: `DIALOGUE_MAX_CHOICES = 4` becomes its own literal
(not `MAX_SCRIPTED_KEYWORDS`, which stays 16 for the interact-target keyword pool — the two
bounds are documented as independent today). Server validator rejects a fifth choice; the UMD
mirror `protocol.js` `DIALOGUE_MAX_CHOICES` becomes 4 in lockstep (Node gate + Vitest mirror
tests pin the message). Table order keeps the first four authored keywords — the same prefix
the affordance surface already truncates with — so no re-ranking logic is invented.

### D5 — Caption restructure: static head above a dedicated scroll viewport, two-column picks

`NarrativeFeed.vue` becomes: card root (not scrollable) → `.narrative-head` (static, sibling
of the scroll region, so nothing can ever render between the card edge and the head) →
`.narrative-scroll` (the only `overflow-y:auto` element; keeps `role="log"`, the scroll-keep/
unread/pin owners move to it unchanged in behavior). The 32vh bound moves from the card to the
scroll region; the card grows only by the head's fixed height.
In the dialogue variant: picks render in a two-column CSS grid (single column under the
caption's narrow width via container query/`@media` fallback), and the freeform + exit rows
form one trailing row pair. With the 4-choice cap the exchange unit (avatar box + up to 4
picks + trailing row) fits 32vh for normal lines; the existing pin keeps the box top aligned
under the head when a pathological 2000-code-point reply overflows — behavior unchanged, but
now bounded by ≤4 picks instead of ≤16.

### D6 — Exit row placement and wiring

The exit row renders inside the `.choices` unit as a distinct `.pick.pick-exit` row (label
`結束對話`, `✕` badge, `data-testid="dialogue-exit"`), clicking emits
`dialogue-leave` → AppClient → `store.dispatchAction("explore.dialogue_leave", {npc_id:
vm.host.identity})`. It sits after the freeform row. No confirm step: the action is
consequence-free (a clear seam the movement settlement already performs silently), and the
server rejects races idempotently.

### D7 — Command-echo catalog: declared silent presentation control (Rubber-duck)

Registering `explore.dialogue_leave` trips the registry-coverage contract
(`webclient-input-narrative::catalog-coverage-is-pinned-against-the-action-registry`).
Candidate resolver was a fabricated `leave <NPC>` echo — rejected: no such text command exists,
and the catalog's own rule is to stay silent rather than invent a command. Chosen: add the id to
`command_echo.js`'s `SILENT_PRESENTATION_CONTROLS` (the server success line is the player-facing
outcome, mirroring `options.dismiss`'s reasoned-silence idiom), extend the manifest's
`silentPresentationControlIds`, and pin the silence in the Node catalog gate.

### D8 — One shared exploration-form predicate for the widened lifecycle (Rubber-duck)

The dock-form lifecycle assumptions are not confined to the two submit gates: hosted/non-hosted
drawer close, Escape/menu-close `activeSubDock` cleanup, and settle-driven sub-dock teardown all
hard-check mode `exploration`. Chosen: one store-level predicate
(`dockOnExplorationForm(rs)` ⇔ mode ∈ {exploration, dialogue}) replacing every such guard in the
router lifecycle, so a services/character sub-dock opened while talking closes, re-homes, and
settles exactly as in exploration mode. Partial widening is the known failure mode this guards.

## Risks / Trade-offs

- [Existing tests pin the mirror behaviour] → `dialogue_dock.test.js`, the `dialogueForm`
  branch of `dialogue_store.test.js`, the legend swap scenarios in the dock suites, and the
  frame-resolution teardown scenario are REMOVED with the behaviour, not re-pinned; new
  caption/exit/digit-retarget tests replace them in the same change.
- [Digits bound outside the dock while the dock still shows its legend] → accepted: the
  legend names the generic digit-row behaviour; the caption's pick badges (`1..4`) are the
  visible source of truth while it presents. Covered by a store test asserting the dock root
  rows are NOT claimed while the variant presents picks.
- [Host replies with >4 authored keywords lose caption access to keywords 5+] → mitigation:
  the interact-target affordance list still offers all 16 (unchanged), and freeform talk
  covers the rest; no production table currently exceeds a handful of keywords.
- [`dialogue_leave` race with a clear seam (NPC departed first)] → adapter rejects with
  `dialogue_inactive`; the client shows the standard one-shot rejection line and the next
  commit already shows exploration mode — no stuck state.
- [Scroll-owner refactor regresses scroll-keep/unread/pin] → the three owners move verbatim
  onto the new element; the existing `narrative_feed`/`dialogue_feed` Vitest suites are the
  regression net.

## Migration Plan

No data migration (`db.dialogue_session` untouched). Server registry, presenter, UMD mirror,
Vue store, and components cut over in one change; deploy is a plain restart. Rollback = revert
the change (no persisted-shape dependency).

## Open Questions

- None blocking. (A future refinement could let the caption collapse to a one-line "交談中…"
  chip on Esc; deliberately out of scope — the explicit exit row is the contract.)
