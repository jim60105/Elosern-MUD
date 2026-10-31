# Design

## Context

The registry already supplies AND prerequisite edges, reverse consumers, transitive ownership closure and exact-minimum XP seeding. `can_use_skill` currently checks its immediate edges. `freeform_mastery_entitled` in `world/rules/progression/_scaling.py` currently checks bare direct ownership. Both practice entry points in `world/rules/progression/__init__.py` award ACTIVE XP, notify already-owned consumers, then evaluate cross-lineage rules. `grant_owned_skill` in `world/rules/cross_lineage_unlock.py` supplies identity-safe append-if-absent writes and committed dialogue refresh. Cross-lineage multi-key scopes use OR semantics and are unsuitable for duplicating whole-tree mastery prerequisites.

`build_lineage_view` in `world/rules/lineage_query.py` currently computes `consumed = all(node.capped for node in nodes)`. Passive Lv.0 can never reach a positive XP cap. Action, cast-settlement and clock rollback surfaces already include `skills` and `skill_proficiency`; reuse them.

## Goals / Non-Goals

Finish the existing mastery lifecycle in one engineer-day without adding a persisted model or a second grant rulebook. This change owns graph/entitlement/acquisition logic and passive completion. It MUST NOT edit preset rows, affinity classification, race ranges, resource costs, ordinary spell edges, monster skill definitions or freeform shape/ladder constants. Other weapon trees are unimplemented and separately scheduled; this scope statement carries no rejection of their implementation.

## Decisions

### D1. Authored mastery edges, one prerequisite authority

Edit `world/skills/registry/data_enhancement_masteries.py` only for the eight existing mastery definitions, importing `SkillPrerequisite` through the file's existing vocabulary convention. Each mastery declares every terminal of its unrestricted ordinary ACTIVE elemental catalog at Lv.10, in registry order. The current content choices are below. These are data decisions, absent from normative specs.

| Element | Terminal prerequisite keys, all Lv.10 | Mastery label |
| --- | --- | --- |
| fire | `flame_shroud`, `scorching_armor`, `crimson_apotheosis` | 火焰精通 |
| water | `water_shield`, `abyssal_surge`, `abyssal_maw`, `abyssal_heart` | 水流精通 |
| wind | `haste_domain`, `sky_apotheosis` | 疾風精通 |
| earth | `earthen_ward`, `thorned_carapace`, `earthen_apotheosis` | 大地精通 |
| lightning | `thunder_shatter_strike`, `thunder_prison`, `thunder_apotheosis` | 雷霆精通 |
| ice | `frost_mire`, `crystal_shatter`, `eternal_frost_apotheosis` | 寒冰精通 |
| light | `sanctified_ward`, `goddess_blessing`, `bliss_apotheosis` | 光輝精通 |
| dark | `dark_dominion`, `abyssal_apotheosis` | 闇影精通 |

The graph universe is `SkillKind.ACTIVE`, `SkillCategory.ELEMENTAL_MAGIC`, same registered element/group, with unrestricted `SkillEligibility` (no actor/race/subrace/species restriction or required capability). Existing public catalog rows remain ordinary even when their names sound monstrous. Element-tagged martial skills are outside this universe. `flight` remains an independent enhancement passive. Preserve all existing ordinary thresholds and terminal caps; adding Lv.10 consumers leaves the current Lv.10 terminal caps unchanged. Update mastery descriptions to acquired whole-tree command/freeform entitlement, with no claimed flat damage or magic-stat bonus.

Keep `validate_prerequisite_graph` and `rebuild_prerequisite_caches` unchanged. Existing graph validation handles references and cycles. A generic registry-integrity test derives ordinary terminals from category/group/eligibility and verifies their relationship to each mastery, with thresholds preserving pre-mastery derived caps. It reads authored progression constants and never copies the endpoint roster or numeric approval table. Keep synthetic graph-cache rebuilding independent of production catalog-content checks. No runtime endpoint list and no duplicate YAML grants.

### D2. One lawful closure query shared by grant and entitlement

Add in `world/rules/progression/_gates.py` and export through `progression/__init__.py`:

```python
def mastery_prerequisites_met(
    entity: Any, skill: SkillDef, *, owned_keys: Any = None
) -> bool:
    ...
```

The function is a pure predicate. The target must be a registered PASSIVE elemental-mastery definition with nonempty prerequisites and pass `skill_identity_eligible` and `skill_effect_allowed`. It does not require ownership of the target, because acquisition calls it before granting. Traverse its complete prerequisite DAG using a local visited set. Every ancestor must be directly owned, identity/effect eligible, and every declared ancestor edge must meet its minimum `skill_proficiency_level`. Unknown keys fail closed. No ownership/XP repair and no conferred-grant substitution occur. Read stored XP and registry edges; avoid repeated traversal of shared ancestors.

