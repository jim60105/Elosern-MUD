# Design

## Context

The approved authority is `docs/superpowers/specs/2026-10-09-monster-resource-skills-design.md` sections 3, 7 and 8. Architecture sections 3.1 and 5.2 retain read-only `world/skills/` and `world/lore/`; writes stay in `world/rules/`. Current `SkillDef` lives in `world/skills/registry/vocab.py`; builders and divine/sexual declarations still pass the old marker. `can_use_skill` in `world/rules/progression/_gates.py` already combines ownership with `skill_effect_allowed`, then checks edges. Resolver gates independently check the divine flag and can assume a false use result has a missing edge. `SkillHandler`, combat modifiers and status breakdown already share the pure restriction reader. See proposal.md for scope.

## Goals / Non-Goals

Deliver a standalone clean qualification cutover without crocodile content or damage dependencies. Preserve universal actions, category cadence, acquisition and command contracts. Do not define new races, abilities, migrations, compatibility fields or rule expressions. Synthetic identities supply the general mechanism's evidence.

## Decisions

### Typed immutable metadata and one pure query

Add a frozen eligibility record to `SkillDef` and propagate it through builders. Use optional tuples for allowed actor kinds (player, NPC, monster), races, subraces and species, plus a closed required-capability tuple initially covering `can_use_divine_arts`. Omitted lists are unrestricted; explicit empty allowed lists fail. Validate reference membership and satisfiability at registry validation, including every allowed subrace's registered parent if a race list is present. Race/subrace/capability restrictions require character identity and species restrictions require monster identity; an actor-kind set must have a satisfiable intersection. Do not require unrestricted skills to invent missing identities.

Put the pure record evaluator and runtime identity adapter in `world/skills/eligibility.py`. Accept intended actor kind and authored identity for import/preset validators. Runtime classification uses deterministic typeclass identity, checking Monster before character inheritance; adapters read stored keys without provisioning handlers. Races/subraces use existing registries; species qualification validates species/variant membership. No variant eligibility field is added. Do not classify by presence of race/species/threat-tier attributes. Lazy typeclass references or their existing identity predicates avoid bootstrap coupling.

Keep registry load validation separate from runtime reads and prevent a skills-to-rules import or a monster-registry-to-skill-assembly cycle. Lore's variant kit fields remain plain frozen references; complete kit validation is construction-owned in the later consumer. A second predicate in action gates or hardcoded race-name checks would diverge and is rejected.

### Runtime and passive consumers

Compose identity qualification with existing restrictions in the shared read-only qualification path, then have `can_use_skill` retain owned-key and prerequisite checks. Update resolver, preview and submission rejection paths to distinguish identity failure before looking for an unmet edge. Keep existing unowned/unmet-edge reasons and return a named identity rejection for identity failures, updating presentation reason mappings with tests. Reject before dice or any staged write.

Apply the pure identity query to directly owned and recipient-conferred passive reads, including trait multipliers, rule-table `skill_owned` adjustments, movement waivers and status breakdown. `record_conferred_grant` rejects identity-ineligible recipients, and conferral planning omits no validation needed by the primitive. Source ownership and grant shape remain separate. Current restriction checks in handler.py, combat_modifiers.py and status_query/breakdown.py are reusable integration seams. No persistent state writes enter skills.

### Divine definition, acquisition and authored-kit cutover

Replace every old field/argument in registry/vocab.py, builders.py, data_divine_mystery.py, data_utility_passives.py and sexual_acts/{_builder,divine,__init__}.py. The sexual family pleasure-ratio exception and mastery blanket exclusion inspect the declared required divine capability, regardless of whether the reader's race would qualify. Eligibility never becomes an automatic divine acquisition rule. Keep `RaceProfile.can_use_divine_arts` and values untouched. DIVINE_MYSTERY family validation requires that capability, empty cost and existing effect vocabulary; daily cadence remains category-based.

Update world/imports/validate.py, player_presets/validation.py, prerequisite closure validation and the core grant/ownership paths before any persistent ownership is accepted. Closure-added keys must qualify too. Degraded registry reporting remains the existing import policy; do not add a fallback. Update synthetic data_skills.py and every affected test builder/assertion, including registry-contract field inventories, sexual structure, divine cadence/gate and preset/import tests. Delete the independent divine action gate and old aliases rather than preserving a compatibility surface.

### Presentation and main contracts

Filter identity-ineligible catalog entries via the same pure query in status readers, character skill serialization and any full-registry player menus. `lineage_query.py` admits identity-eligible roots/nodes, derives closure/order and counts over those entries, and leaves isolated roots absent. Identity does not substitute proficiency, ownership or MP checks. No frontend payload version or command syntax changes are intended. Modified deltas reproduce entire existing requirement blocks and preserve unaffected scenarios; headers containing the former marker remain exact archive match keys, not runtime aliases.

## Risks / Trade-offs

Import cycles are a risk; use pure lore references and keep construction validation outside lore assembly. Passive leaks are a risk; exercise multiplier, rule-table, movement and conferred cases through real consumers. Catalog filtering can distort counts; compare synthetic eligible/ineligible chains and retain root-consumption semantics. Broad divine mechanical edits fit one workday only as a single shared metadata cutover with existing consumer seams; do not add content or split into a deployable half-cutover.

## Migration Plan

Pre-release clean replacement, with no migration, legacy field or adapter. Persisted ownership keys remain unchanged; runtime qualification contains corrupt assignments. Deploy as one self-contained prerequisite, verify and archive before applying the crocodile consumer. Rollback reverts the whole cutover rather than exposing parallel gates. Recommended sequencing and file conflicts are in proposal.md.

## Planning assumptions

The one-engineer-day estimate in proposal.md is a planning assumption rather than measured feasibility evidence. This is a single deployment unit because a partial divine marker cutover would leave parallel qualification paths. The final full-set review found no eligibility blocker; its two crocodile main-contract findings are resolved in that consumer's registry delta.

## Planning validation evidence

On 2026-10-09, `openspec validate shared-skill-identity-eligibility --strict` and the explicitly requested `openspec validate shared-skill-identity-eligibility --type change` both passed. The initial strict run identified a renamed retained scenario; its original matching title was restored before the passing run. Artifact writing-style checks have zero errors; warnings in retained main-contract wording were accepted as existing technical labels.

The final repository-root `uv run --locked python -m tools.contract_gate` passed, reporting 2028 requirements and 8277 associations, 2028 covered, zero uncovered/errors; observability scanned 668 with zero violations; test-data scanned 1231 with zero violations; manifests passed and all 18 contract tests passed. This is planning/checkout evidence, not implementation or runtime smoke evidence. No builds or gameplay tests were run.

Final commits are owned by Main under the revised assignment; proposal files remain uncommitted for that handoff. Before commits, `os-phase shared-skill-identity-eligibility` returned exit 2, unknown change. Main must record the expected proposed phase after its directory-scoped commit. The unrelated human_guild_hosts.py edit was left intact.
