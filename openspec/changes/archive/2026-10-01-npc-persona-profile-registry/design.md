## Context

See proposal.md for motivation. The authoritative product design is `docs/superpowers/specs/2026-10-01-npc-persona-authoring-design.md` (§5.1, §5.2, §10, §12). `npc-persona-card-foundation` provides the pure card contract in `world/lore/npc_card.py`. `world/lore/settlements/places.py` assembles place slices and validates an all-or-nothing host group; `world/lore/dialogue/__init__.py` assembles `guild`, `altoria`, `ciaran` dialogue slices, with all 16 capital tables in one `altoria.py`. `world/lore/` must never import `world/rules/`.

## Goals / Non-Goals

**Goals:** a profile vocabulary and slice layout that lets six content changes and the companion change run in parallel without touching shared files; a machine-checked source inventory; an optional, validated place reference.

**Non-Goals:** authoring any profile (content changes); making the place reference mandatory (`npc-persona-host-examiner-producers`); any persistence or runtime behavior.

## Decisions

### D1. Profile vocabulary and slice ownership

`world/lore/npc_profiles/shape.py`: `NpcVoiceLines(greeting: str | None = None, misunderstood: str | None = None)` (each ≤ 300 code points, single paragraph plain text, normalized like card leaves) and `NpcProfile(key, card: NpcCard, voice: NpcVoiceLines)`. Profile keys are lowercase ASCII snake identifiers ≤ 64 characters. Convention (enforced by later slice tests, not by the vocabulary): a host profile key equals its place `service_id`; examiners use `guild_examiner_<rank lowercase>`; companions use `companion_<partner preset key>`.

`world/lore/npc_profiles/__init__.py` assembles `NPC_PROFILE_REGISTRY` (a `MappingProxyType`) from the slices in fixed order: `altoria_lower`, `altoria_trade`, `altoria_guild`, `altoria_upper`, `ciaran_homes_a`, `ciaran_homes_b`, `companions`. Each slice exports `ROWS: tuple[NpcProfile, ...] = ()` and is owned by exactly one later change. Assembly rejects a duplicate key naming both slices and rejects any profile whose card fails the contract, naming the profile key and slice. The registry is not mirrored into lore Scripts (like dialogue rows): it holds hidden identities and is consumed only through code.

`inventory.py` declares `NPC_SOURCE_INVENTORY`: frozen `NpcSource(kind, key, owner)` rows. Kinds: `place_host` (keyed by `service_id`), `dialogue_table` (keyed by `dialogue_key`), `guild_examiner` (rank key), `starting_companion` (`<declaring preset>:<partner preset>`), `quest_template_occupant` (`<template name>:<stage>:<position>`), `import_example` (example file stem). `owner` is the owning change's slice label. The data-contract test derives the actual sources from `PLACE_REGISTRY`, `DIALOGUE_ROWS`, `GUILD_RANK_REGISTRY`, `PLAYER_PRESET_REGISTRY`, `QUEST_TEMPLATE_POOL`, and `world/imports/examples/*.json`, and asserts set equality with the inventory, so a source added later without an owner fails. Expected size at this baseline: 25 hosts, 25 tables, 7 examiners, 4 companion declarations, 1 template occupant, 1 import example.

Owner assignment (binding for the content changes):
- `altoria_lower`: services `altoria_eatery_owner`, `altoria_tavern_keeper`, `altoria_innkeeper`, `altoria_bathhouse_keeper`, `altoria_guard_captain` and their five tables.
- `altoria_trade`: `altoria_merchant`, `altoria_blacksmith`, `altoria_tailor`, `altoria_jeweller`, `altoria_alchemist`, `altoria_merchant_master` and their six tables.
- `altoria_guild`: `altoria_guild_master`, the `guild_staff` table, and the seven guild examiners.
- `altoria_upper`: `altoria_high_priestess`, `altoria_sanctum_deacon`, `altoria_noble_watch_captain`, `altoria_drill_instructor`, `altoria_academy_dean` and their five tables.
- `ciaran_homes_a`: `ciaran_elenis`, `ciaran_gwenaera`, `ciaran_hailiel`, `ciaran_lareneth` and their tables.
- `ciaran_homes_b`: `ciaran_nireth`, `ciaran_teliel`, `ciaran_valwyn`, `ciaran_vethiel` and their tables.
- `companions`: the four starting-companion declarations.
- `generated_quest_cards`: the template occupant; `import_cards`: the import example.

### D2. Optional place reference now, mandatory later

`PlaceDefinition.host_profile_key: str | None = None` is appended after the existing defaulted fields. `validate_place_registry` rejects a set key on a hostless place and a key absent from `NPC_PROFILE_REGISTRY`, naming the place. It is not yet in `HOST_IDENTITY_FIELDS`; `npc-persona-host-examiner-producers` adds the mandatory rule once every slice has filled its rows; the requirement this change adds states only the conditional rules (resolve when named; never on a hostless place), so both requirements stay true together after archive. `place_is_hostless` treats a set `host_profile_key` as host material so a stray key is never silently ignored.

### D3. Altoria dialogue split is a pure move

Rows move verbatim into `altoria_lower.py`, `altoria_middle.py`, `altoria_upper.py` according to the terrace of the place that authors each `dialogue_key`; `world/lore/dialogue/__init__.py` assembles `GUILD_STAFF_ROWS, ALTORIA_LOWER_ROWS, ALTORIA_MIDDLE_ROWS, ALTORIA_UPPER_ROWS, CIARAN_ROWS`. A test asserts the assembled key order and every definition are identical to the pre-split table (captured from `git show HEAD:world/lore/dialogue/altoria.py` during apply, then asserted structurally: each key's terrace matches its place row). `altoria.py` is deleted, with every import site updated (no re-export shim).

## Risks / Trade-offs

- [Empty slices could be mistaken for completed content] → the inventory test names owners; the boot gate in `npc-persona-roster-validation` requires every inventory source to resolve to a complete profile, so empty slices cannot pass activation.
- [The dialogue split touches imports in tests] → enumerate with `rg "world.lore.dialogue.altoria"` and update every site in this change.

## Migration Plan

None; registry-only data.
