## Context

`DreamPanel.vue` is mounted by `AppClient.vue` while the committed `dream` panel (schema v2) is open. Its box is fixed to `inset: var(--header-h) 0 var(--workspace-bottom)`, which is the whole stage plus the band, with the command-line row left visible below. The server owns every fact the surface shows:
- the exchange count and the remaining count;
- whether input is allowed, whether a response is pending, and whether the last generation failed;
- the excitement `track` (ordinal 0–4 over the canonical five bands, plus the level label);
- the opening, the scene and dialogue prose, and the direction parts;
- the thread choices and the saved draft preferences.

On every `say` the server stores the player's last message as the direction, so "the 念頭" defaults to what the player last said. Awaken auto-saves that direction as a draft when none exists, so only *local* unsent edits can be lost. When the dream closes, the panel unmounts and the server's ending line lands in the normal message window.

The official artwork is near-white, 2880×1600. The left ~45% is empty pale sky with low clouds and calm water. The faceless goddess on her throne fills the right ~55%.

The AVG stage language comes from `docs/superpowers/specs/2026-09-23-webclient-avg-stage-redesign-design.md` §5, §6, §8 and §9:
- a full-bleed stage;
- a bottom band whose message window takes 2/3 of the width;
- a name plate inside the window, choice rows with numbered badges and gold corner brackets;
- motion only through `--motion-*` tokens at full, reduced or off levels;
- committed state is never gated by presentation.

The redesign brief, critique and storyboard were produced in a game-UI design pass and verified with Storybook screenshots at 1280×720, 1600×900 and 1920×1080, using the real artwork.

## Goals / Non-Goals

**Goals:**
- Present the dream as a scene in the established AVG vocabulary, keeping the goddess uncovered above the knees and leaving the band's right third open onto the art.
- Keep the whole redesign inside one SFC and its story. Reuse the shared typewriter clock, the motion tokens, the focus-trap utility and the `.ui-btn` chrome.
- Derive every presentation state from the committed panel plus a few local refs.

**Non-Goals:**
- No server, protocol, validator, action or text-command change.
- No persistence of unsent drafts across a full page reload (sessionStorage backup was considered and deferred).
- No in-dream display of server refusal text for draft/confirm. Refusals still arrive as narrative lines behind the modal, and surfacing them needs a store change.
- No exit transition in `AppClient.vue` (a white "wake" fade around the `v-if` was considered and deferred).

## Decisions

### D1. Layout: sky card + docked reply bar + 2/3 band (1920×1080 reference, all px × `--ui-scale`)

```
┌ stage (inset header … workspace-bottom) ──────────────────────────────────┐
│ ╭ 雲上王座之夢 · 夢中無晝夜 ╮                          [story tools slot]    │
│ ┏ 此刻的念頭 ─── ‹provenance› ┓          goddess / throne (uncovered)      │
│ ┃ summary (3-line clamp)       ┃                                           │
│ ┃ 歸屬：…                      ┃                                           │
│ ┃ ① 改寫念頭…  ② 帶著…醒來     ┃                                           │
│ ┃ ③ 記下念頭…  ✕ 醒來          ┃                                           │
│ ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛                     ‹converging caption›  │
│ ┌ 你 │ reply textarea (grows ↑)          ◆◆◇◇◇◇ 尚餘 n │ 訴說 ┐            │
│ ╞═ band 66.667% × --band-h, right 96px feathers into the art ═╡  water   │
│ │ ◆ 王座上的女神 ▰▰▱▱▱ level        (◆◆◆ 正在回應)          │  & foot  │
│ │ beat text (serif, 42em measure, scrolls)                  │          │
│ │ 重讀                                  Enter 繼續 / ▼ ■     │          │
└─┴───────────────────────────────────────────────────────────┴──────────┘
```

- The card sits at `left: 40px; top: 84px; width: min(440px, 32vw)`, with a max height that clears the band and the reply bar. Under `max-height: 800px` it compacts: the preview clamps to one line and the rows tighten, so it fits 1280×720.
- The reply bar spans `66.667% − 72px` and docks `10px` above the band. The converging caption aligns to its right end so it never overlaps the card.
- *Alternatives:* a full-width band covers both of her feet, and a left column re-creates the old box. Putting the exits in the band strip would be too cramped and would hide the 念頭.

### D2. Legibility over near-white art: "ink lacquer glass"

All chrome uses `linear-gradient(rgba(16,18,22,.86) → rgba(11,13,16,.93))` with `backdrop-filter: blur(12px)`, a 1px `--band-edge` top rule and a **pale halo** shadow instead of a dark drop shadow, so the panels read as inlays set into the light. The band uses a `mask-image` feather on its right 96px.
- With the art missing, a pearl gradient of the same luminance replaces it, so contrast does not change.
- A rose radial aura multiplies over the art at `ordinal × 0.055` opacity, giving ambient feedback for excitement.
- *Alternative:* light "paper glass" chrome. Gold on white falls under 4.5:1 and breaks the token language.

### D3. Track visuals live where they are used

The budget pips sit on the reply bar, because the budget is spent at the send decision. The excitement gauge sits on the speaker's name plate, reusing the `· 羈絆` slot idea from the dialogue stage. Gauge segments run from gold to seal red at index 4, and the level label sits beside them, so colour is never the only signal.

### D4. Beat controller over the shared typewriter, not the message-page measurer

`beats` holds `[opening]` on arrival, or `[scene, dialogue]` after a reveal. Pending and failure override the presented beat with an echo or a notice. One synchronous watcher on the presented beat's `(kind, text)` either types it, when the change came from a reveal or an advance, or completes it at once (echo, notice, re-read, reconnect). `present()` suspends the watcher while it swaps the list and the index together, which avoids a mid-swap completion. The band scrolls within its fixed height instead of paginating.
- *Alternative:* reusing `MessageWindow`'s paging measurer (about 1400 lines). It was too heavy, and sentence integrity is preserved by scrolling anyway.