`can_use_skill` keeps existing behavior for ordinary skills. For elemental mastery it additionally requires `mastery_prerequisites_met`, after its existing direct-ownership/identity/restriction checks. `freeform_mastery_entitled(entity, element, *, owned_keys=None)` keeps element validation first, resolves the corresponding existing registry mastery, then delegates to `can_use_skill` with the direct-owned set. Missing registry mastery returns false. This denies a bare injected key, an ineligible/restricted ancestor, absent root, low ancestor XP, conferred mastery and conferred prerequisites. Preserve optional `owned_keys` snapshot forwarding for AI callers.

The recursive check is needed because explicit imported ancestor XP can leave an internal edge unmet while terminal XP satisfies the immediate mastery edges. Shallow terminal qualification would authorize an invalid tree.

Extend `missing_prerequisite` for mastery to find the first unmet ownership/XP edge in deterministic declared-edge traversal through the closure; ordinary skills retain their current immediate-edge behavior. `lineage_query` can then name a low internal ancestor. In `world/rules/action/gates.py::ownership_failure`, reject a registered owned PASSIVE as `SKILL_NOT_ACTIVE` after its existing target identity/restriction checks and before ACTIVE lineage rejection formatting. Preserve ACTIVE rejection order. This is required because a mastery can now fail the boolean gate solely through a restricted ancestor without an unmet numeric edge; passives cannot be submitted as actions and must never reach the old unchecked `unmet.skill_key` dereference. Add a synthetic passive-submission regression to the existing action rejection tests.

### D3. Practice acquires the passive through the existing writer

Add private `_grant_ready_masteries(entity: Any, changed_key: str) -> list[str]` in `world/rules/progression/__init__.py`. Starting from the existing reverse consumer cache, visit descendants of the changed key to find affected mastery passives; a repaired internal ancestor can be relevant even when it is not a direct mastery parent. Sort candidate keys for deterministic storage and notices. Skip already directly owned keys. Call `mastery_prerequisites_met` and then lazily import/reuse `cross_lineage_unlock.grant_owned_skill(entity, candidate.key, SKILL_REGISTRY)`.

Invoke after `award_practice_xp` on BOTH `grant_skill_practice_xp` and `grant_study_practice_xp`, inside the caller's existing transaction and after ordinary unlock-flip evaluation. Append one `_unlock_notice(entity, candidate)` per successful new grant to the optional existing sink. Grant even without a sink. Keep cross-lineage evaluation and its notices intact. A mastery already owned that changes unusable-to-usable through repaired ancestor XP must also produce one notice: snapshot affected mastery usability before the award, compare after, and deduplicate against immediate-consumer flips and new-grant notices by key for that award. Do not print or publish from progression.

No passive XP is awarded; passive practice requests still return false. Nonlethal use, failed awards and dedupe refusals do not grant. A repeated/capped endpoint award may reevaluate mastery, but append-if-absent produces no repeat ownership or notice. Concurrent settlement follows the existing single-writer transaction contract; add no second transaction owner or independent commit.

### D4. Closure/seed and display completion

Keep `lineage_ownership_closure`, `seed_lineage_proficiency`, `normalize_lineage_record`, `apply_lineage_auto_seed` and `_preset_lineage_state` as the shared construction mechanisms. Mastery edges now make declaration of a mastery include every ordinary branch and seed the minimal needed XP. Explicit entries still win, including insufficient ones. Accept otherwise-valid explicit-low-XP records and deny mastery use/entitlement until the whole closure is lawful; do not silently overwrite, strip the declared passive or add a special import rejection. Identity-invalid records continue to reject atomically through existing validation. Do not pin an exact number of production callers; current callers also include host construction.

In `lineage_query._node_view`, set passive completion (`capped`) to `owned and usable`, with level and XP at their genuine stored/derived values and `xp_to_next_level = 0` for a complete passive. An unowned or unusable passive is incomplete. For ACTIVE nodes, retain XP-cap calculation and require ownership/usability for graph completion. Define `consumed` as every ACTIVE node owned, usable and XP-capped, and every PASSIVE node owned and usable. `completed_count` follows these graph flags. No passive XP fabrication, no schema/version change, no new frontend rules. Ready mastery must require identity, restrictions, direct prerequisite ownership and the lawful closure. Text and OOB consumers keep reading the same model.

### D5. Specification and documentation cutover

