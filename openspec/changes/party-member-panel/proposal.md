# Proposal: party_member panel

## Why

Design §5 and §6.1 of `docs/superpowers/specs/2026-10-18-party-member-management-ui-design.md`: the 成員 tab needs the viewed member's bond stage with pips, membership (general and temporary commissions), intimate state, persona prose (commander only) and action descriptors for possess or release, leave and the NPC persona editor. Today these facts are split between `party` v2 rows, `character` v7 (persona, intimate, puppet-only) and client-side affordance lookups in `PartyDrawer.vue`.

## What Changes

- New presenter and exact validator `web/webclient/presentation/party_member.py` (`party_member` v1) built for the viewed member (fallback commander), available in exploration and combat; JS mirror, parity contract, store allowlist and fixtures.
- Read helpers in rules for bond stage index/count (`world/rules/affinity.py` stage table) and the existing possession/leave/persona-editor verdicts reused for descriptors.
- `party.view_member` affected panels add `party_member`.
- No removal yet: `character` still carries persona/intimate until `character-panel-v8-viewed-member`.

## Capabilities

### New Capabilities

- `webclient-party-member-panel`: the `party_member` panel contract.

### Modified Capabilities

None.

## Impact

- New `web/webclient/presentation/party_member.py`; `web/webclient/presentation/registry.py`; `web/webclient/actions/party_actions.py` (affected tuple); JS mirror under `web/static/webclient/js/elosern/protocol/panels/`; `web/webclient-app/stores/elosern/constants.js` allowlist; fixtures.
- Tests: `web/webclient/presentation/tests/test_party_member_panel.py` (sharded), parity contract, Node mirror test.

## Effort

**6.5 hours total, strictly less than 8 hours**, including implementation, focused verification, documentation and integration.

## Batch: party member management

Declared implementation order: **14 of 31**.

- depends-on: party-panel-v3-view-member

### Code and spec conflicts within the new batch

- `party-panel-v3-view-member`: shared file `party_actions.py` affected tuple (F; that first).
- `character-panel-v8-viewed-member`: moves persona/intimate out of `character`; shares the persona/intimate serializer helpers in `character.py` (F; this change first, it extracts them).
- Protocol registry, allowlists, parity contract and fixtures: shared with every protocol change (F, conditional; ordered).
- `webclient-party-window-member-tab`: consumes this panel (D).

### Active change coordination

No active OpenSpec change. Possession verdicts and NPC persona editor actions are consumed unchanged.
