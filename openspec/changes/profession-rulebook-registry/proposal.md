# Proposal: profession-rulebook-registry

## Why

"Profession" does not exist as a datum today: the sharing that professions imply is scattered
across capability components keyed by `shop_key`/`branch_key`, schedule role templates, and
free-text narrative roles. Authored content (YAML rulebooks + JSON import records — the two
surfaces the design docs and the user's workflow treat as the content pipeline) has no place to
declare "this NPC is a merchant". This change lands the profession registry itself, the
foundation the service-anchoring and declarative-host changes consume.
Source design: `docs/superpowers/specs/2026-09-05-profession-registries-design.md` (R3, D1–D2, D6).

## What Changes

- New `world/rules/rulebook/professions.yaml`: a keyed profession table (`key`, `components[]`
  with `{type, default_binding}`, `schedule_template`, `default_tier`), shipped with exactly the
  three professions replicating today's hardcoded host assembly (`merchant`, `guild_staff`,
  `guild_examiner`), all with `schedule_template: null` / `default_tier: null` so the later
  sync conversion stays behavior-neutral.
- New loader `world/rules/profession_config.py` following the `guild_config.py` family: frozen
  dataclasses, whole-file batch validation with `ProfessionConfigError` naming every offense,
  `get_professions()` cache read, cross-validation against the schedule rulebook and
  `STATIC_TIER_REGISTRY`, and a component-type vocabulary whose closed set is contract-tested
  against `typeclasses/components.py`.
- `default_binding` (`person | place`) is validated for vocabulary and **stored but not read by
  any runtime gate in this change** — the service-anchoring gate is its first consumer (R3 D6).
- No import-record field, no sync rewrite, no component assembly here — changes
  `profession-import-assembly` and `declarative-service-hosts` build on this registry.

## Capabilities

### New Capabilities

- `profession-registries`: the professions rulebook file, its validation matrix, the keyed
  frozen read surface, and the component-type vocabulary contract.

### Modified Capabilities

None. Nothing reads the registry yet.

## Impact

- New: `world/rules/rulebook/professions.yaml`, `world/rules/profession_config.py`,
  `world/rules/tests/test_profession_config.py` (register in `.github/evennia-shards.json`).
- Depends on: nothing. Dependents: `profession-import-assembly`, `declarative-service-hosts`,
  `service-anchoring-gate` (reads `default_binding` off components assembled by those changes).
- No player-facing commands, no settings, no webclient surface.
