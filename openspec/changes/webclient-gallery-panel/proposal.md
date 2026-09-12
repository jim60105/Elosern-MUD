# Proposal: webclient-gallery-panel

## Why

The gallery backend is fully shipped (design
`docs/superpowers/specs/2026-09-08-character-gallery-art-design.md`, all seven
decomposed changes plus `gallery-monster-generation`/`gallery-failure-visibility`
follow-ups archived), but design §12.4 records the live gap: the Vue production
client consumes `face_rect` everywhere a portrait renders, yet there is no
management surface. Design §8 lists the manager as TODO intent, and §8.4 says
that until it ships, management ops run only through the service API seam. The
four mockups under `docs/design/elosern-redesign2/角色肖像圖庫管理頁-*.webp` are
the approved shape of that surface.

The player (and, per the session decision, every gallery-bearing subject) has no
way to see their gallery, filter it, generate a new image from ticked data
fields, set a default, or delete a card from the webclient.

## What Changes

- New `gallery` presentation panel (schema version 1), subject = the rendered
  puppet, presenting ONE selected gallery-bearing subject's gallery per render:
  a bounded `subjects` rail (kind, subject key, display name, ordering facts) and
  the selected subject's `cards`, `filters` counts, `equipment_summary`
  read-model, and error surface.
- Subject rail scope: the puppet itself always first; then live characters with
  a gallery — active-party companions before other characters (design §8.3);
  then the closed `MONSTER_TIER_REGISTRY` bestiary entries (the monster kind's
  gallery-bearing subjects, bounded by the registry). The scene kind is never
  offered (no gallery, per `art-gallery-kind-capabilities`).
- Per-card server-authored presentation: media URL (validated exactly as the
  art-panel catalog does), truthful status, binding-slot chips derived from the
  card's binding mask (主手/副手/防具/飾品 vocabulary), custom-vs-default face-rect
  chip, 目前預設 crown flag, formatted `created_at`, and the card's
  `requested_fields` provenance.
- Synthetic status entries: pending gallery jobs render as 生成中 entries and the
  record's `last_error_code`/`last_error_at` renders as one failed entry carrying
  「暫時無法生成，稍後再試」 — AI-offline generation is a surfaced failed state,
  never a broken panel (D13/§12.3.1).
- Server-computed filter-tab counts for 全部 / 預設 / 已綁定 / 生成中 / 失敗;
  newest-first card order (presentation sort only — the record stays
  append-ordered).
- Session-scoped subject selection with the same retirement discipline as the
  options layer: default selection is the puppet; an unknown selection falls
  back to the puppet; selection is retired at disconnect, unpuppet, and account
  character switch. The `gallery.subject.select` action (registered by
  `webclient-gallery-actions`) writes only this session state.
- Exact-shape Python validator + JavaScript mirror in
  `web/static/webclient/js/elosern/protocol.js` with the `PANEL_ALLOWLIST` entry
  and the schema-version parity contract; additive wire change (new panel key
  only).
- No mutation of any gallery record or job state anywhere in this change; the
  presenter reads through `world/art/gallery.py`, `world/art/gallery_match.py`,
  the kind-capability declaration, and a new bounded read-only pending-job
  accessor.

## Capabilities

### New Capabilities

- `webclient-gallery-panel`: the `gallery` read model — subject-rail scope and
  companion-first ordering, card/chip/crown/filter-count/error surface, the
  equipment summary read-model, session-scoped selection lifecycle, and the
  read-only presenter contract.

### Modified Capabilities

- `webclient-oob-protocol`: the registered-panel allowlist gains `gallery`
  (registration/dispatch wording only; no envelope change).

(No action-side delta: the `gallery.subject.select` registration belongs to
`webclient-gallery-actions`, which owns the action registry / protocol.js
action-list conflict surface. This change ships the selection store it writes.)

## Impact

- New presenter/validator `web/webclient/presentation/gallery.py`; registration
  in `web/webclient/presentation/registry.py`; session-scoped selection store in
  the presentation layer (wired alongside the options-state retirement seams).
- Client mirror in `web/static/webclient/js/elosern/protocol.js`
  (`PANEL_ALLOWLIST.gallery = 1`, per-panel validator) + the
  `webclient-vue-application` protocol mirror table.
- One read-only accessor for a subject's in-flight gallery jobs in the art queue
  surface (no new writers).
- New focused test modules registered in `.github/evennia-shards.json` in the
  same change; dual-direction Python/JS parity tests extended.
- No Vue component consumes the panel yet — `webclient-gallery-ui` does.

## Batch:

- depends-on: (none — first of the gallery-UI batch)
- Code-conflict notes: `web/webclient/presentation/registry.py` and
  `presentation/gallery.py` are owned EXCLUSIVELY by this change;
  `web/webclient/actions/registry.py` is owned exclusively by
  `webclient-gallery-actions`; `protocol.js` is touched by both changes but in
  disjoint regions (panel validator/allowlist vs action payload validators),
  resolved by landing order. `webclient-gallery-ui` owns `AppClient.vue`,
  `web/webclient-app/component-manifest.json`, and new components — no overlap
  with this change. Scope note: this change is the batch's ceiling workday;
  its drop-lever if it overruns is deferring the equipment-summary display-name
  enrichment (raw keys first), never the payload key set.
