# Proposal

## Why

Confirmed retreat currently marks the party fled in place. A valid escape must afford a real adjacent edge using post-attempt reserve and commit the actual traversal with its old-session exit.

## What Changes

Execute confirmed whole-party retreat over a legal affordable edge, charging one attempt round plus normal travel once, with immediate arrival re-engagement.

This is a bounded one-engineer-day slice. **BREAKING** where a current behavior is replaced, with every caller and substantive test migrated in that slice. No feature code is authorized by this proposal.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `player-combat-session`.

## Impact

Consumes landed mechanisms. Persistent combat IDs and whole-cell admission are already landed. The map population owner keeps actual arrivals and escaped enemies, and the existing clock source settles journeys during travel. Prior batch changes provide edge history, canonical route quotes, contact admission and indivisible traversal visibility.

Attaches at combat_session/exit.py confirmation receipts, rounds.py::resolve_party_retreat/_escaped_party_retreat/_failed_party_retreat, settlement.py, movement_settlement.py and travel_cost.py.

Baseline is current code and synced main specs, including the archived 2026-11-04 regional-population owner/recovery/runtime, manual compositions, actual-live views, combat identity and whole-cell admission changes. Historical design descriptions of coordinate slots and provisioning are superseded. `world/maps/monster_provisioning.py` and `world/clock/` do not exist; the active clock is `world/rules/clock.py`. Do not recreate removed paths.

Human judgments of ecology selection, player wording and presentation clarity are reviewed in `docs/development/monster-field-behaviour.md` during implementation. Tests establish state, identity, legality and timing rather than shipped copy or balance tables.

## Non-goals

No patrol guards, full ecology, cross-cell pursuit, disease, corrosion, wildfire, rewards or new species/boss content. Lore and skills remain read-only registries; maps owns population/location; rules owns travel pricing, physiology, combat and coordination; AI never writes state. No aliases, legacy slot readers, hidden resets, save conversion or online migration. Existing incompatible development state requires an explicit operator procedure.

## Batch:

depends-on: interruptible-field-contact

Code conflicts require every predecessor session and movement contract. Exit, round and settlement billing are owned exclusively while this change lands; shard manifests and both command docs serialize. All changes share the developer review/evidence document; serialize that file, `.github/evennia-shards.json` and `.github/browser-shards.json`. Command behavior changes update `docs/game/commands.md` and `docs/game/command-reference.md` together.
