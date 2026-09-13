# Proposal: webclient-gallery-actions

## Why

The gallery management mockups (`docs/design/elosern-redesign2/角色肖像圖庫管理頁-*.webp`)
show five mutations: generate a new image (生成新圖 drawer), set a card as
default (設為預設), delete a card (刪除), re-mark the face rectangle (儲存框選),
and save the binding editor (儲存綁定) — plus the subject-rail selection the
gallery panel reads. The backend service/gallery API already enforces every
domain rule (`request_gallery_image`, `set_default`, `remove_card`, typed
errors, the kind capability gates, the monster one-card 替換 semantics), and
the companion backend change `gallery-card-update-api` adds the two missing
in-place card writers (`update_card_face_rect`, `update_card_binding`) plus the
public subject-key resolver this change consumes; the panel presenter
(`webclient-gallery-panel`) already renders the read side — but there is no
`ui_action` path for any of it, so design §8.4's "management ops run through
the service API seam" still holds in the worst sense: the player can't reach
that seam from the webclient.

## What Changes

- Six new production `ui_action` adapters, each with one exact payload
  validator, typed rejection codes, and the standard dispatcher
  idempotency/base_revision/busy discipline:
  - `gallery.subject.select` — writes only the session selection store shipped
    by `webclient-gallery-panel` (the `options.dismiss` pattern);
    `affected_panels: ("gallery",)`.
  - `gallery.generate` — exactly `subject_key`, `fields` (subset of the closed
    catalog), `custom_prompt` (≤512 code points, control-free); calls
    `request_gallery_image`; the minted `image_id` travels in the result's
    bounded `data` slot; every typed backend error maps to a stable code with a
    zh-TW message (capacity kinds, kind-capability refusals, prompt bounds).
  - `gallery.default.set` — `subject_key`, `image_id` → `set_default`.
  - `gallery.card.delete` — `subject_key`, `image_id` → `remove_card`
    (confirm-gated client-side; the adapter never trusts a client to have
    confirmed).
  - `gallery.face_rect.update` — `subject_key`, `image_id`, `face_rect` →
    gallery-API validated rect write (server stores verbatim; never crops).
  - `gallery.binding.save` — `subject_key`, `image_id`, `slots` (non-empty
    subset of the four slot ids). Snapshot semantics per the session decision:
    the adapter captures the CURRENT normalized equipment snapshot over the
    enabled slots at save time (the unchanged backend `binding.snapshot`
    contract); the payload NEVER carries item keys.
- Binding-overlap warnings (規則重疊提醒) stay panel data computed by the shipped
  `webclient-gallery-panel` presenter (server-side only); the binding-save
  adapter changes nothing about them — the editor drawer displays the committed
  facts verbatim, so no matching rule ever reaches a client.
- Observability: one facade event per management mutation (`gallery_generate`
  already exists at the service seam; the webclient layer adds
  `gallery_action` info/warn with `subject`, `image_id`, `kind`, action id).
- All persistent mutations re-resolve every client-referenced identity — character-kind
  subject keys through the new public
  `world/art/service.py::resolve_gallery_subject_by_key` (the entity-derived
  kind needs its live entity for the age precondition and the equipment
  snapshot; the bare key alone is never trusted), registry kinds through the
  typed producer, cards through the tolerant read — and go ONLY through
  `world/art/service.py` / `world/art/gallery.py` public APIs (including the
  `gallery-card-update-api` writers). No direct record writes (dispatcher
  ownership contract).
  Subject selection instead validates current rail membership through the
  session-only panel selection store.

## Capabilities

### New Capabilities

- `webclient-gallery-management-actions`: the six adapters — payload grammars,
  typed-error → stable-code mapping, current-snapshot binding semantics,
  server-side overlap computation, session-state selection, and the zh-TW
  rejection copy.

### Modified Capabilities

- `webclient-action-dispatch`: the production registry allowlist gains the six
  `gallery.*` action ids (pinned-set scenario rewritten with them).

## Impact

- New `web/webclient/actions/gallery_actions.py` + registration in
  `web/webclient/actions/registry.py`.
- Consumes (does not own) the backend writers/resolver shipped by
  `gallery-card-update-api`. Scope note: six adapters + six mirrored payload
  validators + typed-error table is this batch's heaviest change; its
  drop-lever is shipping face-rect/binding save with shared test fixtures
  rather than per-action bespoke suites — never a missing validator.
- `web/static/webclient/js/elosern/protocol.js` action-payload validators for
  the six ids; pinned production action-set test extended.
- New test module covered by the existing recursive `web.webclient.actions`
  shard label; deterministic tests only (fake queue settles — no live SD/LLM).
- `docs/game/commands.md` untouched (D14 stands: management is webclient-only).

## Batch:

- depends-on: webclient-gallery-panel, gallery-card-update-api
- Code-conflict notes: owns `web/webclient/actions/gallery_actions.py`,
  `web/webclient/actions/registry.py` hunks, and the protocol.js action block
  (disjoint from the panel change's validator region; resolved by landing
  order). `web/webclient/presentation/registry.py` is owned exclusively by
  `webclient-gallery-panel` — this change touches no panel registration;
  `world/art/` writer hunks belong exclusively to `gallery-card-update-api`.
  Shares `web/webclient/presentation/registry.py` (panel registration is the
  panel change's; this change touches no panel registration). Depends on the
  panel change's selection store and rail vocabulary — land strictly AFTER it.
  `webclient-gallery-ui` consumes these action ids by name only.
