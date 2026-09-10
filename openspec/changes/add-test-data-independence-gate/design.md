# Design: Test-Data Independence Gate & Classification

## Context

The scan (597 test files) found 341 files referencing shipped-content tokens. Three
populations must be separated: (1) **data-contract tests** — they validate the data
itself (registry sizes, cross-registry coherence, docs parity) and legitimately break
when data changes; (2) **behavior tests** — they validate mechanics and only incidentally
name a shipped id; (3) **debt** — behavior tests asserting shipped literals (291 files).
The rework deletes/renames hundreds of ids; population (2) must stop coupling to (1)'s
inputs. This change builds the enforcement machinery; the 17 `migrate-*` changes execute
(3) → (2).

## Goals / Non-Goals

**Goals:** one authoritative classification record; a CI gate that cannot be silently
weakened; human-obvious classification (a docstring tag); a shrink-only debt ledger.
**Non-Goals:** the synthetic kit itself (`add-test-synthetic-data-kit`), any test-file
migration, production seams.

## Decisions

### D1 — Token universe is derived, never hand-maintained

`tools/test_data_lint.py` imports the shipped catalogs at lint time (via
`django.setup()` + `server.conf.settings`, mirroring the Evennia test bootstrap; no DB
access because every catalog is code/YAML-backed):

- module-level dict/mapping registries: `ITEM_REGISTRY`, `SKILL_REGISTRY`,
  `SUBRACE_REGISTRY`, `RACE_REGISTRY`, `PLAYER_PRESET_REGISTRY`, `NPC_TIER_REGISTRY`,
  `MONSTER_TIER_REGISTRY`, `ELEMENT_REGISTRY`, `ANCHOR_REGISTRY`, `NATION_REGISTRY`,
  `GUILD_RANK_REGISTRY`, `FIXED_TITLE_REGISTRY`, `SHOP_REGISTRY`, `SCENE_ARCHETYPE_REGISTRY`,
  `WILDERNESS_REGION_REGISTRY`, `QUEST_DEFINITION_REGISTRY`, `QUEST_ISSUANCE_REGISTRY`,
  `SEXUAL_ACT_REGISTRY`, `CITY_GATE_REGISTRY`, `NAME_PACK_REGISTRY`, `DIALOGUE_TABLE`,
  `PRICE_TABLE`, `MP_COST_TIERS`, `SUBRACE_STARTING_KIT_REGISTRY`, guild offer maps;
- rulebook YAML keys (`world/rules/rulebook/*.yaml`: buffs, professions, clock periods,
  schedules, behaviours, item/equipment effects, sexual tiers/stages, status display);
- display prose: complete identifier-bearing display values harvested whole from the
  catalogs' label/name fields (e.g. the full `治療藥水`), NOT arbitrary n-grams of
  description prose — a partial-word token like `藥水` would flag ordinary authored
  prose that merely shares a morpheme.

A denylist file (`tools/test_data_lint_deny.json`) records token-exclusions. Admission
is rule-bound, not ad hoc: a token qualifies only if it is (a) a schema field name or
structural vocabulary that collides with a catalog key (e.g. `schema_version`,
`command_defaults`, single-letter direction keys) or (b) a token the scanner proves
present in the non-test production corpus independent of any catalog lookup; every
entry carries a reason and is covered by a scanner regression proving shipped-key
references are still caught. Editing the denylist is a review-visible change to the
gate's semantics. Derived (not snapshot) means the universe tracks renames
automatically; contract tests breaking on rename is their purpose.

`tools.spec_traceability` precedent: deterministic tool, stdlib-only, machine-readable
`check`/`list`/`report` subcommands.

### D2 — Exemptions live in one ledger with two kinds

`tools/test_data_freeze.json`:

```json
{
  "seedDebtPaths": ["<291 paths, frozen>"],
  "contract": [{ "path": "...", "reason": "..." }],
  "debt": ["<291 paths at seed, shrinking to []>"]
}
```

Violation rules (exit 1, JSON output available for migration tooling):

| rule | condition | why |
| --- | --- | --- |
| `unexempted` | flagged file not in `contract ∪ debt` | the core gate |
| `new-debt` | any `debt` path ∉ `seedDebtPaths` | ledger is provably shrink-only |
| `untagged-contract` | `contract` entry whose file lacks the tag line | classification must be human-visible |
| `stale-path` | ledger path missing on disk | ledger cannot rot |
| `duplicate` | path in both kinds or twice | single classification per file |

