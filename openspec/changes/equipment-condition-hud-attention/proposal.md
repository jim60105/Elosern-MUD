## Why

Equipment-origin adverse conditions currently count as unconditional vitals-HUD attention because the client checks severity alone. Wearing an item can therefore keep the contextual dock visible at full resources outside combat, even though its persistent trade-off still belongs in truthful status information.

## What Changes

- Add deterministic, read-only condition provenance distinguishing equipment-dependent, independently non-equipment, mixed, and unattributable sources. Preserve global severity, condition membership, durations, and actual combat adjustments.
- Exclude proven equipment-dependent conditions from the dock's condition-attention trigger. Independent adverse conditions, combat, depleted resources, and the existing low-HP presentation state retain their triggers, subject to existing availability and mode gates.
- Attribute worn attached buffs to their verified item sources and distinguish them from independent instances of the same definition. Derive state-modifier provenance from the actual equipment overlay and the same rule evaluator over an equipment-free in-memory comparison.
- **BREAKING**: advance the status panel from its implemented schema version 2 to 3, requiring provenance on each condition. Cut over the presenter, mirrored validators, fixtures, stories, and consumers together; add no compatibility form or migration.
- Keep every condition available in the complete status roster and, when another trigger reveals the dock, its condition row. Expose equipment source labels in existing condition detail surfaces.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-status-presentation`: exact version-3 condition provenance and pure equipment-aware source attribution, including mixed and unknown sources.
- `webclient-contextual-hud`: provenance-aware condition attention and truthful source disclosure, preserving the existing mode, availability, focus, and trailing-bar rules.

## Impact

One bounded engineer-day change across `world/rules/status_query/`, existing pure equipment-effect accessors, `web/webclient/presentation/status.py` and status schema ownership, mirrored browser protocol validation, vitals derivation, and shared condition-detail rendering. The equipment settlement API, combat balance tables, stored sexual state, global display severities, and content registries keep their gameplay semantics. Synthetic backend, protocol, component, and committed-update tests cover the cutover. No new dependency or persistent data is required.

## Scope Boundary

The prior read-only investigation found Yuna's stored exposure already at 極高, full HP/MP/SP, no combat, and the warning `high_exposure_defense_penalty`. Her worn `dark_elf_kimono` adds +1 exposure bias, which clamps to the same 極高. Her preset also stores 極高. The warning therefore remains independently applicable without equipment; this change does **not** promise to hide her current dock. Suppressing permanent innate/baseline adverse states, changing that preset, or special-casing Yuna is out of scope. Tests reproduce this boundary with synthetic actors and equipment, without depending on shipped content or a live database.

Historical equipment-caused state mutations are also outside this read-time provenance contract. Once a consequence is persisted as canonical state, this change does not erase it or reconstruct its history.

## Dependency and Conflict Matrix

`openspec list --json` returned no active changes before creation. This change has no proposed-change dependency. Its implementation ownership includes status-query models/context/assembly, status presenter and schema registration/validation, browser status protocol constants/validator, vitals derivation, condition details and their fixtures/tests. A subsequently proposed change editing those surfaces must reconcile that overlap before parallel application. Existing equipment-effects and OOB replacement/ordering contracts are prerequisites already present on the primary branch.
