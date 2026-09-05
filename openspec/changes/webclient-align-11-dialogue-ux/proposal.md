# Proposal: webclient-align-11-dialogue-ux

## Why

The dialogue surface landed in `webclient-align-08-dialogue-surface` is unplayable in practice: entering a conversation locks the dock into a `對話選項` mirror that hides every other dock affordance, duplicates the exact same pick rows inside the narrative caption, offers no way back (the player's only exit is physically leaving the room), and — because the caption is a 32vh scroll card whose picks stack below the reply — a panel with many choices pushes the speaker's line out of view so the player scrolls buttons while the conversation itself is invisible. The sticky `.narrative-head` also leaks stream content into the strip between the card border and the head.

## What Changes

- **The narrative caption becomes the single dialogue surface.** The feed's dialogue variant gains a trailing `結束對話` (exit) row that clears the session; the box (host + line + picks + exit) is guaranteed to fit the caption without scrolling.
- **The dock stops hijacking itself in dialogue mode.** While mode is `dialogue`, the action dock keeps its ordinary exploration root (move/interact/suggestions/…) instead of tearing down to the single-`對話選項`-tab mirror. Moving away stays the implicit exit; the explicit exit row is the deliberate one. The duplicated pick rows in the dock are removed (the rows live once, in the caption).
- **A new deterministic exit seam:** the `explore.dialogue_leave` UI action (payload `{npc_id}`) validates that the viewer's live session names that NPC and clears it through the sole-writer `clear_dialogue_session` helper — the session spec's ONLY-writer list gains this seam. Mode commits back to `exploration` atomically.
- **The dialogue panel choice cap drops from sixteen to four** (`DIALOGUE_MAX_CHOICES = 4`, table order, server validator + client mirror in lockstep), matching the `數字鍵 1–4` legend and keeping the bounded caption self-contained. Overflow keywords stay reachable through the interact affordance surface, which keeps its own budget.
- **Feed card chrome restructure:** the head row moves out of the scroll viewport (a static header above a dedicated scroll region), so narrative content can never render between the card border and the head, and the dialogue-variant layout compacts picks into a two-column row grid so the bounded caption always fits the current exchange.

## Capabilities

### New Capabilities

（無。）

### Modified Capabilities

- `webclient-contextual-hud`: the feed dialogue-variant requirement (exit row, head-outside-viewport layout, bounded fits, dock no longer mirrors picks); the dock dialogue-form-mirror requirement is **replaced** by a keep-the-exploration-root requirement; the shortcut-legend dialogue branch is retired.
- `webclient-dialogue-session`: the panel requirement's `choices` bound changes sixteen → four; the ONLY-writer list gains the `explore.dialogue_leave` adapter success path as a clear seam.
- `webclient-action-dispatch`: registration of `explore.dialogue_leave` (validator, adapter, availability context).
- `webclient-frame-resolution`: the `dialogue.root` resolver family is removed (the dock has no dialogue form anymore); mode-based root selection returns to the combat/creation/exploration heuristic while mode is `dialogue` (the exploration root descriptor serves the dialogue-mode dock).

## Impact

- **Server:** `web/webclient/presentation/dialogue.py` (choice cap constant + validator message), `web/webclient/actions/exploration_actions.py` + `registry.py` (new action), `world/rules/dialogue.py` (seam comment), client protocol mirrors (`bridge.js`, UMD `protocol.js` panel validation if it bounds choices, `stores/dialogue-view.js`).
- **Client:** `components/NarrativeFeed.vue` (head/scroll restructure, exit row, two-column picks), `AppClient.vue` / `AppShell.vue` (exit emit wiring, dock props), `stores/elosern.js` (drop `dialogue.root` teardown + `dialogueFormPresented` + digit/ArrowRight dialogue branches), `stores/frame-resolvers.js` (drop family).
- **Docs/tests:** `docs/game/commands.md` unchanged (no player text command changes — the exit is a UI action; `talk` semantics unchanged); Vitest dialogue suites, node protocol gate where the choice bound is pinned, `tools.spec_traceability`, shard manifest unaffected (no new test modules).
- No data migrations; `db.dialogue_session` shape unchanged.