`seedDebtPaths` is written once (P1 task) and frozen thereafter. Permitted future
mutations are exactly: (a) removing a `debt` entry whose file the gate no longer
flags (the migration shrink), and (b) the atomic debt→contract reclassification for a
seeded debt file legitimately reclassified as a data-contract test: the path must be
in `seedDebtPaths`, is removed from `debt` and added once to `contract` with the tag +
reason in the same commit, and still satisfies every stale/duplicate rule (a
`new-debt`-style recheck rejects any conversion attempt for a path outside the seed).
All 54 classified contract files — including the 4 that currently scan clean (e.g.
`world/lore/tests/test_magic.py`) — receive a `contract` ledger entry plus the tag;
the gate never requires a contract entry to be currently-flagged, so classification is
complete in the ledger.

### D3 — The tag is the classification, the ledger mirrors it

Data-contract test files carry, as the first non-blank line of the module docstring:
`Data-contract test: <one-line rationale>`. JS test files use the first-line comment
`// Data-contract test: <rationale>`. The lint refuses contract registration without it
(rule above), so a reviewer skimming the file learns its class in one line; grepping the
tag enumerates the whole class. Why not a naming convention (`test_data_contract_*`):
renames churn git history/shard manifests and hide class from imports/docs parity tests.

### D4 — One scanner for Python, JS, and browser corpora

- Python: stdlib AST — `ast.Constant` string literals (assert-context and setup-context
  both flagged), attribute/name references to `*_REGISTRY`-style catalog symbols, and
  `len(<registry-ish>) == N` / `assertEqual(len(...), N)` quantity pins reported
  separately as `quantity-pin`.
- Python string grammar: statically resolvable string expressions — literal constants,
  literal-only concatenation, and all-literal f-strings (joined and the pieces flagged),
  so `f"{'healing'}_potion"` cannot smuggle a shipped key.
- JS/TS (vitest + Node gate + `web/tests/browser/**` seed helpers): template/string
  literals including literal-only template literals and concatenation (same corpus
  exclusions as the coverage gate: never `dist`, `node_modules`).
- Test-file definition: `git ls-files` paths matching `tests/`, `test_*.py`, `*.test.*`,
  `*_spec.*` under `commands/ server/ typeclasses/ world/ web/ tests/ tools/tests/`.

### D5 — Wiring

CI: a `test-data-lint` step in the existing `quality-gate.yml` beside
`observability-lint` and `spec-traceability` (same uv-locked invocation). Local:
AGENTS.md uv-workflow block lists the command; `docs/development/evennia-testing-guide.md`
gains the authoring rule (kit or local fixtures for behavior tests; tag+ledger only for
data-contract tests; meaningful assertions over data echoes; coverage is a ≥80% floor,
not a target — data-echo tests are replaced, not multiplied).

### D6 — Seed is mechanical, classification is reviewed

