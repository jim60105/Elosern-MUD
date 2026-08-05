## Why

The `art-assets` delivery unit (roadmap 22) now owns every scene and portrait asset record, status,
same-origin media URL, and placeholder primitive, but the WebClient still renders the foundation
placeholder: the GoldenLayout `art` component registers an "unavailable" message
(`web/static/webclient/js/plugins/goldenlayout.js`), no `art` panel is registered in the
presentation registry, and there is no scene renderer, contextual portrait overlay, or OOB art
update. Roadmap item 23f (`webclient-art-panel`) is the graphical consumption slice: it depends only
on the landed `art-assets` (22) and `webclient-oob-foundation` (23a) changes, renders approved scene
and portrait assets when present, and degrades every missing, pending, failed, invalid, or offline
state to truthful placeholders so the deterministic game stays fully playable with the worker
command fixed to fail.

## What Changes

- Register a read-only version-1 `art` panel beside `status`, `context_actions`, `local_map`,
  `services`, and `creation`. It is available in `exploration` and `combat` modes and uses the
  registered common unavailable form in `creation` mode. The payload contains exactly
  `schema_version`, `available`, `kind`, the current room's validated scene (subject key, asset
  status, same-origin URL, aspect, alternative text, and truthful placeholder kind/label) and a
  bounded `portrait_catalog` keyed by the opaque IDs of currently focusable present entities. Each
  catalog value contains the server-resolved subject key, status, URL/placeholder, aspect,
  alternative text, and display context (name plus role/target label).
- Derive the scene and catalog through read-only seams only. The scene comes from the current room's
  validated `scene_archetype` through `world.art.presenter.resolve_scene`; catalog entries resolve
  each present entity's portrait subject through `world.art.presenter.resolve_entity`, which
  dispatches by kind: named characters through the explicit portrait policy and both adult age gates,
  generic monsters through their bestiary `MONSTER_TIER_REGISTRY` archetype (no character age gate),
  and anything else to a truthful unavailable placeholder. In combat mode the catalog keys are the
  combat-session participant identities already emitted by `context_actions`; in exploration mode they
  are the present entities in the current room (dialogue hosts and characters carrying an explicit
  named portrait policy) in deterministic room-contents order. The browser never constructs a subject
  key, URL, status, or alternative text, and the payload never exposes `out_path`, the store root, or
  a rejected/underage prompt.
- Advance the `context_actions` combat panel to schema version 2: each participant now carries a
  nullable server-authored `portrait_ref` referencing that participant's opaque `art` catalog key —
  including a catalog entry that resolves to a placeholder card — instead of the version-1 "always
  null" rule; it is `null` only when the participant is absent from the catalog. The reference comes
  from one shared catalog-key mapper so the combat and art panels cannot drift. The browser still
  never derives a portrait from entity data; it only selects among verified catalog values. Versioned
  panel schema evolution, not a compatibility break; the project is unreleased.
- Replace the GoldenLayout placeholder `art` component with the approved scene renderer: 16:9
  cover-style cropping, scene label and alternative text visible outside the bitmap, click or Enter
  on the focused image opening the same full view, Escape closing it. When the current scene is
  pending and a prior scene is already rendered, the panel retains the prior image visibly dimmed and
  labelled `目前場景圖片生成中`; without a prior image, and for failed or invalid assets, it uses the
  scene placeholder. The panel never silently presents old art as current.
- Add the contextual 3:4 portrait overlay at bottom right without covering the scene label or
  required status: it shows the focused entity's name and role/target context, has its own accessible
  full-view control, shows no card when there is no focus, and shows a portrait placeholder card
  (rather than removal) when a focused character exists but its portrait is missing. No stacked
  portraits and no history gallery.
- Keep contextual focus entirely client-local: the KeyboardRouter emits a focus event and the art
  renderer selects a supplied catalog value; there is no focus mutation message, and a full snapshot
  preserves focus only when that catalog ID survives replacement (otherwise exploration has no
  portrait focus and combat selects the first valid target in deterministic presenter order). Menu
  descriptors reference catalog entries by opaque ID; this change ships the combat descriptors
  (`portrait_ref`), while exploration-menu descriptors that reference the same catalog arrive with the
  exploration-menu delivery unit (23d).
