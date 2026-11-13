# Design: gallery image page and capability-driven footer

## Context

- `components/DetailFooter.vue`: props `reason`, `reasonTone`, `reasonRole`,
  `buttons[{key,label,tone,enabled,pressed,glyph,testid,describedByReason}]`;
  emits `press(key)`; disabled buttons stay focusable with `aria-disabled`.
  `QuestDetail.vue` shows the arming pattern (armed abandon, cancel takes
  focus).
- `GalleryDetailRail.vue` today renders preview, badges, conditions from
  `binding_warnings`, and the affordances; `gallery-copy.js::galleryDate`
  formats relative/exact time (日期不詳 for impossible values).
- The quest detail condition row `.quest-detail__cond` is the cell grid to
  follow (label, one line, one note per cell).
- v4 card rows carry `chips`, `label`, `status`, `is_default`,
  `binding_present`, `created_at`, `artwork`; per-card binding condition lines
  exist only in `binding_warnings` entries.

## Goals / Non-Goals

**Goals:** page component and pure footer/ribbon functions.

**Non-Goals:** landscape layout (`gallery-landscape-page`); dispatching
(the window maps `press` keys to actions); editors.

## Decisions

### D1. Contract (verbatim)

```js
// GalleryImagePage.vue
props: {
  panel:        { type: Object, required: true },  // committed v4 panel
  subject:      { type: Object, default: null },   // committed subject row of `selected`
  groupLabel:   { type: String, default: null },
  categoryLabel:{ type: String, required: true },
  selection:    { type: Object, default: null },
     // { type: "card", row } | { type: "official", row } | { type: "empty" }
  now:          { type: Number, required: true },
  disabled:     { type: Boolean, default: false },
}
emits: ["press"]   // keys below
```

Footer keys: `delete`, `face`, `stage`, `binding`, `default`, `regenerate`,
`generate`, `official-geometry-clear`, `official-face`, `official-stage`,
`official-select`, `official-clear-selection`.

### D2. `galleryFooter(selection, capabilities) -> { buttons, note }`

```
if !selection || selection.type === "empty": [generate "生成新圖" primary]
card, status "pending": [] and note "生成中"
card, status "failed":  [regenerate "重新生成"]
card, status "card":
  supports_card_delete -> delete "刪除" (tone danger)
  supports_face_rect   -> face "臉框"
  supports_stage       -> stage "舞台位置"
  supports_bindings    -> binding "綁定裝備"
  max_cards === null   -> default "設為預設" (enabled = !row.is_default,
                          reason "目前預設" when disabled)
  max_cards === 1      -> regenerate "重新生成"
official:
  !supports_personal_official_preferences -> []
  else: official-geometry-clear "清除個人調整",
        supports_face_rect -> official-face "臉框",
        supports_stage     -> official-stage "舞台位置",
        row.is_current ? official-clear-selection "清除選取"
                       : official-select "設為預設"
```

Planner decisions (flagged in the programme report): a failed row offers only
重新生成 because no backend action deletes a failed row (D5 lists 刪除); a
current official entry keeps 清除選取 so the existing clear-selection action
stays reachable (D5 lists only 設為預設).

### D3. Delete arming

Local `armed` ref. First `delete` press sets `armed = true` and replaces the
footer with `[confirm-delete "確認刪除" danger, cancel "取消"]`, focus to
取消, reason `刪除後無法復原。` with `reasonRole: "alert"`. `confirm-delete`
emits `press("delete")`; `cancel`, Escape on the page, or a change of
`selection` resets `armed` without emitting.

### D4. Facts

- 圖片: `row.label` (official: `官方圖片`), note per selection type: official
  `唯讀，只能調整個人的臉框與舞台位置。`, one-card kind
  `只保留一張，重新生成會替換原圖。`, empty `尚無圖片`.
- 生成時間: `galleryDate(row.created_at, now)` relative + exact (stored and
  failed rows).
- 狀態 (only `capabilities.max_cards === null`, card rows): 目前預設 with the
  crown glyph, 備用圖片, 生成中, 生成失敗.
- 標記: `row.chips` verbatim; omitted when empty.
- 綁定條件: the `conditions` of the `binding_warnings` entry whose `image_id`
  equals the row's; omitted otherwise (the panel carries no other per-card
  condition lines — flagged limitation).
- `panel.description` non-null → letter box with heading 描述.
- `galleryRibbon(categoryLabel, groupLabel)` → `categoryLabel` or
  `${categoryLabel}・${groupLabel}`.

### D5. Layout

Portrait: grid `art | facts`; art column height 100% of the page body with
`aspect-ratio: 9 / 16`; facts column scrolls with `scrollbar-gutter: stable`;
footer pinned. Tokens only (style lint as in `gallery-wall-component`).

## Review

Fact-cell typography, spacing and resemblance to the approved prototype page
are human-reviewed in Storybook at both viewports.

## Risks / Trade-offs

- [Binding conditions appear only for overlapping cards] → existing panel
  contract; a later change may add per-card conditions if the user wants them.
