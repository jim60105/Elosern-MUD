# Design: webclient-gallery-panel

## D1 — One panel, one selected subject, a rail of subjects

The mockups show a gallery for one subject at a time with a filter bar and a
detail rail. The `gallery` panel renders exactly that: a bounded `subjects` rail
plus the fully server-authored payload for the ONE selected subject. This keeps
every payload inside the 65,536-byte OOB envelope (a full multi-subject gallery
could never fit) and matches how every existing panel renders verbatim.

## D2 — Subject rail scope and ordering

The rail entries are derived, never stored:

1. The rendered puppet (the player) — always first, `is_puppet: true`.
2. Live characters with a gallery-capable subject (explicit named
   `portrait_policy` subjects and every account character carrying a gallery
   record), ordered active-party companions first, then the rest (design §8.3).
   Ordering facts come from the party surface, not client logic.
3. Bestiary subjects: every `MONSTER_TIER_REGISTRY` key resolved through the
   kind's typed producer — bounded by the registry itself, monster kind declares
   one card and no bindings.

Scene-kind subjects are never listed (`art-gallery-kind-capabilities`: no
gallery). The rail is capped (design task fixes the bound; 24 rows named in the
validator) and truncated by these precedence groups, never mid-group.

## D3 — Session-scoped selection is presentation state, not game state

The selected subject key lives in a per-session presentation store retired with
the same lifecycle as the options layer: dropped at disconnect, unpuppet, and
account character switch. Default selection is the puppet; a stored selection
that no longer names a rail entry silently re-selects the puppet at render
(never an error). `gallery.subject.select` (registered by the companion
`webclient-gallery-actions` change, which owns the action-registry conflict
surface) writes only this store — the `options.dismiss` precedent — it touches
no gallery record, and its completion publishes the panel update.

## D4 — Card projection is a read, never a second truth

The presenter composes each card row from `cards_for(subject)` (tolerant reads —
a malformed stored card is already skipped by the model layer and reported
there), the presenter-side URL builder discipline of
`art-gallery-resolution` (validated stored identity, confinement, closed
extension set), and chip derivation:

- binding chips: one per masked slot id — `weapon_main`→主手,
  `weapon_off`→副手, `armor`→防具, `accessories`→飾品 (server-authored labels;
  a bound card also carries a 已綁定 chip fact).
- face chip: 自訂臉框 when `face_rect != DEFAULT_FACE_RECT`, else 預設臉框.
- crown fact: `is_default` from `default_image_id`.

No chip logic exists client-side.

## D5 — Synthetic statuses: pending and failed entries

A gallery card is only appended on success, so 生成中 and 失敗 rows are derived,
not stored:

- `pending`: one read-only accessor over the art queue surface returns the
  subject's in-flight gallery job ids and minted timestamps (bounded). Each
  becomes one synthetic `status: "pending"` row (spinner card, name placeholder
  「風之歌（生成中）」-style copy is server-authored via the pending label fact).
- `failed`: the record's `last_error_code`/`last_error_at`
  (`gallery-failure-visibility`) becomes one synthetic `status: "failed"` row
  with the bounded 「暫時無法生成，稍後再試」 line. The stable error code is
  carried; the message is server-authored.

Filter counts 全部/預設/已綁定/生成中/失敗 are computed server-side over exactly
these rows (全部 = valid cards + pending + failed-when-no-cards-match? — no:
全部 counts every row the panel lists). Counts travel as data; the client draws
tabs verbatim.

## D6 — Equipment summary and capability flags

For a kind whose declaration supports bindings/fields (character), the panel
carries `equipment_summary`: the four-slot current normalized snapshot enriched
with registry display names (`world/lore/items.py` read-only), accessory count
n/5, plus the capability flags (`supports_bindings`,
`supports_field_selection`, `supports_free_text`, `max_cards`) so the UI renders
binding/生成 affordances truthfully per kind without duplicating the
declaration. Monster subjects carry `equipment_summary: null` and
`supports_bindings: false`.

## D7 — Ordering and sort are facts, not behavior

Cards are listed newest-first (`created_at` descending, append order as the
stable tiebreaker) — the mockups' 最新優先 default. List/grid view and any
non-default sort are client-local presentation state (like art focus); the
payload order is authoritative.

## D8 — Failure surface stays a reported state

Every degrade path is the panel's own unavailable form (registry-owned) or a
truthful row; SD offline NEVER degrades the panel (D13). A subject with no
record renders `cards: []` with zero counts — available, empty, never
unavailable.

## D9 — Card labels and overlap warnings are presenter facts

Cards carry no name in the stored contract, so each row's zh-TW display line is
derived server-side (timestamp-anchored label; pending rows suffix 「生成中」).
規則重疊提醒 travels as `binding_warnings`: the presenter takes the current
snapshot once and lists (≤5, newest-first) every non-default bound card whose
masked slots all evaluate equal to that snapshot — cards that could win display
for the equipment being worn right now, so saving an overlapping binding risks a
priority surprise. Condition lines are server-authored (accessories carry the
「任一」 phrasing). No client ever evaluates a match.
