# companion-portrait-lineup

## Why

The party quickbar island (four compact cells with HP hairlines) was designed for at-a-glance status, but companions as game characters deserve the same standing-portrait presence the player and the dialogue host already have. The quickbar also wastes vertical space in the left column. Replacing it with a depth-staged portrait row in the actor-left area — mirroring the foe line-up on the right — gives the party visual weight and turns possession from a banner-only indicator into a visible body swap.

## What Changes

- The party quickbar island is **removed** from the `vitals` anchor and the stage entirely. No compact cell, no header, no HP hairline, no `同伴 N / 4` count. The 同伴 ‧ 隊伍 drawer remains reachable through the character-status drawer's 同伴 ‧ 隊伍 control, which already exists.
- Companion standing portraits are rendered in the `actor-left` anchor alongside the player's portrait, as a left-growing depth-staged row: the currently controlled character (the player character, or the possessed NPC during possession) stands in front at the group's rightmost position, and each companion stands behind it going left in party order, slightly overlapped and progressively smaller. The group right-aligns to the actor-left anchor's standard position, and the row grows leftward within the left half of the stage, compressing overlap when the group grows. The portraits are non-interactive decorative art — no focusable element, no pointer events — matching the existing portrait anchor contract.
- During possession: the controlled character swaps to the rightmost slot. The player character A's portrait moves leftward into the companion row in the position the possessed NPC formerly held (or an arbitrary position; the key invariant is: the rightmost figure is always the currently controlled character).
- **Server: party panel v2** lifts the portrait_ref seam: the presenter resolves each companion NPC's default gallery portrait into `portrait_ref` (an opaque key that resolves through the art panel's `portrait_catalog`), keeping null when no gallery portrait exists. The schema version bumps to 2 on the server presenter and on all three validators (server, UMD mirror, Vue store mirror). A companion without a gallery portrait shows the initial-letter placeholder (the same `portraitGlyph` fallback the quickbar used).
- `party-helpers.js::portraitFor()` already resolves `portrait_ref → portrait_catalog → entry`. The lineup reuses this helper to resolve each companion's portrait entry; the stage actor's `ReferenceArtwork` component renders it with the same truthful placeholder as the player portrait, or the initial-letter fallback.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `webclient-contextual-hud`: the party quickbar island requirement is **removed**; the stage portrait-anchor requirement adds the companion lineup; the island-stack requirement no longer names the party quickbar; the visibility-matrix row for the party quickbar is removed; the portrait-standing requirement adds the lineup geometry, the depth staging, the possession swap, and the left-half span.
- `webclient-party-panel`: the party panel bumps to schema version 2 with non-null `portrait_ref` support; the validator accepts a string portrait_ref in v2 while v1 remains null-only.

## Impact

- `web/webclient/presentation/party.py`: presenter reads each NPC companion's default gallery portrait (via `world.art.gallery.record_for` with `create=False`), emits the matching `portrait_catalog` ref key, or null. Schema version 1 → 2.
- `web/webclient/presentation/party.py`: validator `_validate_slot` allows non-null `portrait_ref` at schema version 2.
- `web/static/webclient/js/elosern/protocol/panels/party.js` (UMD mirror): validator accepts non-null `portrait_ref` at v2.
- `web/webclient-app/stores/elosern-store.js` (Vue store mirror): party panel allowlist unchanged (already names `party`); schema version assertion updated to v2.
- `web/webclient-app/components/PartyStrip.vue`: **deleted**.
- `web/webclient-app/AppClient.vue`: removes PartyStrip from the `#vitals` slot; renders the companion lineup as multiple StageActor instances inside the `#actor-left` slot.
- `web/webclient-app/components/companion-lineup.js` (new): pure geometry helper mirroring `foe-lineup.js` — `companionSlots(count)`, `companionLineupSpan(count)`, scales/exposed/lift tables for up to 4 companions + 1 controlled.
- `web/webclient-app/components/CompanionLineup.vue` (new): the companion lineup component — a row of StageActor instances in the actor-left anchor, depth-staged, right-aligned to the anchor's natural position, growing leftward.
- `web/webclient-app/components/HudFrame.vue`: `[data-anchor="actor-left"]` overflow set to `visible` (like `actor-right` during combat) so the lineup can extend leftward beyond the anchor box.
- Tests: remove `party_strip.test.js`, `PartyStrip.stories.js`; add `companion-lineup.test.js`, `CompanionLineup.stories.js`; update `app_client_drawers.test.js` (party strip assertion removal); update `deferred_surfaces_absent.test.js` (manifest); update `component-manifest.json`.
- Stories: new `CompanionLineup` story with 0/1/2/4 companions, possession swap, and placeholder fallback.
