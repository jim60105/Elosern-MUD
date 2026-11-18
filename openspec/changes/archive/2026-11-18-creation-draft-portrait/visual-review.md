# Visual review: creation draft portrait

Scope: the live `CreationPortraitSlot` in all five committed portrait states,
and the real `GalleryGenerateDrawer` mounted in creation context over the
custom form (its copy, layout, unavailability, rejection and nested focus).
The review compares the result with approved design
`docs/superpowers/specs/2026-11-17-creation-portrait-redesign-design.md`
§7 (portrait slot and generation flow), §11 (accessibility) and §12 (error
handling). Only existing tokens from `styles/tokens.css` are used; no token
was added.

This is a human review record. No automated test pins the wording, the
layout or the markup reviewed here.

## Method

- Real production components in Storybook (`storybook dev`):
  `Overlays/CreationOverlay` (`CustomPortraitPending`, `CustomPortraitReady`,
  `CustomPortraitFailed`, `CustomPortraitUnavailable`, `CustomPortraitDrawer`,
  `CustomPortraitDrawerReady`, `CustomPortraitRefused`,
  `CustomPortraitDrawerUnavailable`), `Overlays/CreationPortraitSlot`
  (`Empty`, `Pending`, `Ready`, `Failed`, `Unavailable`, `GateHeld`) and
  `Overlays/GalleryGenerateDrawer` (`CreationContext`, `CreationRegenerate`,
  `CreationRejected`, `CreationUnavailable`, plus the unchanged gallery
  stories). All panels are synthetic story fixtures.
- Screenshots and DOM measurements used headless `agent-browser` (a throwaway
  Chromium) at CSS viewports **1451x790** (`--ui-scale: 1`) and
  **2560x1440** (`--ui-scale: 1.4`). Each screenshot was opened and judged
  visually.
- Motion levels were checked by setting `<html data-motion>` to `full`,
  `reduced` and `off` on the pending story and reading the computed animation
  durations.
- The real game was exercised on a fresh `pnpm run build` by
  `test_browser_creation_portrait` (the drawer open at both reference
  viewports, no page-level horizontal scroll, the submit on screen, pending to
  ready while editing) and `test_browser_creation_viewport_pointer`.

## Findings

| Area | Expected (approved design) | Observed | Disposition |
| --- | --- | --- | --- |
| Slot composition (§7.1) | Picture, then the name, then the state caption and one button. | The frame keeps its gold corners and floor light. Under the name sits a status plaque: a short heading with a diamond mark, then the caption. The action row is last. At 1451x790 its bottom edge lines up with the steps' 上一步／下一步 row, so the two columns end on one line. | Accepted. The plaque was added during review to give the caption a place that reads as status rather than body text |
| Empty | Silhouette, 「填好身分後，為角色繪製肖像。」, 生成肖像. | As specified; the heading reads 尚未繪製 with an outlined diamond. | Accepted |
| Pending | Breathing silhouette and a spinner; 「可以繼續填寫，完成後會自動出現。」; button disabled. | The silhouette breathes between 55% and full opacity on `--motion-pending`, and a thin gold ring with a soft glow turns at chest height on `--motion-spin`. The heading is 繪製中 with a half-filled diamond. The disabled button reads 繪製中… so the control states why it is unavailable. | Accepted |
| Ready | The generated portrait; 「不滿意可以重新繪製。」; 重新生成肖像. | The artwork fills the frame from the top and fades in on `--motion-portrait`. The frame border warms from the dim edge to `--band-edge`. The heading is 肖像完成 with a solid diamond. In Storybook the fixture's runtime URL is not served, so `ArtworkPreview` shows its existing load-failure note over the silhouette. The real-game journey shows the stored card. | Accepted. The Storybook load failure is the fixture, not the slot |
| Failed | Silhouette, the server's reason, 生成肖像. | The silhouette recedes to 70% opacity. The plaque turns seal red with a crossed diamond and 繪製失敗, and the caption is the server reason verbatim. Generation stays enabled for an explicit retry. | Accepted |
| Unavailable | Silhouette, the server's offline reason, button disabled. | As failed, with the heading 繪圖服務離線. 生成肖像 is disabled and 重新檢查 stands beside it, so the row keeps two equal buttons. | Accepted |
| Not colour alone (§11) | Every state also differs by shape or text. | Each state has its own heading text and diamond shape (outlined, half, solid, crossed). | Accepted |
| Drawer placement | The existing drawer, above the creation modal. | Teleported to the body at the drawer tier over the shared scrim. In creation context it is anchored to the right at a reading width (880px × scale, never wider than the viewport less the side insets). The custom form stays visible, dimmed, on the left, so the player sees what is being illustrated. | Accepted. Changed during review: the full-width gallery layout left a narrow plate and an empty field column beside it |
| Drawer layout | Free text only: no field selection or equipment. | Two columns: a 220px × scale portrait plate (the current portrait for a regeneration, or 「肖像／將在此現身」 on a warm floor light) with a one-line caption, and the prompt column with 補充提示詞, the hint, a taller textarea and the counter. The notes are combined into one paragraph in the smallest text size. At 1451x790 everything, including the rejection feedback, fits without scrolling the drawer body. At 2560x1440 the content sits at the top with empty space below, which keeps the footer in place. | Accepted |
| Drawer copy (§7.2) | The two gallery-dependent phrases replaced with creation copy. | Title 繪製肖像. Intro 「依照目前填寫的種族、血統、性別與外觀年齡，為角色繪製肖像。」. Notes 「肖像只保留一張；重新繪製完成後會取代目前的肖像。送出後可以繼續填寫，完成的肖像會出現在左側的肖像欄。」. Neither the character-data link nor the gallery's in-gallery note appears. | Accepted |
| Unavailable in the drawer (§12) | Submit disabled, reason shown, creation otherwise usable. | A seal-red bar carries the server reason with 重新檢查 at its right end. 開始生成 is disabled; the textarea keeps its text and stays editable. | Accepted |
| Rejection (§12) | The existing 「操作未完成」 message, input kept. | The existing feedback and its 查看伺服器訊息 link sit under the prompt, with the typed prompt intact. The log opened from it lifts above the drawer in creation mode. | Accepted |
| Nested focus | The drawer owns the keyboard and returns focus. | Opening moves focus to the drawer's close control; Tab stays inside the drawer; Escape closes only the drawer and returns focus to 生成肖像. After a successful submission focus returns to the slot: the opener when it can take focus, otherwise the slot's status line. | Accepted. Covered by the Vitest suite |
| Motion (§11) | Every animation follows the motion level. | `full`: breathing 2.4s, ring 1.2s. `reduced` and `off`: both 0s, so the frame is static and the heading and caption carry the state. | Accepted |
| Text floor (§11) | Nothing below `--text-xs`. | The smallest text in the slot measures 16px at 1451x790. | Accepted |
| Fit | No page-level horizontal scroll. | `documentElement.scrollWidth` equals the viewport width at 1451x790 in Storybook and at both reference viewports in the real game with the drawer open. | Accepted |

## Residual notes

- At 2560x1440 the drawer's lower half is empty. A taller plate would only
  enlarge a placeholder, so the space stays.
- After a confirmed reset the existing reset confirmation frame stays on
  screen until it is cancelled. This behaviour predates this change; the
  reset journey cancels it before continuing.
