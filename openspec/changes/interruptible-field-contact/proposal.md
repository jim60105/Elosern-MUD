# Proposal

## Why

next_registered_boundary currently reports population maintenance boundaries, and cannot forecast a later contact created by an intermediate journey or birth. Long waits need the first actual interactive tick with exact sleep recovery.

## What Changes

Forecast deterministic future contacts read-only and stop wait/rest/sleep at the first contact, preserving accepted receipts and discarding unused requested time.

This is a bounded one-engineer-day slice. **BREAKING** where a current behavior is replaced, with every caller and substantive test migrated in that slice. No feature code is authorized by this proposal.

## Sizing

The new surface is the pure chronological projection in task1.1, which reuses the committed planners instead of adding a second scheduler. Tasks2.1 and 3.1 are consumer integration across the wait, sleep, owner-continuation, study, camping and travel owners that already exist. A forecast with no consumer is unverifiable, and a consumer without the forecast cannot stop at a contact that intermediate facts create, so both halves stay in this change. The equal-time partition check in design.md Verification is the completion boundary for the projection, and each consumer task carries its own accepted-interval assertion.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `hostile-field-contact`.
- `time-skip-commands`.
- `wilderness-travel-interrupts`.

## Impact

Consumes landed mechanisms. register_event_source already accepts next_boundary; mental_time.next_skip_boundary composes it with fatigue and sleep receipts. Extend the merged population source rather than add another scheduler. Persistent IDs, real population ownership and whole-cell admission are reused through the two preceding changes.

Attaches at population_lifecycle.py::next_population_lifecycle_boundary, mental_time.py::next_skip_boundary, time_skip.py and sleep receipt/control owners, text/browser time consumers.

Baseline is current code and synced main specs, including the archived 2026-11-04 regional-population owner/recovery/runtime, manual compositions, actual-live views, combat identity and whole-cell admission changes. Historical design descriptions of coordinate slots and provisioning are superseded. `world/maps/monster_provisioning.py` and `world/clock/` do not exist; the active clock is `world/rules/clock.py`. Do not recreate removed paths.

Human judgments of ecology selection, player wording and presentation clarity are reviewed in `docs/development/monster-field-behaviour.md` during implementation. Tests establish state, identity, legality and timing rather than shipped copy or balance tables.

## Non-goals

No patrol guards, full ecology, cross-cell pursuit, disease, corrosion, wildfire, rewards or new species/boss content. Lore and skills remain read-only registries; maps owns population/location; rules owns travel pricing, physiology, combat and coordination; AI never writes state. No aliases, legacy slot readers, hidden resets, save conversion or online migration. Existing incompatible development state requires an explicit operator procedure.

## Batch:

depends-on: hostile-field-admission

Code conflicts begin with hostile-field-admission, which supplies the writer and sleep transitions first, and include paid-party-retreat, which requires indivisible arrival contact behavior from this change. Shared time/command documents serialize. All changes share the developer review/evidence document; serialize that file, `.github/evennia-shards.json` and `.github/browser-shards.json`. Command behavior changes update `docs/game/commands.md` and `docs/game/command-reference.md` together.
