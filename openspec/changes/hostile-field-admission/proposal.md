# Proposal

## Why

Current combat admission requires player initiation and forced-sleep opening becomes zero-round defeat. Explicit aggression must admit normal encounters immediately and resolve real enemy turns when allies cannot act.

## What Changes

Admit immediate whole-cell hostile contacts with no free opening attack, consuming the preceding real enemy-only continuation and forced-sleep threshold contract.

This is a bounded one-engineer-day slice. **BREAKING** where a current behavior is replaced, with every caller and substantive test migrated in that slice. No feature code is authorized by this proposal.

## Sizing

The slice has three mechanisms, namely the rules-only contact evaluator and writer (task1.1), the owner-mediated sleep interruption with retained exam-only FAIL (task2.1) and the atomic arrival-to-combat publication (task3.1). Contact authority without its writer hooks admits nothing observable, and the interruption contract is reachable only through a real admitted contact, so the three cannot become separately playable slices. Each task check names its observable end state instead of asserting a duration.

## Capabilities

### New Capabilities

- `hostile-field-contact`.

### Modified Capabilities

None.

## Impact

Consumes landed mechanisms. field_enemy_roster already collects all living local monsters in persistent-ID order, independently of effect recipients. engage_group is the staged roster API; hostile admission gets distinct rules authority without weakening voluntary sleep gates. Population lifecycle and recorded protection intervals provide chronological birth/arrival facts.

Attaches at combat_initiation.py, combat_session/{lifecycle,battlefield,rounds,settlement,records}.py, fatigue.py, sleep_control.py, movement_settlement.py and population_lifecycle.py.

Baseline is current code and synced main specs, including the archived 2026-11-04 regional-population owner/recovery/runtime, manual compositions, actual-live views, combat identity and whole-cell admission changes. Historical design descriptions of coordinate slots and provisioning are superseded. `world/maps/monster_provisioning.py` and `world/clock/` do not exist; the active clock is `world/rules/clock.py`. Do not recreate removed paths.

Human judgments of ecology selection, player wording and presentation clarity are reviewed in `docs/development/monster-field-behaviour.md` during implementation. Tests establish state, identity, legality and timing rather than shipped copy or balance tables.

## Non-goals

No patrol guards, full ecology, cross-cell pursuit, disease, corrosion, wildfire, rewards or new species/boss content. Lore and skills remain read-only registries; maps owns population/location; rules owns travel pricing, physiology, combat and coordination; AI never writes state. No aliases, legacy slot readers, hidden resets, save conversion or online migration. Existing incompatible development state requires an explicit operator procedure.

## Batch:

depends-on: incapacitated-hostile-rounds

Code conflicts begin with interruptible-field-contact, which consumes this admission and automatic-round accounting, and include paid-party-retreat, which later changes session terminal billing; serialize all session/clock edits. All changes share the developer review/evidence document; serialize that file, `.github/evennia-shards.json` and `.github/browser-shards.json`. Command behavior changes update `docs/game/commands.md` and `docs/game/command-reference.md` together.
