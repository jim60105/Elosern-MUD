# Proposal: Raise the Combat-Panel Skill-Count Bound (MAX_SKILLS)

## Why

The combat panel hard-caps the flattened skill-descriptor count at `MAX_SKILLS = 32`
(`world/rules/combat_view.py`), mirrored by the web panel validator and `protocol.js`. The sexual
act catalog added 63 active skills on top of the 91 base active skills — a theoretical maximum of
154 owned active skills — so any character who unlocks a meaningful share of the act catalog
alongside normal spell acquisition crosses the bound and the entire combat action panel becomes
unavailable (`CombatViewError` → `PanelUnavailableError`). The bound predates the catalog (A2
preserved it deliberately); this change reconciles the presentation bound with the now-much-larger
skill universe.

## What Changes

- **BREAKING (protocol bound)**: `MAX_SKILLS` rises from `32` to `192` — above the current
  theoretical maximum of 154 active skills with headroom for catalog growth, and a multiple of 16
  consistent with the presentation-bounds family (`MAX_PARTICIPANTS = 16`, `MAX_SKILLS = 32` were
  the existing members).
- Update the four enforcement points to the new value: `world/rules/combat_view.py` (build-time
  bound), `web/webclient/presentation/combat_panel.py` (validation bound — imports the constant),
  `web/static/webclient/js/elosern/protocol.js` (client-side mirror), and both boundary tests
  (Python panel test and the JS protocol test, which hardcode 32/33).
- The flattened-total semantic stays exactly as shipped (A2 design D-5): the bound applies to the
  flattened descriptor count across all categories, not to the top-level category-group count.
- The v3 payload grows proportionally; `MAX_DEPTH = 12` already accommodates the nesting.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `webclient-combat-menu`: the flattened skill-count bound requirement's value rises from 32 to
  192; the boundary scenarios are updated.

## Impact

- `world/rules/combat_view.py` — `MAX_SKILLS` constant.
- `web/webclient/presentation/combat_panel.py` — imports the constant; no logic change.
- `web/static/webclient/js/elosern/protocol.js` — `MAX_SKILLS` constant (mirror).
- Tests: `world/rules/tests/test_combat_view.py`, `web/webclient/presentation/tests/test_combat_panel.py`,
  `web/static/webclient/js/tests/protocol.test.js`.
- Spec delta: `webclient-combat-menu`.
