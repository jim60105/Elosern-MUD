# Character portrait gallery storyboard

## Run the interactive storyboard

From the repository root, run `pnpm install --frozen-lockfile`, then
`pnpm run serve-storybook`. Open `Data / GalleryPanel / Storyboard`.
For an offline build, run `pnpm run build-storybook` and serve
`.storybook-out` over HTTP. No Evennia, LLM, or image-generation service is
required. All fonts, styles, and sample images are local assets.

The storyboard mounts the real gallery, drawers and face editor. Its top
control strip is a **story-only publication driver**, not a production service.
After submitting an action, choose **發布成功** or **發布拒絕** to publish its
explicit result. **檢視操作意圖** shows the submitted action and payload.
**發布初始圖庫** publishes the initial synthetic eight-row fixture again.
Offline portraits reuse the existing `art/defaults` artwork; the story media
adapter substitutes their URLs and illustrative face rectangles, while integration tests use protocol-valid
`/art/gallery` URLs. These are fictional subjects and equipment.

## Visual references

The implementation was designed after viewing all four reference images:

- [Gallery overview](角色肖像圖庫管理頁-圖庫主畫面.webp)
- [Generate portrait](角色肖像圖庫管理頁-生成新圖.webp)
- [Equipment binding](角色肖像圖庫管理頁-裝備綁定.webp)
- [Face selection](角色肖像圖庫管理頁-臉部框選.webp)

Shared visual language: ink-black surfaces, restrained gold borders, gold serif
headings, muted supporting copy, explicit pending/failure states, and selected
cards outlined in gold. The live gallery leaves the character column and the
bottom command area visible. Drawers sit on the right; face selection uses a
bounded two-column modal rather than replacing the game shell.

## Frames and transitions

| Frame | Trigger | Visible state and next action | Recovery |
| --- | --- | --- | --- |
| 1. Browse | Open **角色肖像圖庫** beside the live portrait, or open the storyboard | Eight cards; five server-counted filters; subject rail; grid/list controls; default crown; selected portrait details | Empty and unavailable stories show their explicit states; no invented portraits |
| 2. Inspect | Select a card; change filters or grid/list locally | Original card order, server chips and UTC timestamp; pending rows use a spinner; failed rows preserve the server label | Select another card; unavailable binding details are labelled as unavailable |
| 3. Generate | Choose **生成新圖** | Five optional character-data selections, committed equipment summary, raw prompt and Unicode code-point counter | **取消** or Escape returns focus to the opener without dispatch |
| 4. Submit and settle | Choose **開始生成**, then use the story publication controls | Controls lock during admission; only the matching successful result and its committed revision close the editor; published pending row appears in the grid | Publish rejection: retain the draft; **查看伺服器訊息** exposes the message. Oversized prompts are not silently truncated |
| 5. Bind | Select a completed card and choose **編輯設定** | Checkbox-only slot mask, current equipment, explicit server condition lines and warning cards; no item picker | Save requires a slot; **查看** selects the warning's card; cancel discards the draft |
| 6. Crop | Choose **臉部框選** | Original image with movable gold rectangle and resize handle; normalized numeric keyboard controls; square preview | Move/resize clamps to the original image. Cancel sends nothing; save sends rectangle coordinates only |
| 7. Default | Select a non-default completed card, choose **設為預設**, publish success | The next story publication moves the default marker | Rejection leaves the published marker unchanged |
| 8. Delete | Choose **刪除** | An inline confirmation identifies the destructive action | **取消** sends nothing; **確認刪除** submits once. The card disappears only after publication |
| 9. Monster | Select **測試魔物**, publish success | Single-card replacement explanation; generation has no field selection or free text; no equipment binding | Switch back through subject selection; all visibility follows published capabilities |

Standalone stories also cover locked, unavailable, empty, unmatched-binding,
and rejected-editor states. The production character-data shortcut opens the
existing puppet status drawer directly; the isolated storyboard describes that
transition instead of pretending to contain live character data.

## Deliberate differences from the reference pictures

The current gallery v1 wire panel does not expose full historical equipment
bindings, original pixel dimensions, or the currently resolved image. The UI
therefore never reconstructs these facts from equipment IDs or chips. Binding
conditions appear only from explicit `binding_warnings`; an absent entry is
marked unavailable. A default crown does not claim that the image is currently
resolved by equipment rules. Header and filter labels are static chrome;
counts, card labels and failure labels are server facts. Embedded failure codes
remain intact when the server includes them in its label.

The four shipped binding slots replace the reference's illustrative fifth
slot. Monster capabilities hide both optional fields and free text. Only the
puppet's generation drawer links to the puppet's character data. Existing
thumbnail face anchoring remains shared with the HUD; the editor preview clips
the selected normalized rectangle into its square output frame. Non-square
selections are letterboxed rather than stretched.

## Live verification boundaries

Storybook publishes synthetic state deliberately and never contacts a real
backend. Vitest application integration uses the actual Pinia store, protocol
validator, dispatcher, global mutation gate and result/narrative handling.
Visual browser verification covers the actual authored component surfaces.
Real image generation and matching rules remain owned by the previously
implemented deterministic backend, not by this UI change.
