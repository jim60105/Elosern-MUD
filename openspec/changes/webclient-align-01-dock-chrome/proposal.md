# Proposal: webclient-align-01-dock-chrome

## Why

The dock band renders its gradient inside the max-width-centered content container, so at
wide viewports the design draft's full-bleed band shows pure-black gutters on both sides
(measured: content x=210 of 1600). The draft (`docs/design/elosern-redesign/index.html`)
draws the gradient, hairline top border, and shadow on the full-width `.dockwrap` and centers
only the content `.dock`. The dock's shortcut legend also diverges from the draft's `.hint`
structure (plain text, no `<kbd>`, advertises `/ 聚焦指令列`), and the command line's utility
buttons use a heavier style than the draft's `.hist button`.

## What Changes

- The dock's full-bleed band (gradient, `border-top`, shadow, padding) moves to the
  full-width anchor wrapper; the centered max-width container keeps only content layout.
  The single `#action-dock` element identity, `--dock-h` height, tab-bar/breadcrumb/row-region
  layout, and scroll contract are unchanged.
- The dock shortcut legend becomes the draft's hint markup: `數字鍵 1–4 · <kbd>Enter</kbd> 執行 ·
  <kbd>Esc</kbd> 返回`, with the draft's `kbd` styling (mono, `--ink-780` ground, 2px bottom
  border). The `/ 聚焦指令列` wording is dropped (the binding itself stays implemented).
  The truthfulness rule (name only implemented behaviour) is kept.
- The command line's four utility buttons keep their positions and functions but adopt the
  draft `.hist button` style (transparent ground, 26×26, hover `--ink-700`).

## Capabilities

### New Capabilities

(None)

### Modified Capabilities

- `webclient-contextual-hud`: the action-dock geometry requirement is restated as a
  full-width band with a centered content container (fixes the black gutters), and the
  shortcut-legend requirement adopts the draft's wording and `<kbd>` structure while
  keeping the one-instance and truthfulness rules.

## Impact

- `web/webclient-app/components/ActionDock.vue`, `DockTabBar.vue`, `AppShell.vue`/stage
  anchor styling, `styles/tokens.css` consumers; `CommandLine.vue` utility-button styling.
- Anchoring Vitest/DOM-contract tests for dock geometry and legend wording updated in the
  same change.
- No server, protocol, or player-command surface changes; no docs churn.
