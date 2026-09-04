# Proposal: webclient-align-05-party-hud

## Why

The draft carries two party surfaces the live client cannot build: the left-HUD companion
quickbar (`.comps`: 同伴 N/4, per-companion avatar/name/HP bar/state row with the combat `aN`
token, and a dashed `+ 邀請` slot) and the 同伴 · 隊伍 drawer (`dr-party`: compbig rows,
請其離隊, the empty-slot invite rule, and the fixed 跟隨規則 card). Both were explicitly deferred
by the showcase contract as unbacked — change 04 landed the `party` read model, so both can now
exist truthfully.

## What Changes

- New left-HUD party island bound to the committed `party` panel: header `同伴` + `N / 4`;
  per-companion cell (avatar initial-letter fallback, display name, HP hairline bar, state row
  `180/220 親睦`, joined combat token prefix `a2` when the companion fights in the committed
  combat panel); pad with dashed `+ 邀請` cells to the 4-slot row; empty party renders one row
  of dashed invite slots. Clicking a slot or the island opens the drawer. The island renders in
  exploration and combat; it is hidden in creation mode per the visibility matrix.
- New 同伴 · 隊伍 drawer on the shared right-anchored drawer shell: `N / 4` sub-count, compbig
  rows (name, 羈絆 stage, HP bar + numerals, joined 參戰 token, 請其離隊 →
  `explore.party_leave` confirm contract), the 空位 row naming the invite
  rule with `邀請當前 NPC…` → `explore.party_invite` (enabled only when the committed
  exploration panel carries an invite-capable target), and the three fixed 跟隨規則 lines.
  The draft's per-row 詳情 button is dropped: it would open the player's status drawer — there
  is no companion-status read model to back it (documented deviation in design.md).
- Deferred-surface bookkeeping: the party/companion deferral entries (test patterns +
  `DEFERRED_SURFACES` record) are removed, the two new components gain manifest entries +
  deterministic offline stories in the same change, and the showcase deferred-surface
  requirement is modified to drop the Party panel from the deferred list.

## Capabilities

### New Capabilities

(None)

### Modified Capabilities

- `webclient-contextual-hud`: ADDED — the party quickbar island and the 同伴 · 隊伍 drawer
  requirements (backed-fields-only rendering, join-by-identity tokens, mutation contract).
- `webclient-component-showcase`: MODIFIED — the deferred-surface requirement no longer lists
  the Party/companion panel (it now has its `party` read model); event-log toasts and the
  objective tracker stay deferred.

## Impact

- New `PartyStrip.vue` + `PartyDrawer.vue`; `AppClient.vue` anchor wiring; store reads party +
  combat panels by identity (no new protocol surface).
- `component-manifest.json`, `stories/` (two stories),
  `tests/overlays/deferred_surfaces_absent.test.js` (deferral entries removed); Vitest for
  island/drawer rendering + join logic; showcase coverage gate green.
