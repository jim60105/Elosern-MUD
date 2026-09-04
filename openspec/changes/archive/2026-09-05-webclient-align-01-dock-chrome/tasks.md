# Tasks: webclient-align-01-dock-chrome

## 1. Full-width dock band

- [x] 1.1 Move the dock band chrome (gradient `linear-gradient(0deg,#0c0a0e,#141019 70%,var(--panel))`,
  `border-top`, upward `box-shadow`, `11px 18px 12px` padding) onto the full-width dock-anchor
  wrapper element; strip those properties from the max-width-centered `ActionDock` container,
  keeping `max-width:1180px; margin:0 auto` and the tab-bar/breadcrumb/row-region vertical layout.
- [x] 1.2 Confirm `--dock-h` height ownership, the single `#action-dock` element identity, its
  `data-mode` attribute, tab index, and focus role are untouched across explore/combat/creation.
- [x] 1.3 Update the Vitest/DOM-contract geometry tests that assert the gradient/shadow on the
  inner container to assert them on the band wrapper, and add the gutter assertion (painted band
  spans full stage width; content column centred, max 1180) at 1280x720 and 1600x900.

## 2. Shortcut legend to draft structure

- [x] 2.1 Replace the legend content with `數字鍵 1–4 · <kbd>Enter</kbd> 執行 · <kbd>Esc</kbd> 返回`
  and delete the `/ 聚焦指令列` wording; keep the `data-testid` hook on the single visible element
  and remove the visually-hidden duplicate.
- [x] 2.2 Add the draft `kbd` rule (mono, `--ink-780` ground, `--ink-600` 1px border with 2px
  bottom, radius 4, `--paper-300`) scoped to the legend.
- [x] 2.3 Update the legend one-instance/wording tests: exactly one legend element; text matches
  the draft; no element names a key the client does not bind.
- [x] 2.4 Make the named digits real: bind `1`–`4` in the store's `focusPress` entry (move the
  current frame's focus onto the Nth row and activate through the same confirm path as Enter;
  unclaimed when the frame has fewer rows or the stack is empty; the quantity form keeps
  precedence), add the digits to the bridge's claimed-key set, and add the key to the client's
  controls reference — the UMD keyboard router stays untouched (design D1).
- [x] 2.5 Cover the binding: Vitest store suite (pick, disabled row, unclaimed slot, pre-session,
  quantity precedence, repeat suppression), bridge claim test (consumed digit prevents the
  default, unclaimed digit does not), and a managed-browser journey (digit 4 pops via the back
  row, digit 2 submits the second row's move once, digit 9 unclaimed).

## 3. Utility button restyle

- [x] 3.1 Restyle the command-line utility buttons (lineage/codex/settings/help) to the draft
  `.hist button` treatment (transparent ground, 26×26, hover `--ink-700`); keep positions,
  functions, labels, and accessibility attributes unchanged.

## 4. Verification

- [x] 4.1 Run the focused Vitest suite covering dock chrome and command-line bar tests.
- [x] 4.2 Screenshot the live client at 1600x900 and 1280x720 (if reachable) and compare the dock
  band, legend, and command-line buttons against the draft at the same viewport.
