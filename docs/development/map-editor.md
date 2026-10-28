# Standalone Map Editor: Reference Context and Deletion Boundaries

## 1. External Reference Context

The standalone map editor is an independent authoring tool that runs outside the Evennia/Django runtime and does not import game modules. To validate external dependencies (such as scene archetypes, quest definitions, service hosts, titles, and lore elements) and safely prevent deletion of referenced map objects, the game exports an authoritative static reference index:

- File: `content/map-reference-context.json`
- Generator: `tools/map_reference_context.py`
- Core Codec & Freshness Checker: `elosern_map_core.reference_context`

The reference context records:
- Supported `schema_version` (1) and `exporter_version` (1).
- External identifier sets (`scene_archetypes`, `quest_definitions`, `nations`, `wilderness_regions`, `titles`, `service_hosts`, `races`, `subraces`, `elements`, `magic_tiers`, `monster_tiers`, `monster_species`, `settlements`, `shops`, `assortments`).
- Incoming external static references to qualified map objects (such as `places` in `world/lore/settlements/` joining interior rooms, or `service_hosts` spawning in interior rooms).
- Workspace-relative source paths for diagnostic location reporting.
- A manifest of source file paths and SHA-256 digests covering the complete transitive external static source closure.
- Allowlisted discovery rules and an aggregate dependency fingerprint.

## 2. Exporter and Freshness Commands

### Regenerate committed index
When an external static declaration changes (e.g., adding an NPC place, altering a service host, or modifying a static registry):

```bash
uv run --locked python -m tools.map_reference_context
```

Commit `content/map-reference-context.json` together with the source changes that caused the regeneration.

### Verify freshness in CI
CI runs the check during preflight and as part of `tools.contract_gate`:

```bash
uv run --locked python -m tools.map_reference_context --check
```

If the committed file differs byte-for-byte or any source closure dependency has changed, the command exits with code 1 without rewriting the file.

## 3. Deletion Safety and Limitations

### Deletion Safety Requirements
An object-removing operation in the editor (including destructive delete commands and object-removing undo operations) requires all of the following:

1. **Current External Context**: The reference context must report `status="current"`. If the context is unavailable (due to changed sources, missing files, membership mismatch, or unsupported versions), deletion is refused immediately. Unknown or unavailable context can never prove absence of references.
2. **Zero External Incoming References**: No external static declaration (such as an authored place joining an interior room) may reference the target.
3. **Zero Map-Internal Incoming References**: No authoring document (e.g. another room's door or exit) may reference the target within the `AuthoringWorld`.

When external context is unavailable or an incoming reference exists:
- Destructive commands and object-removing undo operations refuse execution.
- No disk files or command history states are altered.
- Ordinary non-destructive editing (moving nodes, adjusting attributes, inspecting diagnostics) remains available.

### Live Database Safety
The editor operates on static authoring documents and does not connect to or query the live game database (`ObjectDB`). It cannot certify live save dependents (e.g., players currently occupying a room or dynamic exits). Live occupied room safety and persistent room preservation remain strictly game-side responsibilities enforced during runtime synchronization (`sync_map_world`).

### Geometry Exclusion
The reference index records stable authored identities (e.g. `settlement_node:capital_altoria:central_plaza`), not derived spatial coordinates or grid wire strings (`grid:capital_altoria:100:200`). Moving a node coordinate alone does not alter the external reference index or its dependency fingerprint.
