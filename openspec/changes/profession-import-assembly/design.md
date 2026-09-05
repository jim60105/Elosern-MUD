# Design: profession-import-assembly

Ratified decisions: R3 design §4 and D4/D5. Local implementation choices only here.

## Context

`world/imports/loader.py::_instantiate_validated_character` constructs the entity and writes
seam attributes inside one transaction (`load_batch` wraps batch work transactionally); the
import path never touches components today. `typeclasses/components.py` components are attached
via the entity's `components` handler (`host.components.get(slot)` is how readers find them;
`GuildStaff`/`GuildExaminer`/`ScriptedDialogue` take `service_id`/`branch_key`/`dialogue_key`
kwargs, `Merchant` takes `shop_key`). `set_npc_schedule(npc, schedule)`
(`world/rules/npc_schedules.py:457`) stores the template-reference form
`{"schema_version": 1, "template": <key>}` validated by its own model. Trait construction today:
`_resolve_trait_values` = race floor + literal record stats, applied via `_trait_config`.

## Goals / Non-Goals

**Goals:** profession-driven assembly that never invents authored identity values; D5
precedence; absent-`profession` byte-identity (the strongest regression pin).

**Non-Goals:** runtime profession reads, sync changes, binding consumption, PlayerCharacter
professions.

## Decisions

- **Assembly helper in the loader module** (`_apply_profession(record, entity)`), not a new
  module: it is import-path logic, and `declarative-service-hosts` imports the same helper.
  Attaching components = construct the component class with the merged kwargs through the same
  attach path the guild sync uses (`_sync_service_host`'s loop) so assembly is one mechanism.
- **Identity kwargs resolution:** the record's explicit `components` entry carries the full
  kwargs mapping (`{"type": "merchant", "kwargs": {"shop_key": "…", "service_id": "…"}}`);
  blueprint-only components (no per-record kwargs) are attachable ONLY when every identity kwarg
  is absent from the row (possible for `scripted_dialogue` with an authored `dialogue_key`…
  which is itself identity). Therefore: for the four identity-carrying components, the record
  MUST supply kwargs for every blueprint component it did not explicitly override — a named
  batch rejection otherwise. This keeps "profession: merchant" alone invalid for NPCs whose shop
  key is authored, which is honest: the registry shares the SHAPE, authoring supplies identity.
- **Schedule application** runs only for NPC typeclasses (guarded `isinstance(entity, NPC)`),
  after attributes, before return, same transaction.
- **Tier rule:** `profession.default_tier` applies iff `record["stats"]` is empty; implementation
  is one branch in `_resolve_trait_values` receiving the resolved tier. Literal-stats records
  keep the invariant "imported base stats are literal values".

## Risks / Trade-offs

- [Two assembly entry points drift (loader vs future sync)] → `declarative-service-hosts` calls
  the same `_apply_profession` helper; the shared-helper requirement is named in both deltas'
  tasks.
