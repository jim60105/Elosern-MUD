# Proposal: companion-possession-webclient

## Why
Changes `companion-possession-rules` (state, gates, release ordering) and
`companion-possession-transition` (real puppet transfer, cmdset mount) make possession work on the
text surface; the Vue webclient currently has no way to enter, see, or leave it, and its panels
would render A's identity at B's location without an honest banner. Design doc D9 fixes the v1
presentation as an "honest hybrid": the camera moves to B, the banner says so, panels keep showing
what B genuinely has (inventory/equipment from B's real attributes) and what only A has
(wallet/quests/guild) under the banner rather than silently laundering A's purse through B's hands.
Source design: `docs/superpowers/specs/2026-09-05-companion-possession-design.md` (D9, D10, §4
Presentation, §5).

## What Changes

- `explore.possess` / `explore.possess_release` join the canonical affordance vocabulary: possess
  is emitted once per bound companion carrying the deterministic entry-gate verdict as its
  enabled/disabled state; release appears exactly once while possessing.
- Possession-mode refusals render honestly in the vocabulary: while the actor is a possessed NPC,
  talk entries, engage, and guild/shop navigation carry stable disabled codes with fixed zh-TW
  messages (D10's v1 refusals as disabled states, not hidden entries).
- PartyDrawer offers the possession affordances per companion row (and the release control while
  possessing) without changing the `party` panel payload schema.
- New webclient capability: the actor re-point through the established epoch-reset transition,
  the persistent banner 「你透過 B 的雙眼行動」on every snapshot while possessing, the panel hybrid
  (A's wallet/quests/guild/status under the banner; B's inventory/equipment from B's own
  attributes), and dispatcher-side refusals (shop, engage, talk-while-possessed) as fixed
  zero-write rejections.

## Capabilities

### New Capabilities

- `webclient-possession-presentation`: actor re-point, banner, hybrid panel contract, and the
  dispatcher-side possession-mode refusals.

### Modified Capabilities

- `exploration-affordances`: the allowlist gains the two possession codes, the vocabulary covers a
  possessed actor, and D10 refusals become stable disabled states.
- `webclient-party-panel`: PartyDrawer offers possession affordances; the panel payload schema is
  unchanged.
- `webclient-action-dispatch`: the production registry enumeration gains the two new adapters
  (exact-list requirement — the enumeration itself must change).

## Impact

- `web/webclient/presentation/affordances.py` (vocabulary),
  `web/webclient/actions/exploration_actions.py` (two new validators), PartyDrawer (Vue + UMD
  mirror), the presentation coordinator (banner field/panel), dispatcher guards.
- Depends on: `companion-possession-rules` + `companion-possession-transition` (the affordance
  emission reflects their gates; the transition owns the puppet/epoch side).
- JS gates apply: Vitest component suite + Storybook showcase coverage for the banner/PartyDrawer
  components; server-side panel validator + client mirror allowlists in lockstep.
- No player-command change (docs untouched); shard manifest updated for new Python test modules.

## Sizing

The largest slice (server affordances + validators + Vue PartyDrawer/banner + Vitest/Storybook
gates). If execution exceeds a day, land the server half first (affordance vocabulary,
exploration-action validators, coordinator banner field, Python tests) — the Vue/UMD half is
rendering-only over an already-correct server surface and lands second in the same branch before
merge; the JS gates (Vitest + Storybook showcase coverage) run with the Vue half. Do not split
the repo into a ninth change.
