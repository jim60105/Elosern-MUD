# companion-portrait-lineup

## Why

The party quickbar wastes vertical space and understates companions as characters. Replace it with overlapping, equally sized standing portraits left of the controlled character. Possession becomes a visible body swap; AVG speaking focus brings the speaking companion above the overlapping listeners.

## What Changes

- The party quickbar island is **removed** from the `vitals` anchor and the stage entirely. No compact cell, no header, no HP hairline, no `同伴 N / 4` count. The 同伴 ‧ 隊伍 drawer remains reachable through the character-status drawer's 同伴 ‧ 隊伍 control, which already exists.
- Companion standing portraits share the controlled character's full size and ground line, overlapping leftward in party order within the stage's left half. Only overlap compresses; no shrinking/lift/depth-dim ramp. Solo keeps its existing position. Portraits remain non-interactive decorative art.
- During possession the controlled companion exchanges exactly its former slot with A. The status identity is corrected to the session actor with its existing string type; every other owner-keyed status hybrid field stays unchanged.
- Companions reuse the existing listener dim unless speaking in committed dialogue state; a speaking companion temporarily gets the highest z without moving, then restores its baseline z.
- **Server: party panel v2** lifts the portrait_ref seam: the presenter resolves each companion NPC's default gallery portrait into `portrait_ref` (an opaque key that resolves through the art panel's `portrait_catalog`), keeping null when no gallery portrait exists. The schema version bumps to 2 on the server presenter and on all three validators (server, UMD mirror, Vue store mirror). A companion without a gallery portrait shows the initial-letter placeholder (the same `portraitGlyph` fallback the quickbar used).
- `party-helpers.js::portraitFor()` already resolves `portrait_ref → portrait_catalog → entry`. The lineup reuses this helper to resolve each companion's portrait entry; the stage actor's `ReferenceArtwork` component renders it with the same truthful placeholder as the player portrait, or the initial-letter fallback.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `webclient-contextual-hud`: remove the party quickbar; add equal-size overlapping portraits, possession exchange, temporary speaking focus and bounded left-half geometry.
- `webclient-party-panel`: schema v2 accepts null or 1–32 ASCII decimal digits for portrait refs; v1 is unsupported, with no shim.
- `webclient-art-panel`: exploration membership adds live co-located companions after existing members, preserving the cap and truthful unavailable entries.
- `webclient-possession-presentation`: status identity addresses the controlled session actor while all other hybrid fields retain their existing contract.
- `webclient-character-roster`: preserve the authenticated account's owned A/current portrait while B is possessed; keep pending/capacity facts owned and combat lock keyed to the actual session actor.

## Impact

- `web/webclient/presentation/party.py`: presenter reads each NPC companion's default gallery portrait (via `world.art.gallery.record_for` with `create=False`), emits the matching `portrait_catalog` ref key, or null. Schema version 1 → 2.
- `web/webclient/presentation/party.py`: validator `_validate_slot` allows non-null `portrait_ref` at schema version 2.
- UMD `protocol/constants.js` and `protocol/panels/misc.js`: party v2 allowlist and exact decimal-string/null validator, reused directly by Vue.
- `web/webclient-app/components/PartyStrip.vue`: **deleted**.
- `web/webclient-app/AppClient.vue`: removes PartyStrip from the `#vitals` slot; renders the companion lineup as multiple StageActor instances inside the `#actor-left` slot.
- `companion-lineup.js`: pure equal-size overlap/baseline-z geometry and exact possession exchange.
- `CompanionLineup.vue`: equal-size StageActors with responsive dialogue clearance and committed paint-only speaking focus; foe lineup untouched.
- `web/webclient-app/components/HudFrame.vue`: `[data-anchor="actor-left"]` overflow set to `visible` (like `actor-right` during combat) so the lineup can extend leftward beyond the anchor box.
- Tests: remove `party_strip.test.js`, `PartyStrip.stories.js`; add `companion-lineup.test.js`, `CompanionLineup.stories.js`; update `app_client_drawers.test.js` (party strip assertion removal); update `deferred_surfaces_absent.test.js` (manifest); update `component-manifest.json`.
- Stories: new `CompanionLineup` story with 0/1/2/4 companions, possession swap, and placeholder fallback.
