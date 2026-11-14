# Proposal

## Why

Landmark rites (design `docs/superpowers/specs/2026-11-14-landmark-rites-design.md`) replace the instant district reveal with an authored, repeatable ritual scene. Every later change reads one authored document: the ritual archetypes, their options and scenes, and the assignment of every district to one archetype. That document needs a typed model and a strict loader before any content or rule can exist.

This change ships only the model and the loader. It ships no content, publishes nothing at startup and changes nothing a player sees.

## What Changes

- New package `world/lore/rites/` with immutable shape dataclasses, a strict loader for one rite document, and the process-wide snapshot holder that later changes read.
- The loader validates the document against a supplied set of district keys and rejects every fault with a diagnostic that names the field path and a stable code.
- A rite scene reuses the existing `Scene`, `Speech` and `Narration` model. It may open with narration and must contain at least one narration line.

## Capabilities

### New Capabilities

- `landmark-rite-content`: the authored rite document, its bounds, its district assignment and its validated snapshot.

### Modified Capabilities

None.

## Impact

- New: `world/lore/rites/__init__.py`, `world/lore/rites/shape.py`, `world/lore/rites/loader.py`, `world/lore/tests/test_rite_content.py`.
- Edits: `.github/evennia-shards.json` (register the test module).
- No shipped content, no startup step, no wire change.

## Batch:

- depends-on: none
- conflicts: none. `landmark-rite-content` and `landmark-rite-art` later edit `world/lore/rites/`; they run after this change.
