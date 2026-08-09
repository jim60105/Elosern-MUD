# persona-store

## Why

`persona` is the only `LivingEntity` data seam without a working handler: validated imports
persist the record verbatim on `entity.db.persona`, but nothing in the game reads it. The master
design (§5.2) contracts a `PersonaStore` handler that retrieves by key and flattens into prompt
blocks, and the persona-dialogue design (`docs/superpowers/specs/2026-08-09-persona-dialogue-design.md`)
needs it as its foundation. Claiming the seam now completes the §5.2 contract with no behavior
change for existing characters.

## What Changes

- Adds a read-only `PersonaStore` handler in `world/rules/persona.py` with keyed retrieval and
  bounded prompt-block flattening over the `personality`, `life_story`, and `habit` fields.
- Mounts the handler on `LivingEntity.persona`, replacing the placeholder
  `AttributeProperty(default=None)`; raw storage stays at `entity.db.persona`.
- Keeps `world/imports/loader.py` unchanged (verbatim storage is the only writer).
- Carries no write API, preserving the single-writer boundary.
- Flips the `living-entity-hierarchy` persona-seam requirement and its no-PersonaStore scenario.

## Capabilities

### New Capabilities
- `persona-store`: The read-only `PersonaStore` handler — keyed retrieval and bounded
  prompt-block flattening of an entity's verbatim persona record, mounted on `LivingEntity.persona`.

### Modified Capabilities
- `living-entity-hierarchy`: `persona` is no longer a forward-declared placeholder; it becomes the
  working `PersonaStore` mount, and the "no PersonaStore class definition" scenario is replaced by
  the working-handler contract.

## Impact

- `typeclasses/entities.py`: `persona` placeholder attribute flips to the `PersonaStore` mount
  (same pattern as the `relations` mount).
- `world/rules/persona.py`: new read-only module (flatten + bounds + tests).
- `world/imports/loader.py`: untouched.
- No behavior change for created characters: `persona` stays absent until a future change (e.g.
  persona-dialogue injection or generative character creation) supplies content.
