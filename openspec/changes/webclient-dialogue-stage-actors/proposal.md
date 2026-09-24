## Why

The AVG stage design (`docs/superpowers/specs/2026-09-23-webclient-avg-stage-redesign-design.md` §2 item 5, §4, §5.2, §8.2) turns a conversation into a scene. The player stands on the left, the NPC stands on the right, the speaker is lit and the listener dimmed, and the command panel collapses so the message window spans the band under a name plate. Today, after C9a and C9b, 交談 opens a conversation, but it shows only as a variant inside the two-thirds message window. The command region keeps showing the exploration overview beside it, and `actor-right` stays empty. C10a (`dialogue-panel-host-portrait`) now ships the host's art catalog key. This change (C10b) builds the stage half of the dialogue screen: `StageActor` on both sides with the speaking state, the collapsed command region, and the name plate. C10c then pages the line and moves the choices over the stage.

**Implementation profile:** visual. Portrait placement, the dim treatment, the full-width band, and the name plate's look need layout and look-and-feel judgement at the reference viewport.

## What Changes

- **New governed component `web/webclient-app/components/StageActor.vue`** (story `stories/Core/StageActor.stories.js`, manifest title `Core/StageActor`).
  - It wraps `ReferenceArtwork`, which stays for the drawer's `#art` slot (`AppClient.vue`).
  - Props: `portrait` (a roster or catalog entry, or `null`), `name`, `side` (`left` | `right`), and `dimmed`.
  - With no entry, it passes a placeholder built from `name` (the name's initial and the name), never a stock image.
  - The root carries `data-testid="stage-actor"`, `data-side`, and `data-speaking="true|false"`. It is dimmed with `filter: brightness(var(--actor-dim))`, where the new token `--actor-dim: 0.6` lives in `styles/tokens.css`.
  - The dim is a static state; C11 owns any transition.
- `web/webclient-app/AppClient.vue`:
  - `#actor-left` renders `StageActor` for the player: the roster's current portrait, unchanged, replacing the bare `ReferenceArtwork`.
  - `#actor-right` renders `StageActor` for the dialogue host while the mode is `dialogue` and the dialogue view model is available. Its entry is `artPanel.portrait_catalog[vm.host.portraitRef]` when the key is non-null, else `null`. The client never builds a key.
  - Speaking state: in dialogue mode the player is dimmed while `store.view.dialogueSpeaker === "host"`, and the host is dimmed while it is `"player"`. Outside dialogue nothing is dimmed.
- `web/webclient-app/stores/elosern/view.js` publishes `dialogueSpeaker`. It is `"player"` while `ctx.inFlight.actionId` is `explore.talk_scripted` or `explore.talk_freeform`, and `"host"` otherwise. The in-flight record lasts until the declared revision is accepted or the action is rejected. The freeform adapter settles only after the LLM reply, so the player stays lit until the reply commits.
- **Collapse in dialogue mode:**
  - `components/HudFrame.vue`: in dialogue mode `.stage-band` becomes one column and `[data-anchor="band-command"]` is `display:none`. `#action-dock` stays mounted, not remounted, and its router keeps the overview (C9b D1 already resets to it).
  - `components/AppShell.vue`:
    - `HIDDEN_BY_MODE.dialogue` names `[data-anchor='band-command']`.
    - `restoreDockFocus` becomes `restoreFocusHome`, which focuses the action dock, or in dialogue mode the message window's focus target. Every caller follows, including `composables/use-dock.js` `onNavigateHome` and the exposed API.
    - Focus is rescued before the dock hides on entering dialogue, and moved back to the dock after the attribute flips on leaving it.
- `web/webclient-app/stores/elosern/interaction.js` `focusPress`: in dialogue mode only the caption digit retarget and `/` are claimed. Every other key is unclaimed, so no key moves or activates the hidden dock.
- **`components/MessageWindow.vue`** (C6b/C6c):
  - In dialogue mode with an available panel, the window renders a name plate (`data-testid="message-name-plate"`) as a header row above its text area: `display_name`, plus ` · 羈絆 <stage>` in `[data-testid="dialogue-bond"]` only when `bond_stage` is non-null.
  - The dialogue box loses its avatar (`.av`) and its speaker line (`.who`, `dialogue-who`), because the portrait now stands on the stage.
  - The window exposes `focusHome()`: the first dialogue row while the variant renders, else the page surface.
  - The variant stays unpaged; C10c replaces it.
- `web/webclient-app/styles/app-shell.css`: dialogue-mode rules for the full-width message region and the plate. The command-line row keeps its geometry: it spans the band's left two thirds in every mode, so it never covers the host portrait.
- `lib/controls-reference.js`: the Enter / digits rows say that in dialogue the dock is collapsed and digits pick the conversation's choices.
- **BREAKING (internal)**: `tests/dialogue_dock.test.js` ("the dock keeps its ordinary form in dialogue mode") is rewritten to assert the collapse. Its evidence test is re-anchored.
- Spec deltas:
  - restate the stage, the visibility matrix, the command region, the legend, the dialogue variant, the message window, and the command line's focus return for the collapsed dialogue mode
  - replace "The dock keeps its regular exploration form in dialogue mode"
  - add the stage-actor requirement
  - restate the exploration dock's mode ownership, the desktop-shell required surfaces (dropping "bounded caption"), keyboard routing, and the showcase manifest
- No OOB schema, presenter, server, or persistence change.

Out of scope:
- Paging and typing the dialogue line, the choices over the stage, `↦ 移動…`, and the borrow restatement with the phase fix: `webclient-dialogue-choices-overlay` (C10c).
- Portrait slide-in, crossfade, and dim transitions: `webclient-motion-layer` (C11).
- Foes in `actor-right` during combat: `webclient-combat-beat-playback` (C13). In combat `actor-right` stays empty.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `webclient-contextual-hud`:
  - MODIFIED, each on the latest series text:
    - "The WebClient renders a full-bleed cinematic stage with anchored HUD surfaces" (C8b)
    - "Surface visibility is gated by the committed game mode" (C6c)
    - "The action dock fills the band's command region at a fixed size" (C8b)
    - "The dock's shortcut legend names only real keyboard behaviour and renders as one visible instance" (C8c)
    - "The feed presents the dialogue variant from the committed panel" (C6c)
    - "The message window presents the current response one page at a time in the band's message region" (C7)
    - "The command line is a collapsible row docked on the message region's top edge" (C5)
  - REMOVED "The dock keeps its regular exploration form in dialogue mode" (C8b).
  - ADDED "The command region collapses in dialogue mode and the message window spans the band".
  - ADDED "Stage actors present the player and the dialogue host with a speaking state".
- `webclient-exploration-menu`: MODIFIED "The keyboard-first exploration dock roots at the scene overview and opens dialogue directly" (C9b `webclient-talk-open-dock`). The dock owns the surface in exploration mode, and its root stays the overview while collapsed in dialogue.
- `webclient-desktop-shell`: MODIFIED "Required desktop surfaces remain visible and usable" and "Keyboard routing is menu-first and submission-safe" (both C8b).
- `webclient-component-showcase`: MODIFIED "Every required UI component is a Vue SFC with a documented Storybook story" (C8a): adds the stage actor.

## Impact

- New: `web/webclient-app/components/StageActor.vue`, `stories/Core/StageActor.stories.js`, `tests/core/stage_actor.test.js`.
- Edited source:
  - `web/webclient-app/AppClient.vue`, `components/AppShell.vue`, `components/HudFrame.vue`, `components/MessageWindow.vue`, `components/ReferenceArtwork.vue` (placeholder initial through `portraitGlyph`, design D1)
  - `composables/use-dock.js`, `composables/use-shell-focus.js` (if it calls the renamed API)
  - `stores/elosern/view.js`, `stores/elosern/interaction.js`
  - `styles/tokens.css`, `styles/app-shell.css`, `lib/controls-reference.js`
  - `component-manifest.json`
  - Stories `stories/Core/HudFrame.stories.js`, `stories/Core/AppShell.stories.js`, `stories/Core/MessageWindow.stories.js` (the dialogue state)
- Vitest: `tests/hud_frame.test.js`, `tests/app.test.js`, `tests/message_window_dialogue.test.js`, `tests/dialogue_dock.test.js`, `tests/dialogue_store.test.js`, `tests/store/digit_row_picks.test.js`, `tests/store/store_dispatch_focus.test.js`.
- Python evidence:
  - `web/webclient/tests/test_node_suite_evidence.py` (the dialogue-dock evidence re-anchors, plus new stage-actor evidence)
  - the showcase snapshots that list `Core/ReferenceArtwork` (`test_vue_showcase_{action,data,world,overlays}_evidence.py`) gain `Core/StageActor`
- Browser: `web/tests/browser/test_browser_exploration_dialogue.py`, `test_browser_contextual_hud_stage.py`, `test_browser_contextual_hud_anchors.py`, `test_browser_layout.py`, `browser_helpers.py`.
- Spec traceability: `webclient-contextual-hud::the-dock-keeps-its-regular-exploration-form-in-dialogue-mode` (`test_node_suite_evidence.py`) re-anchors to `…::the-command-region-collapses-in-dialogue-mode-and-the-message-window-spans-the-band`. The two new IDs are covered by new tests.
- Dependencies:
  - Archive order: C9a → C9b → C10a (`dialogue-panel-host-portrait`) → C10b (this change) → C10c (`webclient-dialogue-choices-overlay`).
  - Hot-spot files shared with every earlier stage change and with C10c: `AppClient.vue`, `AppShell.vue`, `HudFrame.vue`, `MessageWindow.vue`, `app-shell.css`. Run the series sequentially.
