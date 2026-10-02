## Why

The user-approved §13c amendment chooses KISS: the offline bundle selector has no production callers, and its planned cutover consumer was cancelled by §13b. Keeping 22 unconsumed cards and their standalone machinery is dead weight; Git history is sufficient recovery if a real future use case appears.

## What Changes

- **BREAKING** Remove the unused bundle module, whole-card pools, pool/selector APIs and exports, subsystem-only validation/tests and owned data-manifest entries; retain no aliases, stubs, backup copy or compatibility decoder.
- **BREAKING** Remove `offline_bundle` from the NPC provenance closed set/validator and retire all three current offline-bundle capability requirements.
- Preserve generic tier/race registries, authored host/examiner profiles, companion single-source presets, generated quest cards, complete offline quest-template occupant cards, NPC imports/editor and current greeting behavior.
- No extra LLM prompt material, inputs/outputs or calls; no post-generation card replacement or offline LLM character generation. No integration of the removed selector into any producer.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `npc-persona-offline-bundles`: retire all owned pool/resolution/selection requirements.
- `npc-persona-card`: retire bundle-only provenance while preserving the four live provenance kinds.

## Impact

One engineer-day: delete `world/lore/npc_profiles/bundles.py` and `world/lore/tests/test_npc_persona_bundles.py`; narrow `world/lore/npc_card.py` and its provenance tests; remove owned entries from both `tools/test_data_freeze.json` and `tools/test_data_lint_seed.json`. The broad `world.lore` shard label stays. No current bundle import/gate exists in profile assembly or roster validation; do not delete unrelated quest-template coverage. Current adding-NPC/roster docs need no invented bundle cleanup; document the retirement where warranted and leave archived changes historical. Superpowers §13c was committed separately by the parent (030fa18c); this change does not edit it.

## Batch:

depends-on: npc-authored-canonical-ages
depends-on: npc-persona-unicode-normalization

Code-conflict notes: retirement runs after the four-fix integration chain. `npc_card.py`, its focused tests and `npc-persona-card` deltas are shared with Unicode normalization (different normalization/provenance requirements). Data manifests and broad lore test ownership may overlap age/roster work; remove only exact bundle-owned entries. No semantic dependency on the fixes; ordering avoids shared-file conflicts and satisfies the requested sequential fifth change.
