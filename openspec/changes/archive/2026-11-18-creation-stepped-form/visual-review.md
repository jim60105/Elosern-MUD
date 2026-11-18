# Visual review: creation stepped form

Scope: the custom and concept modes of `CreationOverlay` after this change.
That covers the `CreationPortraitSlot` portrait column (empty state only),
the `CreationCustomSteps` rail, step pages and previous/next row, the footer
form message, and the `CreationConceptGuide` guide column beside the concept
field. The review compares the result with approved design
`docs/superpowers/specs/2026-11-17-creation-portrait-redesign-design.md`
§6 (stepped form), §7.1 (portrait slot, empty state), §8 (concept guide)
and §11 (accessibility), and with the reference prototype
`docs/design/creation-portraits/CreationPrototype.vue`. Portrait
generation, its states and its button belong to later changes and are
absent here on purpose.

This is a human review record. No automated test pins the questions, the
fill list, the labels or the markup reviewed here.

## Method

- Real production components in Storybook (`storybook dev`):
  `Overlays/CreationOverlay` (`CustomDraft`, `CustomStoryStep`,
  `CustomAllocationStep`, `CustomEmptySlot`, `CustomOverBudget`,
  `CustomIdentityError`, `CustomStoryError`, `CustomAllocationError`,
  `ConceptMode`, `ConceptPartialProposal`, `ConceptFullProposal`,
  `ConceptPending`), plus the component stories
  `Overlays/CreationCustomSteps`, `Overlays/CreationPortraitSlot` and
  `Overlays/CreationConceptGuide`. The `CreationCustomSteps` story builds its
  form from the real `useCreationOverlay`, so it cannot drift from the
  overlay. All panels are the synthetic story fixtures. Silhouettes are the
  committed built-in defaults named by the fixture table.
- Screenshots and measurements used headless `agent-browser` (a throwaway
  Chromium) at CSS viewports **1451x790** (`--ui-scale: 1`) and
  **2560x1440** (`--ui-scale: 1.4`). Each screenshot was opened as an image
  and judged visually. The numbers below come from DOM measurements.
- The real game was exercised on a fresh `pnpm run build` by
  `test_browser_creation_custom` (including the keyboard step journey at
  both reference viewports) and `test_browser_creation_viewport_pointer`
  (every field on its step at 1451x790, 1741x948 and 2560x1440).

## Findings

