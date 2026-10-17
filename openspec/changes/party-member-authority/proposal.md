# Proposal: Party member authority boundary

## Why

Every party-management mutation in the approved design (`docs/superpowers/specs/2026-10-18-party-member-management-ui-design.md` §3.1, §10) carries an explicit actor, recipient, giver, receiver or seller and must be re-derived on the server. Today only combat has such a boundary (`authorize_combat_actor`); exploration rules assume the puppet is the only actor. One shared rules-side boundary must exist before transfer, equipment, field actions, practice, shop and the party window can name a member.

## What Changes

- Add one read-only rules boundary that resolves the **commander** from the authenticated acting character (the character itself, or the owner of a possessed companion), and authorizes a named member for one purpose (`organize`: bag/equipment reorganization, which admits a knocked-out member; `act`: item use, casting, practice, which does not).
- Add the ordered **present party scope**: the commander, then the effective party members (canonical `live_companions` order) located in the commander's room; possession does not change it because the whole party follows a possessed traversal (`party-follow-under-possession`).
- Add one text member-token resolver for the `= <成員>` and `由 <成員>` command suffixes, matching only the commander and effective members by display name.
- Add stable rejection codes `not_party_member`, `member_not_present`, `member_cannot_act` with fixed Traditional Chinese messages. A forged, stale, or non-member identity is rejected and is never replaced by the commander.
- Add `party_in_combat(acting, *members)` (acting character, commander or any named member in an active session) and require a live puppet session before trusting a possession flag.
- No mutation, no new command, no protocol change in this slice.

## Capabilities

### New Capabilities

- `party-member-authority`: commander resolution, purpose-scoped member authorization, the present party scope, the text member token, and their stable rejection vocabulary.

### Modified Capabilities

None.

## Impact

- New module `world/rules/party_scope.py`; tests `world/rules/tests/test_party_scope.py` (registered in `.github/evennia-shards.json`).
- Reads only `world/rules/party.py` (`live_companions`, `bound_owner_of`), `world/rules/possession.py` (owner resolution) and stored HP through `world.rules.action.stored_gauge_pair`. No other code path changes.
- No dependency, schema, command, or document change.

## Effort

**5 hours total, strictly less than 8 hours**, including implementation, focused verification, documentation and integration.

## Batch: party member management

Declared implementation order: **1 of 33**. The full order, ownership map and conflict matrices are in the planning handoff for the 2026-10-18 design and are repeated per change in this section.

No direct prerequisites.

### Code and spec conflicts within the new batch

- Every later rule, protocol and action change imports `world/rules/party_scope.py` (dependency only, D); `party-follow-under-possession` uses `resolve_commander` for the follower set (D). No other change edits it except `party-rest-move-settlement` (adds nothing to its public surface; D).
- `.github/evennia-shards.json`: conditional manifest conflict with every change that adds a test module; preserve exactly-one-shard ownership in declared order.

### Active change coordination

No active OpenSpec change exists at proposal time (`openspec list --json` was empty; `fix-possessed-companion-room-location` is archived). Possession entry and exit rules are unchanged.