- Add targeted OOB art updates. When the art worker completes an asset, a bounded server-side
  notification reaches the presentation layer, which re-renders the `art` panel for each connected
  WebClient session whose current scene or portrait catalog references that subject key and publishes
  an affected-panel update at a newer revision. A late completion for an old room or a
  no-longer-present entity references nothing current and therefore never replaces the visible panel.
  Room or present-entity-set changes replace the art payload through ordinary presentation updates,
  and every admitted combat action publishes `status`, `context_actions`, and `art` together at one
  revision so a defeated, fled, or settled participant leaves the portrait catalog in the same update.
- Preserve every degradation rule: scheduler disabled, worker unavailable or timed out, missing file
  for a done record, invalid output, browser image load failure, OOB disconnect during completion,
  and LLM-unavailable all resolve to approved placeholders with bounded diagnostics; gameplay never
  blocks on a job, and the adult gate is never weakened.
- Extend the Node, Evennia, and managed Playwright gates with art-panel journeys: done, missing,
  pending, failed, scheduler-disabled, and missing-file states; same-origin URL restriction; adult
  prompt gate (rejected content never reaches the browser payload); client-local catalog focus
  switching; late old-subject completion; keyboard full view, Escape, alternative text, and
  placeholder accessibility; and 16:9/3:4 usability at both supported desktop viewports.
- Add no backward-compatibility adapter or persisted-data migration; the project is unreleased, and
  Telnet play and the deterministic core are unchanged.

## Capabilities

### New Capabilities

- `webclient-art-panel`: The read-only version-1 `art` panel (scene payload plus bounded
  `portrait_catalog`), the scene renderer with placeholder/dimmed-retention/full-view behavior, the
  contextual portrait overlay with client-local focus selection, server-initiated targeted OOB art
  updates, the full degradation contract, and the Node/Evennia/browser acceptance boundary.

### Modified Capabilities

- `webclient-combat-menu`: The `context_actions` panel schema advances from version 1 to version 2 —
  participants carry a nullable server-authored `portrait_ref` catalog key (populated in combat mode,
  including placeholder entries; null only when absent from the catalog) instead of the version-1
  "always null" rule, and every admitted combat action publishes `status`, `context_actions`, and
  `art` together at one revision so a removed participant cannot linger in the portrait catalog, while
  the browser still never constructs a portrait subject key or URL.
- `webclient-desktop-shell`: The `art` component renders the validated `webclient-art-panel` payload
  instead of remaining a placeholder; it shows a truthful scene placeholder whenever the asset is
  missing, pending-without-prior-image, failed, invalid, or the OOB channel is unavailable.

## Impact

- New files: `web/webclient/presentation/art.py` (exact schema-version-1 validator + read-only art
  presenter), a frozen no-mutation art view under `world/rules/` (scene archetype resolution plus the
  bounded present-entity focus catalog, following the `combat_view`/`service_view` pattern), a
  DOM-independent `art_panel.js` reducer/renderer model and its Node tests under
  `web/static/webclient/js/elosern/`, the GoldenLayout art component renderer, and the
  `web/tests/browser/` art acceptance file.
- Edits to landed implementation files: `web/webclient/presentation/registry.py` (register the `art`
  panel), `web/webclient/presentation/combat_panel.py` (schema v2) and `world/rules/combat_view.py`
  (shared roster query + populated `portrait_ref` via the catalog-key mapper),
  `web/static/webclient/js/elosern/protocol.js` (panel allowlist + `art` validator + `context_actions`
  version-2 validator, dual-parity guarded), `web/static/webclient/js/plugins/goldenlayout.js` (real
  art component replacing `registerUnavailable`), the combat-action completion affected-panel set
  (adds `art`), the coordinator/publication seam for targeted art updates, a decoupled completion
  notification from the `world/art/` settle path (emitted from the `deferToThread` success callback
  on the reactor thread, consumed by the presentation layer, so `world/art/` stays deterministic and
  never imports `web/`), and browser fixtures.
- New implementation files: the frozen no-mutation art view and `portrait_catalog_key` mapper under
  `world/rules/art_view.py`, the additive `resolve_entity` dispatcher in `world/art/presenter.py`,
  `web/webclient/presentation/art.py` (panel validator + presenter), `web/webclient/presentation/art_push.py`
  (completion subscriber), the DOM-independent `art_panel.js` model and the GoldenLayout art renderer,
  and their tests.
- Reuses the landed `world/art/` store/queue/presenter primitives, the OOB epoch/revision protocol,
  the combat participant seam, the locked Playwright dependency, and the isolated browser harness;
  adds no runtime dependency, database migration, LLM call, image-service call, `world.ai` fragment,
  mobile scope, or backward-compatibility layer. The repository deterministic-path contract test
  stays green with no edits.
