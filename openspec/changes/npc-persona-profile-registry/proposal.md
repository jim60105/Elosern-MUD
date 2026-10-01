## Why

The approved design (`docs/superpowers/specs/2026-10-01-npc-persona-authoring-design.md` §5.1–5.2, §12) needs immutable, keyed NPC profiles owned by one assembly module, a reviewable source inventory with no unassigned shipped entry, and a place-level profile reference — before six content slices can author in parallel. Today service hosts have no profile source at all, and all 16 capital dialogue tables live in one file that four parallel slices would collide on. Split out of the foundation so each stays one workday.

## What Changes

- Add `world/lore/npc_profiles/`: `NpcProfile` (stable key, compact card, bounded voice lines `greeting`/`misunderstood`), validated through the card contract at import; one assembly module owning the fixed slice order; pre-created empty slice modules (`altoria_lower`, `altoria_trade`, `altoria_guild`, `altoria_upper`, `ciaran_homes_a`, `ciaran_homes_b`, `companions`), one per owning change, so no content change edits the assembly; no placeholder profile is created.
- Add the source inventory (`inventory.py`) enumerating every shipped NPC source with its owner, and a data-contract test comparing it with the live registries.
- Add an optional `PlaceDefinition.host_profile_key`, validated when named (must resolve; never on a hostless place). Making it mandatory belongs to `npc-persona-host-examiner-producers`.
- Split `world/lore/dialogue/altoria.py` into terrace slices with no prose change and an unchanged assembled key order.

## Capabilities

### New Capabilities

- `npc-profile-registry`: immutable authored NPC profiles, their assembly and validation, and the shipped NPC source inventory.

### Modified Capabilities

- `settlement-place-registry`: ADDED validation of a host-profile reference on place records.

## Impact

- New: `world/lore/npc_profiles/` (`__init__.py`, `shape.py`, `inventory.py`, seven empty slices), `world/lore/dialogue/altoria_{lower,middle,upper}.py` (moved rows).
- Modified: `world/lore/settlements/places.py`, `world/lore/dialogue/__init__.py`, every import site of `world.lore.dialogue.altoria`.
- Tests: `world/lore/tests/` (package-owned shard), `tools/test_data_freeze.json` (inventory data-contract test).

## Batch:

depends-on: npc-persona-card-foundation

Code-conflict notes: single integration owner of `world/lore/npc_profiles/__init__.py` (profile assembly) and `world/lore/dialogue/__init__.py` (dialogue assembly); no later change edits either. `world/lore/settlements/places.py` is edited here and again by `npc-persona-host-examiner-producers` (sequential). Can run in parallel with every change that depends only on `npc-persona-card-foundation`. Prerequisite of all content slices, `npc-persona-companion-profiles`, `npc-persona-offline-bundles`, and `npc-persona-dialogue-consumption`.