### D5. Reveal only on a live `completed` increase

A non-reactive `revealedCompleted` records the last presented count. The watcher animates only when the new count is greater, so a draft republish or a revision bump at the same count presents nothing new, and a fresh mount shows the latest beat in full (§9.2's mount rule). A count increase that arrives with a reconnect while the surface stays mounted is presented as a reveal. The player never saw that response, so typing it is the correct presentation, not a replay. Reaching six live also triggers a one-shot white bloom (token-gated, dropped at reduced and off) and moves focus to the confirm row.

### D6. Exits by meaning; emphasis follows the phase

The keepsake rows are four `.ui-btn` buttons in a `role="group"`. Arrow keys move between them, and digits 1–3 work outside text fields, keeping the dialogue-choice grammar. `ui-btn--primary` belongs to 訴說 while input is possible and moves to the confirm row at the cap. When the summary is empty, the confirm row is `aria-disabled` with the reason 尚無念頭, but it stays focusable, and activating it routes to the sheet with the alert.
- *Alternative:* keeping confirm primary at all times. That pulls the eye away from talking, which is the core loop.

### D7. Escape and the awaken check

Escape never dispatches. Its order is: close the confirm dialog, close the sheet, blur a text field to the band, or focus the ✕ row and announce the hint. `dirty` is true when there is unsent reply text, or when the trimmed summary, the thread, or the chip snapshot differs from the last synced server values. The confirm dialog is an `alertdialog` with initial focus on 回到夢中.
- *Alternatives:* Escape awakens at once (the old behaviour), which ends a finite session on a stray key; or always confirming, which nags when nothing would be lost.

### D8. Layers and focus

The root, the sheet and the confirm dialog each own a `createFocusTrap`. Tab routes to the top layer's trap. While a layer is open, the main stage is `inert` and an ink scrim covers it. Closing a layer restores focus to its opener. Key handling stays contained (`stopPropagation`), so the shell router never sees dream keys, and IME composition is ignored.

### D8b. Transport lock mirrors the store's dispatch guard

`transportLocked` mirrors the store's own refusal conditions: disconnected, `mutationsLocked`, `phase !== "active"`, a dispatch in flight, or `dispatch.beatLocked`. Controls therefore never look usable while their dispatch would be silently refused. Text fields stay editable while locked, so edits survive a reconnect.

### D9. 念頭 sheet data model

The local refs are `direction`, `thread` and `tags{five lists}`, plus a `synced` snapshot of the last authoritative values. The snapshot starts from the empty values, so a mount with a saved draft adopts its summary, thread and chips as unedited. On every republish for the same session, each field adopts the server value only while it equals the previous snapshot, compared after trimming for the summary. The summary field has no `maxlength`: over-length server text is shown in full, and draft and confirm are refused until the player shortens it. Payload construction is the same as before: `{...nonEmptyTags, kind, thread_id, summary}`, or `""` when everything is empty.

### D9b. The draft toast confirms the committed draft

The draft button closes the sheet at once. The toast 念頭已記下，夢仍在繼續。 waits for a newer revision that carries `draft_preferences`, so a refused draft shows nothing instead of a false confirmation.

### D10. Failure recovery

`lastSent` keeps the trimmed text of the last successful `say` dispatch. It feeds the pending echo, and on `failure` it refills an empty reply field.

### D11. Storybook as the storyboard

`World/DreamPanel` keeps its id, and component-manifest and showcase evidence are untouched. Its fixture now starts from a true arrival state (empty scene and dialogue). The story view model provides `motionLevel` and `textSpeed`, so the typewriter runs at full motion, and the synthetic publisher advances the track through the canonical labels. The named stories are the storyboard frames: Storyboard (arrival), Conversing, Converging, Pending, Failed, Drafted, AtCap, ManyThreads, Disconnected and NoArt.

## Risks / Trade-offs

- [The live client geometry differs from Storybook, for example the `.elosern-root` override pitfall] → `app-shell.css` has no `dream` rules; Storybook renders under `.elosern-root`, and the live-client geometry check is listed as a follow-up when the container image is rebuilt.
- [Escape no longer awakens: a behaviour change for anyone used to it] → The band strip shows `Esc 前往醒來`, and Escape lands focus on the ✕ row, so one more Enter wakes.
- [`field-sizing: content` is unsupported in some browsers] → The textarea falls back to a fixed one-line height with internal scrolling, and its function is unaffected.
- [Unsent text is lost on a full page reload] → Accepted for now and recorded as a non-goal; the awaken check covers in-session loss.
- [Server refusals stay hidden behind the modal] → Local validation covers the predictable refusals (empty, over-length); surfacing others is a deferred store follow-up.

## Review dispositions (independent critique)

- **Adopted:**
  - mount-time preference rehydration (the snapshot started as `"{}"`);
  - the full dispatch-guard lock;
  - toast on the committed draft;
  - spec wording for a reconnect count increase, captions, the lock, sixth-exchange focus, and saved preferences on mount;
  - modifier-free digit shortcuts;
  - focus kept on the page after 重讀;
  - the layer-open race guard;
  - trimmed rehydration;
  - player documentation (`docs/game/command-reference.md`) for the new Escape and keyboard behaviour;
  - the evidence bridge pinned to exact Vitest case names with an exact expected count per requirement;
  - ten new Vitest cases for every claim the review found unasserted.
- **Kept as design-only:** token and chrome constraints (motion tokens, `.ui-btn`), which the spec now states as observable outcomes.
- **Deferred:** the live-client geometry check after an image rebuild; in-dream display of server refusal text.

