# Visual review: creation preset card wall

Scope: the preset mode of `CreationOverlay` after this change: the
three-column header, the `CreationPresetWall` card wall and the footer key
hint. The review compares the result with approved design
`docs/superpowers/specs/2026-11-17-creation-portrait-redesign-design.md`
§4 (shell), §5 (card wall) and §11 (accessibility), and with the reference
prototype `Design/CreationPortraits` (`docs/design/creation-portraits/`).
The custom and concept modes keep their current layout until
`creation-stepped-form`. Only the tabs moved into the header.

This is a human review record. No automated test pins the copy, the roster
size or the markup reviewed here.

## Method

- Real production components in Storybook (`pnpm exec storybook dev`):
  `Overlays/CreationOverlay` (`Default`, `PresetDraft`, `PresetWall`,
  `PresetWallBrowsing`) and `Overlays/CreationPresetWall` (`Default`,
  `DraftRestored`, `ChooseHeld`, `SilhouetteOnly`, `SingleCard`).
- `PresetWall` and the wall stories use the synthetic cards in
  `stories/fixtures/creation_wall.js`. Their image attempts are the committed
  864x1536 (9:16) built-in defaults, the same aspect as every official preset
  image, because the offline static server serves no official-art route. One
  card's image is missing on purpose, which shows the alpha-terminal fallback.
  The committed `CREATION_PANEL_SAMPLE` cards carry no official image, so the
  `Default`/`PresetDraft` stories show the silhouette-only wall.
- Screenshots and interaction used headless `agent-browser` (a throwaway
  Chromium) at CSS viewports **1451x790** (`--ui-scale: 1`) and
  **2560x1440** (`--ui-scale: 1.4`, the cap). Each screenshot was opened as
  an image and judged visually. The numbers below come from DOM measurements.
- The real game was exercised by the browser journey
  `test_browser_creation_preset` on a fresh `pnpm run build`. At both
  reference viewports it asserts that the page does not scroll horizontally
  and that the primary action sits above the footer and inside the viewport.

## Findings

| Area | Expected (approved design) | Observed | Disposition |
| --- | --- | --- | --- |
| Shell (§4) | Header with three columns: title, `.ui-tabs` labelled 預設角色／自由創建／概念生成, subtitle. Reset on the left of a fixed footer. Preset mode puts a key hint on the right. | Matches the prototype. The tabs are centred in the header, and the content area gains the row the old tab strip used. The footer hint shows `← →` and `Enter` as small keycaps in the existing ink and gold, at `--text-xs`. | Accepted |
| Composition (§5.1) | One row of portrait cards fills the content height. The expanded card is about seven collapsed widths. | With 8 cards at 1451x790, a collapsed card is **96px** wide and the expanded card is **660px**, a ratio of 6.9 once the gaps are counted. With the 3-card sample the expanded card takes 7/9 of the row. | Accepted |
| Collapsed card | The figure is cropped from the top and dimmed with lowered saturation. An ordinal and a vertical name sit on a bottom gradient. On hover the figure brightens and the border turns gold. | The crop is anchored at the top and centred on the descriptor's face rectangle through `ArtworkPreview`, so faces stay visible. Ordinals now line up across cards: the names hang from one line instead of growing upward. That fixes the ragged ordinal row in the prototype. | Accepted, improved over the prototype |
| Expanded card | Uncropped 9:16 figure with a gold glow. The dossier shows 預設角色 NN / NN, name, race, a separator ornament, emphasis, background and 以〈名字〉啟程. | The figure is shown whole with a soft gold halo and a warm pool of light behind it. The name uses `--text-initial` in the display face. The dossier is capped at 560px × `--ui-scale`, so with few cards the button and the lines do not stretch across a wide card. The saved draft card carries a 目前草稿 chip, a diamond plus a word, so it is not marked by colour alone. | Accepted. The measure cap was added during review |
| Crop fidelity | One size definition: the figure is always card-height tall and 9:16 wide in `cqh`, and opening only changes position and scale. | The figure box is `height: 100cqh; width: min(100%, 56.25cqh)`. A frame captured mid-transition shows the figure scaling smoothly from the face crop to the full figure, with no jump. Silhouettes keep their full 9:16 width centred on collapsed cards rather than shrinking into the strip. | Accepted |
| Fallback | An absent or failed image uses the shared loader's terminal. The browser never builds a URL. | The card with the missing image shows the alpha silhouette. In collapsed cards it reads as a dark figure. This is the shared fallback treatment and is left unchanged. | Accepted |
| Motion (§5.1, §11) | `flex-grow` transition on `--motion-*`/`--ease-*`. Reduced and off switch immediately. | At full motion, card widths 50ms after a key press were mid-interpolation (`96,549,96,207,…`). With `data-motion="reduced"` the computed transition duration is `0s` and the widths are final within the same 50ms (`…,660,…`). Off inherits the global rule. | Accepted |
| Focus and state (§5.2, §11) | Collapsed cards are named native buttons. The expanded card shows `aria-current` plus a gold border, and keeps the existing gold focus outline. | Entering preset mode focuses the expanded card, which draws a 2px gold-400 inset outline inside its gold border. Focus follows a pointer or keyboard opening that started inside the wall. Dock-driven browsing leaves focus on the dock. The double gold frame is visibly distinct from the single border of the unfocused expanded card. | Accepted |
| Text floor | Nothing below `--text-xs`. All dimensions scale with `--ui-scale`. | The smallest text is the ordinals, eyebrow and key hint at `--text-xs`. At 2560x1440 everything scales by 1.4 and the page `scrollWidth` equals its 2560 width. | Accepted |
| Copy | Approved player-facing wording. | Tabs 預設角色／自由創建／概念生成, eyebrow 預設角色 NN / NN, primary action 以〈名字〉啟程, hint 「← → 或數字鍵 切換角色」「Enter 選擇」. The hint adds 或數字鍵 because the digit shortcuts are a supported path (§5.2). The marker 目前草稿 identifies the saved draft card. | Accepted |

## Residual notes

- Official preset art could not be shown offline. The built-in defaults have
  the same 9:16 size and transparent background, so the crop and halo
  judgements carry over. The face rectangle of each official image positions
  its own collapsed crop.
- If the preset limit grows past 8 cards, the wall needs the horizontally
  scrolling row described in design §14. That is out of scope here.
