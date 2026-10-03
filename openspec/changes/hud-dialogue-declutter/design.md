# hud-dialogue-declutter — Design

## Context

The stage's mode-visibility rules are CSS selectors on `.elosern-stage[data-elosern-mode="<mode>"]` combined with anchor `data-anchor` selectors. Creation already hides the `vitals` and `map` anchors; combat hides `.local-map`. Dialogue extends the anchor gate, its pre-flush focus selector, and the dock's effective reveal visibility.

## Goals / Non-Goals

**Goals:**
- Hide the vitals dock in dialogue mode
- Hide the map anchor (place card + minimap) in dialogue mode
- Preserve all standing portraits during dialogue

**Non-Goals:**
- Adding a "minimal HUD" toggle or preference
- Changing exploration or combat visibility
- Animating the dialogue transition differently

## Decisions

### D1 — Hide the anchors wholesale, not individual islands

The `map` anchor contains the place card, the minimap, the objective line, and optionally the combat participant frame and title ballot. During dialogue, none of these render or need to render. Hiding the anchor hides all its children — simpler and more future-proof than hiding each island class individually. The `vitals` anchor similarly carries only the dock (condition icons + bars); hiding the anchor hides the dock.

**Alternative:** Hide `.place-card`, `.local-map`, and `.status-panel` individually. Rejected — more selectors, same result, breaks if a new island is added to the anchor.

### D2 — Dialogue mode suppresses the vitals rule entirely

The vitals rule (show dock when a vital is below max, or a condition needs attention) is overridden by the mode hide: `display: none !important` from the mode selector wins over the `v-show` reveal. This means a vital dropping below its maximum during dialogue does NOT show the dock. The user explicitly requested this: "完全用不到" (completely unused during dialogue). If the game needs to alert the player to combat-relevant events during dialogue, the message window handles it narratively.

### D3 — Focus rescue on mode change to dialogue

Extend `HIDDEN_BY_MODE.dialogue` to include `vitals` and `map`. The existing entering-dialogue pre-flush `active.closest()` branch then moves focus to the message page while the DOM still carries the previous mode. The post-flush heuristic is not the rescue mechanism; it only promotes focus to the choice list when appropriate.

### D4 — Reuse reveal timing without changing mode choreography

Live dialogue entry fades the outgoing anchors with the existing `--motion-reveal` and exit easing. CSS `display` transitions use `allow-discrete` to retain exit paint until the fade settles at `display:none`; both anchors become inert and `aria-hidden` at commit. Mounts, reconnects, motion-off, and browsers without discrete transition support hide immediately. No mode-transition timing or backdrop treatment changes.

The real dock also receives effective visibility `mode !== "dialogue" && vitals.visible`, so its existing reveal sinks toward the band on exit and rises from positive `translateY` on return. Data updates during dialogue cannot start that reveal. The map column restores at commit; the dock alone owns its normal return motion.

## Risks / Trade-offs

- **[Poison during dialogue]** If a condition deals damage during dialogue, the player won't see the dock. → The message window is the dialogue's attention surface; if damage during dialogue is narratively relevant, it appears as a dialogue line. The dock reappears on mode exit.
- **[Low-HP vignette]** The `data-lowhp` vignette overlay on the stage is NOT mode-gated — it already renders in any mode when `isLowHp` is true. So a low-HP state during dialogue still shows the vignette border, giving a visual cue even with the dock hidden. → No risk.
- **[Title ballot during dialogue]** The title ballot mounts in the map anchor. If a title vote happens during dialogue (unlikely), it would be hidden. → Title votes are exploration-only events; the ballot is not rendered during dialogue regardless.
