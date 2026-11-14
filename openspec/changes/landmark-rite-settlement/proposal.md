# Proposal

## Why

A landmark rite (design `docs/superpowers/specs/2026-11-14-landmark-rites-design.md`) is a deliberate act with a cost: it advances world time, moves the acting body's sexual state through one climax, and records that the player character completed that rite at that district. That settlement and its record need one deterministic owner in the rules layer before any command, action or panel can reach it.

This change adds the completion record and the settlement. Nothing calls them yet, so nothing a player sees changes. Districts still light from visited landmarks.

## What Changes

- New player-character record `landmark_rites` (schema 1) with one module as its sole writer and reader: strict envelope validation, counts per district and per option, unknown keys preserved on write, a corrupt record never overwritten.
- New rules API that resolves the rite landmark the record owner stands on, lists the bodies eligible to perform, checks a request without writing, and settles one rite atomically: one climax on the acting body, the option's shame and exposure steps, the option's full duration of world time, and the record write on the record owner.
- Stable refusal codes for every failure, each leaving no rite write.
- Three observability events: `landmark_rite_committed`, `landmark_rite_refused`, `landmark_rite_record_corrupt`.
- A public read of the canonical node of a location in the map-knowledge module, replacing use of its private helper by new code.

## Capabilities

### New Capabilities

- `landmark-rite-record`: the completion record, its envelope and its write rules.
- `landmark-rite-settlement`: where a rite is available, who may perform it, its refusals and its atomic settlement.

### Modified Capabilities

None. The three events are requirements of `landmark-rite-settlement`; the observability catalog document gains their rows.

## Impact

- New: `world/rules/landmark_rite_record.py`, `world/rules/landmark_rites.py`, `world/rules/tests/test_landmark_rite_record.py`, `world/rules/tests/test_landmark_rites.py`.
- Edits: `world/rules/map_knowledge.py` (public `node_id_for`), `docs/superpowers/specs/2026-09-02-observability-logging-design.md` (§4.2 catalog rows), `.github/evennia-shards.json`.
- No webclient, command, panel or lighting change.

## Batch:

- depends-on: landmark-rite-content-model
- conflicts: `landmark-rite-lighting` later reads `world/rules/landmark_rite_record.py` and edits `world/rules/map_knowledge.py`; it runs after this change.
- parallel with: `landmark-rite-content`.