| Area | Expected (approved design) | Observed | Disposition |
| --- | --- | --- | --- |
| Composition (§6.1) | Fixed-width portrait column on the left, three steps on the right. | The portrait column is 300px × `--ui-scale` and the steps take the rest, capped at 1360px × scale and centred. A warm pool of light sits behind the portrait column. It is anchored to the column rather than the viewport, so at 2560x1440 it stays behind the portrait instead of drifting off to the left edge. That drift was found and fixed during review. | Accepted. The anchoring was fixed during review |
| Step rail (§6.1) | Three equal cells, each a button with number and title. The current step has a gold top rule and gold text, finished steps a dark-gold rule. Remaining points always shown on the 03 cell. | Native buttons show `01 身分`, `02 角色故事`, `03 能力配置` in the display face. The current cell adds a faint gold wash below its rule. Earlier steps carry the dark-gold rule and lighter text. 「剩餘 N 點」 sits at the right of the 03 cell on every step. The number is in the numeral face, turns seal red when negative, and shows 「—」 when the race has no resolved profile. | Accepted |
| Error mark (§6.2, §11) | The errored step gets a vermilion mark and 「需修正」, not colour alone. | The errored cell's rule turns seal red and a seal diamond plus 「需修正」 follows the title. The reported field gets a seal border, `aria-invalid` and the form message as its description. Focus lands on that field after the step opens. | Accepted |
| Form message placement | Existing behaviour and `data-testid` unchanged. | With the message above the footer, an error pushed the story step 46px past its page at 1451x790 (472/426). The local form message now sits in the footer between 重設 and 確認角色, beside the action that raised it. Every step fits again with an error showing (477/477). The server result region is unchanged. | Accepted. Changed during review |
| Identity step | Name and roll, sex, race, age, apparent age, subrace, race description. | Two columns: name and roll with sex, age with apparent age, race with subrace, and the race description underneath as a lore note with a gold left rule. The DOM keeps the established Tab order (name, roll, sex, age, apparent age, race, subrace), so keyboard journeys are unchanged. | Accepted |
| Story step | Affinity, background, personality, life story, habit. | The all-or-empty hint and the affinity fieldset span the width. The four texts form a 2 × 2 grid of three-row textareas. | Accepted |
| Allocation step | Allocated points, seven steppers and bars, two columns. | The total reads 「已配置點數 28 / 28」 with a large numeral, beside the existing budget briefing. The seven axes run in two columns with gold-gradient bars. | Accepted |
| Fit (§6.1, §11) | No internal scrolling on a normal step at 1451x790. No page-level horizontal scroll. | The step page's `scrollHeight` equals its `clientHeight` on all three steps at 1451x790, 1741x948 and 2560x1440, both with and without a form error showing. `documentElement.scrollWidth` equals the viewport width at each size. The real-game journey first failed at 1741x948: the story step ran 41px over, because the compact spacing used to switch on only below 800px of height. The shell and step spacing now use that compact rhythm (`--sp-3` gaps, `--sp-4` page padding) at every height, which also tightens the preset mode's body gap above 800px of height. | Accepted. Changed during review |
| Previous/next | 「上一步」 and 「下一步：〈標題〉」 below the step. | 上一步 is a ghost button, disabled on 01. 下一步 names the next title and is absent on 03. Both move focus into the newly shown step. | Accepted |
| Portrait slot (§7.1, empty) | Silhouette from the server table by sex and apparent age. Name below, or 「尚未命名」. | The table's alpha silhouette stands on the frame floor. The shared near-black alpha fill is lifted to an ink gradient inside this frame so the figure reads on the dark ground. Gold corner brackets and the band ornament sit above the name. An unnamed form shows 「尚未命名」 in muted paper. Input that matches no single entry leaves a neutral empty frame. There is no button and no generation copy, because this change ships no generation. | Accepted |
| Concept page (§8) | Guide on the left (four questions, the fill list, a note); title, flow line and a full-height field on the right, example in the placeholder. | The guide column is 340px × scale. 「可以寫些什麼」 lists the four questions with gold numerals. 「會幫你填好」 lists the nine fill items in two columns. The footnote 「性別與肖像不會自動產生，套用後請在自由創建中補上。」 sits at the bottom. The field fills the height in the serif face, and the example sentence is the placeholder. | Accepted |
| Guide marks (§8, §11) | Items with values are checked. | Filled items show a solid gold diamond and bright text. Open items show an outlined diamond. Hidden text 「（已填入）／（未填入）」 carries the state for assistive technology. The partial story marks 年齡與外觀年齡 (age 0), 種族與血統, 能力配點 (all zeros) and 個性 only. | Accepted |
| Text floor | Nothing below `--text-xs`. | The smallest rendered text measures 16px at 1451x790 and 22.4px at 2560x1440. | Accepted |
| Copy | Approved player-facing wording. | The custom primary action is now 確認角色 (§6.2), replacing 確認自訂. Concept: 「從一段描述開始」, 「套用後會帶你到自由創建，每一項都還能修改，確認後才會建立角色。」 and the prototype's four questions, fill list and footnote. The rail labels follow §6.1. | Accepted |

## Residual notes

- At 2560x1440 the identity and allocation steps leave empty space below
  their content inside the panel. The panel fills the column so the
  previous/next row stays put between steps. A taller layout would need
  more fields, not more spacing.
- The silhouette is the built-in default under an alpha mask. When live
  portrait generation lands, the same frame holds the generated portrait.