Modify existing requirements without losing unrelated scenarios. Remove the four `skill-lineage` authored fire/wind/ice/lightning topology requirements, whose node lists and passive exclusions conflict with this change and the no-game-data-in-specs rule. Preserve those catalogs in `docs/lore/skill-trees/{fire,wind,ice,lightning}.md`; no gameplay deletion. Generic graph validation remains specified, supplemented by the new generic whole-tree mastery requirement. Reassociate each affected test claim by assertion role, recorded before editing in this change's `traceability-cutover.md` during implementation; do not mechanically substitute decorators. Obtain canonical IDs from `tools.spec_traceability list` against the existing and merged-equivalent spec trees, never guessed strings. ADDED behavior tests temporarily claim the closest current mastery requirement, with the mapping documented, until archive provides the new canonical IDs.

Explicitly amend `docs/superpowers/specs/2026-08-30-use-driven-progression-design.md` §9.1 (currently lines 235-238), §9.2 bare-key entitlement and §12 completion. Amend `docs/lore/skill-trees/index.md` §1 outside-tree statement, `docs/lore/magic-system.md` and all eight elemental tree pages' mastery placement. Preserve flight's independent position. The stale `element-mastery` main Purpose is a known pre-existing description; during future spec sync update it to lawful learned mastery, without touching it during proposal creation.

Retain existing MODIFIED scenario headings as OpenSpec merge identities, including the historical `Exactly three production callers` and `Consumed means every node capped`. Their updated WHEN/THEN clauses define shared construction without a fixed caller count and completion with usable passive ownership; the old headings add no separate count or passive-XP rule.

## Evidence and acceptance map

Extend existing modules only; add no new shard or browser test files. Use fixed synthetic registries and independently known expected results. Every ADDED/MODIFIED requirement has a discoverable test target below.

| Requirement / mechanism | Existing test module to extend | Observable assertion |
| --- | --- | --- |
| whole-tree prerequisite coverage | `world.rules.tests.test_skill_lineage` | Synthetic disconnected components and a side leaf all gate mastery; generic catalog-integrity assertion detects omitted/foreign/restricted/cap-changing edges; independent passive excluded |
| lawful direct entitlement | `world.rules.tests.test_freeform_casting.test_scale_tables_and_synthetic_lookups` | Bare mastery, conferred ownership and low internal ancestor deny; full direct closure grants; unknown element raises; query writes nothing |
| use/study acquisition | `world.rules.tests.test_progression.test_derived_and_cross_lineage_unlocks` | Last required XP grants one passive in both entry points, with/without sink; missing branch/ownership/identity does not; re-award produces no duplicate |
| closure and explicit precedence | `world.rules.tests.test_skill_lineage`; `world.rules.tests.test_progression.test_preset_lineage_and_npc_policy` | Identical inputs produce identical closure/minimum seed across preset/import/scene; explicit low ancestor retained, mastery denied until repaired |
| passive graph completion | `world.rules.tests.test_lineage_query` | Usable passive at Lv.0 completes; unowned/unusable passive or unowned ACTIVE does not; roots/merges deterministic; no writes |
| scaled-cast boundary | `world.rules.tests.test_freeform_casting.test_resolver_gate_and_scale_contract` | Invalid closure rejects nondefault scale; default scale and existing shape/ladder behavior unchanged |
| transaction and notification boundary | `world.rules.tests.test_cast_settlement`; `world.rules.tests.test_progression.test_derived_and_cross_lineage_unlocks` | Failure after grant restores raw and cached ownership/XP, tick claim retry remains possible, no notice/dialogue event escapes; committed companion notice names learner |

Use a synthetic mastery with synthetic element marker inside the existing registry kit, adapting kit fixtures in-place to lawful closure. Generic production integrity checks may inspect current rows for references and graph relations; never assert an endpoint roster, display label or balance threshold. Existing shipped-data smoke helpers that inject a mastery must construct its lawful closure, without hardcoded endpoint lists.

## Risks / Trade-offs

- Whole-tree validity costs a DAG traversal per entitlement query. Reuse one local owned snapshot and visited set; never persist a derived entitlement cache.
- Mastery joins disconnected components and changes graph counts. Consumers read existing counts and full prerequisite labels; preserve deterministic truncation and test graph validity rather than fixed roster counts.
- Explicit-low-XP imports can retain an unusable passive. This preserves author precedence and denies the exploit without changing the general import contract.

## Human review document

Use this `design.md`, D1 and D5, as the mastery wording/placement review document. Review that labels and descriptions describe whole-tree learned command, omit arbitrary magic-stat bonuses, leave ordinary branch identities intact and keep other weapon-lineage scheduling neutral. These prose qualities are reviewed by a person; automated tests establish graph and entitlement mechanisms.

## Migration Plan

Pre-release clean cutover. Existing source-authored presets/import fixtures obtain prerequisite closure through the existing construction flow. No saved-world backfill, compatibility alias or migration. Roll back by reverting the implementation change as a unit; never partially revert prerequisite data away from its gate.