`check --seed` regenerates the ledger deterministically from a classification list the
gate carries as data (`tools/test_data_lint_seed.json`: the 54 contract paths + reasons;
Appendix A). Human review happened once (this change's scan + Appendix A); the seed
subcommand exists only for the initial commit — deleting it afterwards is not required
but `check` never re-seeds.

## Risks / Trade-offs

- **False positives on prose**: a test asserting the CJK word `酒館` (also a data label)
  from player prose would flag. Mitigation: denylist entries with reasons, and the rule
  that flags are per-file — migration changes resolve their own false positives by
  narrowing literals or (with review) denylisting genuinely generic words.
- **Catalog import cost in CI**: ~2-5 s of `django.setup()` per lint run. Accepted.
- **Contract-classification judgement calls**: Appendix A is the record; misclassified
  files move classes by the atomic debt→contract conversion (D2), same PR.
- **Coverage gate interaction**: migration changes must not net-delete behavior coverage;
  the `≥80%` aggregate stays owned by CI, untouched here.

## Migration Plan

Day one: seed lands green (341 exemptions). Each `migrate-*` change removes its files'
debt entries in the same commit that makes them clean; mid-flight PRs are internally
consistent, so `check` is never red for an unrelated branch. End state: `debt: []`,
54 tagged contract files, seed list retained as history.

Ownership for parallel execution: test-file edits are area-partitioned and may land in
any order, but the two shared resources are serialized — every ledger removal rebases
onto the current `tools/test_data_freeze.json` (the shrink-only ratchet makes a dropped
removal fail the owner's own gate, and the per-area closure test names the exact removed
entries), and kit-shape extensions to `world/tests/synthetic_data.py` go through the
kit's own change or one designated integration batch, never a silent in-migration edit.

Data-rework handoff: when the game-data rework lands, it updates tagged data-contract
expectations in the same change, and only where the authored data contract intentionally
changed — a contract failure is evidence of a contract change, not a reason to preserve
old content. Behavior migrations keep their assertions against the same production
branches; deletions name their branch-evidence replacement.

## Appendix A — contract classification (seed)

| file | reason | ledger |
| --- | --- | --- |
| `tests/test_command_docs.py` | player command docs parity contract | contract |
| `tests/test_preset_authoring_docs_contract.py` | authoring docs contract | contract |
| `world/lore/tests/test_anchor_placement.py` | anchor placement data contract | contract |
| `world/lore/tests/test_anchors.py` | anchor data contract | contract |
| `world/lore/tests/test_economy.py` | price-table data contract | contract |
| `world/lore/tests/test_elements.py` | element data contract | contract |
| `world/lore/tests/test_guild.py` | guild registry content contract | contract |
| `world/lore/tests/test_items.py` | item registry content contract | contract |
| `world/lore/tests/test_magic.py` | magic tier data contract | contract |
| `world/lore/tests/test_monsters.py` | monster tier data contract | contract |
| `world/lore/tests/test_names.py` | name-pack corpus contract | contract |
| `world/lore/tests/test_nations.py` | nation data contract | contract |
| `world/lore/tests/test_npc_tiers.py` | npc tier data contract | contract |
| `world/lore/tests/test_player_presets.py` | player preset data contract | contract |
| `world/lore/tests/test_races.py` | race/subrace data contract | contract |
| `world/lore/tests/test_scene_archetypes.py` | scene archetype data contract | contract |
| `world/lore/tests/test_sex.py` | sex vocabulary contract | contract |
| `world/lore/tests/test_sexual_vocab.py` | sexual vocabulary contract | contract |
| `world/lore/tests/test_shops.py` | shop registry content contract | contract |
| `world/lore/tests/test_starting_kits.py` | starting-kit data contract | contract |
| `world/lore/tests/test_sync.py` | lore cross-registry sync contract | contract |
| `world/lore/tests/test_titles_registry.py` | fixed-title registry content contract | contract |
| `world/lore/tests/test_wilderness_entry.py` | wilderness entry data contract | contract |
| `world/lore/tests/test_wilderness_regions.py` | wilderness region data contract | contract |
| `world/maps/tests/test_altoria_capital.py` | capital xymap data contract | contract |
| `world/maps/tests/test_bootstrap.py` | map bootstrap/gate data contract | contract |
| `world/maps/tests/test_city_movement_cost.py` | city movement cost data contract | contract |
| `world/maps/tests/test_city_walkthrough.py` | capital map walkability contract | contract |
| `world/quests/tests/test_compile_blueprint.py` | quest compile data-contract surface | contract |
| `world/quests/tests/test_compile_offline.py` | quest compile data-contract surface | contract |
| `world/quests/tests/test_compile_registration.py` | quest compile data-contract surface | contract |
| `world/quests/tests/test_definitions.py` | quest definition catalog contract | contract |
| `world/quests/tests/test_scenario_mapping.py` | scenario mapping data-contract surface | contract |
| `world/rules/tests/test_affinity_config.py` | affinity config validation contract | contract |
| `world/rules/tests/test_clock.py` | clock rulebook contract | contract |
| `world/rules/tests/test_equipment_effect_rulebook.py` | equipment effect rulebook contract | contract |
| `world/rules/tests/test_guild_config.py` | guild/shop config validation contract | contract |
| `world/rules/tests/test_monster_behaviour_profile.py` | monster behaviour rulebook contract | contract |
| `world/rules/tests/test_npc_schedules.py` | npc schedule rulebook contract | contract |
| `world/rules/tests/test_profession_config.py` | profession config contract | contract |
| `world/rules/tests/test_rulebook_schema.py` | rulebook schema contract | contract |
| `world/skills/sexual_acts/tests/test_acceptance.py` | sexual act acceptance catalog contract | contract |
| `world/skills/sexual_acts/tests/test_combat_catalog.py` | sexual act catalog contract | contract |
| `world/skills/sexual_acts/tests/test_divine_core_catalog.py` | sexual act catalog contract | contract |
| `world/skills/sexual_acts/tests/test_divine_mutators_catalog.py` | sexual act catalog contract | contract |
| `world/skills/sexual_acts/tests/test_interspecies_catalog.py` | sexual act catalog contract | contract |
| `world/skills/sexual_acts/tests/test_partner_catalog.py` | sexual act catalog contract | contract |
| `world/skills/sexual_acts/tests/test_registry_structure.py` | sexual act registry structure contract | contract |
| `world/skills/sexual_acts/tests/test_seed_acts.py` | sexual act seed catalog contract | contract |
| `world/skills/sexual_acts/tests/test_shame_catalog.py` | sexual act catalog contract | contract |
| `world/skills/sexual_acts/tests/test_solo_catalog.py` | sexual act catalog contract | contract |
| `world/skills/tests/test_cost_tiers.py` | MP cost-tier assignment contract | contract |
| `world/skills/tests/test_skill_registry.py` | skill registry content contract | contract |
| `world/skills/tests/test_spell_catalogs.py` | spell catalog content contract | contract |
