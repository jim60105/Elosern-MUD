# Proposal: Party panel v3 and viewed-member selection

## Why

Design §3.1–§3.3 and §5 of `docs/superpowers/specs/2026-10-18-party-member-management-ui-design.md`: the party window shows summaries for every member (commander first, with MP, SP, knocked-out and unread flags) and full detail for one viewed member, chosen by `party.view_member` and stored on the session. Today `party` v2 lists companions only, carries HP only, and there is no server-side viewed-member selection.

## What Changes

- **BREAKING (pre-release)** `party` v2 → v3: commander row 0; each row adds `mp_current`, `mp_maximum`, `sp_current`, `sp_maximum`, `role`, `knocked_out`, `unread`; `bond_stage`/`membership` are null on the commander row; the panel adds `viewed_member_id`. The presenter always builds from the commander (possession-identical). Python validator, JS mirror, parity contract and fixtures move together.
- New action `party.view_member {member_id, tab}`: membership-only authorization (presence not required), per-session selection keyed to the commander (survives possession, dropped on disconnect), `tab: skills` clears that member's unread mark (`party-unlock-notices`). It republishes the panels built for the viewed member (this change: `party`; later protocol changes add theirs).
- Fallback: a selection naming a member who left or was deleted resolves to the commander in every presenter.
- Existing consumers (`PartyDrawer.vue`, `CompanionLineup`, `party-helpers.js`, the combat HUD join) skip the commander row; no visual change yet.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-party-panel`: version-3 panel (renamed requirement), viewed-member selection, unread clearing.
- `webclient-action-dispatch`: registry allowlist adds `party.view_member`.

## Impact

- `web/webclient/presentation/party.py`, new `web/webclient/presentation/party_view_selection.py`, `web/webclient/presentation/context.py` (copied selection), `web/webclient/presentation/coordinator.py`, `web/webclient/actions/party_actions.py`, `web/webclient/actions/registry.py`, JS mirror `web/static/webclient/js/elosern/protocol/panels/`, Vue consumers listed above, fixtures.
- Tests: presenter/validator/parity tests, `web/webclient/actions/tests/test_party_actions.py`, Node/Vitest consumer tests.

## Effort

**7 hours total, strictly less than 8 hours**, including implementation, focused verification, documentation and integration.

## Batch: party member management

Declared implementation order: **13 of 31**.

- depends-on: party-unlock-notices
- depends-on: party-item-transfer

### Code and spec conflicts within the new batch

- `party-item-transfer`: shared spec requirement `webclient-action-dispatch` allowlist (S; this delta keeps `party.transfer`), shared files `party_actions.py`, `registry.py` (F; that first).
- `party-member-panel`, `character-panel-v8-viewed-member`, `party-inventory-panel`, `item-holdings-panel`, `lineage-panel-v2-graphs`, `services-shop-structured-rows`: read the copied selection (D) and extend the `party.view_member` affected-panel tuple in `party_actions.py` (F, one line each, ordered); `item-holdings-panel` also extends the payload and re-modifies the `webclient-party-panel` ADDED selection requirement (S).
- `webclient-party-window-member-tab`: removes `PartyDrawer.vue` edited here (F; ordered).
- Protocol fixtures and parity contract files are shared with every protocol change (F, conditional; ordered).

### Active change coordination

No active OpenSpec change. Possession banner (`possession_banner` v1) and HUD `status` are unchanged.
