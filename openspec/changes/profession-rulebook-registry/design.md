# Design: profession-rulebook-registry

Decisions are ratified in `docs/superpowers/specs/2026-09-05-profession-registries-design.md`
(D1 assembly-time blueprint, D2 rulebook YAML, D6 binding stored-not-read). This file records
only the implementation-level choices local to this change.

## Context

`world/rules/guild_config.py` is the family pattern: module-level frozen dataclasses loaded from
`world/rules/rulebook/*.yaml`, batch-validated at import/load with a named error, exposed through
a cache-read function. `profession_config.py` copies that shape exactly.

## Goals / Non-Goals

**Goals:** one validated profession table; every malformed file rejected with a named error before
anything is cached; the shipped rows exactly replicate today's two hardcoded host assemblies so
the sync conversion later is provably behavior-neutral.

**Non-Goals:** reading `default_binding` anywhere; import-record fields; sync or loader changes;
any new profession content beyond the three replicas.

## Decisions

- **Component-type vocabulary lives in the loader as a closed set** (`merchant`, `guild_staff`,
  `guild_examiner`, `scripted_dialogue`, `monster_behaviour` only if a component exists for it —
  the shipped set is exactly the classes in `typeclasses/components.py`, mapped
  snake-case-type → Component class). A contract test asserts the vocabulary equals the
  component classes discoverable in `typeclasses/components.py`, so a new component can never be
  un-declarable (the test names the drift). Alternative considered: import the classes directly
  by path and derive the vocabulary at runtime — rejected because the YAML keys are authored
  strings and the contract test is what pins the mapping.
- **Cross-validation sources:** `schedule_template` keys against
  `npc_schedules.get_schedule_registry()`-equivalent loaded template table (the module's own
  rulebook load), `default_tier` against `world.lore.races.STATIC_TIER_REGISTRY`, and
  `default_binding` against the closed `{person, place}` set (R2 owns semantics).
- **File shape:** top-level `schema_version: 1` + `professions:` list; `key` unique; unknown
  top-level keys rejected (mirrors the strict YAML posture of the schedule rulebook).
- **Read surface:** `get_profession(key) -> Profession | None` and `all_professions()`, frozen
  dataclasses (`Profession`, `ProfessionComponent(type_key, default_binding)`), plus
  `load_professions_into_cache()` for startup wiring exercised by tests only in this change.

## Risks / Trade-offs

- [Vocabulary drifts from `components.py`] → contract test fails naming the unmapped class.
- [`default_binding` stored-but-unused confuses readers] → module docstring + registry field
  comment point at the service-anchoring change as first consumer (accepted seam per AGENTS.md:
  deliberate seam beats a fake consumer).
