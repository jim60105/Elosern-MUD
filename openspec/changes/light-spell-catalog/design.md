## Context

See proposal.md for scope and the amended 2026-08-12 skill-system design §4.3/§4.4 for numeric authority. The engine is Evennia 6.1/Python 3.13, immutable skill data plus deterministic transactional rules. The user requires reusable mechanics and behavior tests only; no light data-contract tests.

## Goals / Non-Goals

**Goals:** Implement this bounded slice through existing typed effects, condition evaluation, buff handling and state writers. Preserve offline play, accurate state/event outcomes and all-or-nothing settlement.

**Non-Goals:** No compatibility layers, migrations, AI state writes, arbitrary expression engine, unrelated spell rebalances, or partial live spell implementations. This turn is planning only.

## Decisions

### D1 — Complete data integration after real behavior
The amended technical design §4.3/§4.4 is the numerical authority; light.md is its lore presentation. Named _spell declarations carry all 16 nodes and policies, not an enlarged positional tuple language. Remove holy_shield and exclusively used light_holy_shield data/references. Keep unrelated light_sword_style and existing mastery/weapon skills. Rebalance goddess_blessing in place. No aliases, automatic save conversion or data migration.

Caps remain proficiency_cap(reverse edges), leaf cap 10. Apotheosis requires exactly blessed_climax Lv.10 AND heavens_judgment_light Lv.10; goddess_blessing is a leaf. Ownership acquisition remains existing import/story/study mechanics, not automatic completion of prerequisites. The tree adds seven nodes and removes one old node, resulting in 16 tree nodes, not 17.

Only this change ships light node definitions, ward/blessing/status bindings and the pain_to_pleasure/priestly_grace passive bindings. Earlier machinery is fully implemented and behavior-tested with synthetic fixtures, but introduces no fake active spell. Ordinary recovery is SELECTED/ANY. Mixed radiance is ENEMIES damage + ALLIES cleanse. Mixed capstone is ALLIES heal + ENEMIES devastation. Emergency heal is SELECTED heal + SELF peak, and therefore not SELF_ONLY as a whole. Contact spells carry generic conditions and resistance policies. No light identifiers in generic executable branches.

### D2 — Behavior-only tests and traceability
Delete the light-specific exact-key/count/label/cost/effect-table assertions and the light tier catalog-pair test; do not re-pin them to 16 rows. test_data_freeze.json entries are per-file allowlists (the `contract` array lists files permitted to name shipped content; `seedDebtPaths` is separate seed-debt accounting), so deleting in-file light echo tests usually leaves the file entries untouched — the files still legitimately name other shipped content. Adjust a freeze entry only when its file no longer references any shipped content, and let `tools.test_data_lint check` output decide; never add a light exemption. Keep meaningful behavior tests and move affected fixtures to the synthetic kit. The buff correspondence rule is removed by sustained-recovery, not waived for light. Change the light requirement to observable lineage and composed-effect behavior; no table of literals in the test contract.

Each generic delta scenario must have substantive synthetic behavior evidence. Get canonical IDs using tools.spec_traceability list when main deltas are synced by the authorized workflow, then annotate the exact tests; never hand-build future IDs or attach unrelated tests to satisfy check. Run local check against the current main index. This proposal turn does not sync or edit main specs.

### D3 — Integration smoke and documentation
Update both player command documents for changed cast availability/lineage and the spell-authoring guide for named typed policies and behavior tests. Do not add commands or aliases. Execute a disposable real-engine scenario using authored recovery, ward, mixed radiance, contact resistance, peak/afterglow, conditional damage and capstone/merge paths. Observe HP/MP/buffs/phase/practice and command/OOB availability, not registry equality. The script is verification evidence only and is removed afterward. No network service is required.

### D4 — Shared interfaces and ownership
| Interface | First owner | Consumers / extensions |
|---|---|---|
| EffectPolicy and SkillDef.effect_policies, per-ordinal normalization | light-effect-potency | routing adds audience; judgment adds DamagePolicy; sacrament adds StateMagnitude; climax adds configured marker maximum |
| Reserved server-bound ResolvedEffect in existing handler context | light-effect-potency | all formula/gate/feedback consumers use trusted policy and source identity |
| Pure audience selection over validated pool | light-effect-routing | mixed catalog nodes; no handler-local faction test |
| Sixth cost label and matching-column precedence | light-divinity-tier | catalog labels and feedback source-tier table |
| Canonical affinity/combat-trait predicates and optional import/spawn data | light-judgment-traits | damage and future conditional schools; never infer from names |
| Recent-action evidence and policy extra strike | light-penance-events | final penitent binding; same producer in battle and field |
| RecoveryRatePolicy, persistent source snapshot, existing tick accounting | light-sustained-recovery | cleric feedback adds recovery-only source multiplier; final ward data |
| Subject-scoped cast conditions, InteractionPolicy, StateMagnitude, stimulus | light-sacrament-casting | climax max override and final contact spells |
| Existing-rule-evaluator state_reactions and phase-scoped markers | light-climax-empowerment | cleric feedback adds actual-damage/new-debuff inputs and pleasure output |
| Complete shipped light data and final authoring/command docs | light-spell-catalog | integration owner only; earlier slices do not publish partial catalog nodes |

Use existing _skill/_spell named builders; preserve the ordinary elemental builder grammar. New public symbols require LSP references before modification; hand-coded cross-file renames are not allowed. Keep source-context bindings immutable and overwrite spoofable request values. Metadata defaults are actual neutral behavior, never stand-ins for unfinished features.

Freeform casting: `is_freeform_eligible` requires every effect prefix to be in {damage, heal, self_heal}. bliss_apotheosis (heal + damage) is eligible and its 10% max-HP rider is scaled by the same freeform stage, per the judgment-traits scenario that orders freeform scaling after every damage component. blessed_climax (heal + pleasure_peak) and the two contact spells (condition/stimulus effects) are not eligible. No special-casing of eligibility by key.

### D5 — Dependency and conflict schedule
| Change | Required predecessors | Hours | Main conflict surfaces |
|---|---|---:|---|
| light-effect-potency | none | 7 | effects.py, registry.py, action.py, combat.py, combat-resolution spec |
| light-divinity-tier | none | 3 | cost_tiers.py, cost-tier tests; skill-registry spec/doc integration |
| light-effect-routing | potency | 7 | effects.py, registry.py, action.py, targeting/read-model tests, skill-registry spec |
| light-judgment-traits | potency | 8 | effects.py, combat.py, import/spawn/entity files, combat-resolution spec |
| light-sustained-recovery | potency | 7 | buffs.py, action.py buff source binding, buff specs/rulebooks |
| light-penance-events | judgment | 7 | effects.py, action.py, combat.py, settlement/surface files |
| light-sacrament-casting | potency | 8 | effects.py, registry.py, action.py, sexual state/settlement, command docs |
| light-climax-empowerment | routing + sacrament | 7 | effects.py, action.py, sexual_state.py, state_reactions/schema/surfaces |
| light-cleric-feedback | divinity + recovery + climax | 8 | reactions, buffs.py, combat.py, items.py, clock/surfaces |
| light-spell-catalog | all above | 6 | final registry/rulebook bindings, test-data contract removal, docs/spec integration |

Recommended conservative future batches: (1) potency + divinity; (2) routing; (3) judgment + sustained-recovery; (4) penance; (5) sacrament; (6) climax; (7) cleric feedback; (8) catalog. Judgment and recovery are separable only if RecoveryRatePolicy lives in the existing buff owner (not effects.py); recovery owns action.py source snapshots, judgment owns combat.py. Final documentation/traceability manifest edits are serialized by the integration owner. Capabilities shared within a batch must be merged requirement-by-requirement, not by replacing whole spec files.

This is advice for later implementation. Proposal authoring and review in this turn are sequential per tmp/propose.md; no parallel subagent execution. Independent logically does not mean merge-safe: all other effects.py/action.py overlaps are serialized. Do not run builds/lints/tests while siblings are editing shared files. A single integration owner applies common import/manifest/doc boundaries and runs focused validation after the batch.

### D6 — Explicit lore resolutions and exclusions
The proposal set already corrects the three-parent diagram, kiss arithmetic, mixed capstone target label, obsolete holy_shield, existing derived caps, no-revival/full-heal wording and generic mastery claims. It explicitly permits blessing's +18/60-second healing rider under the earth defense rule. Penance uses a 60-world-second committed-evidence window rather than undefined blasphemy. Newly chosen ward base 12, grace 10%-per-ordinal, feedback tier values and phase lifetime are marked proposed in both lore and technical design.

No new sexual anatomy/fluid resources, positional combat, clergy quests, secret godhood gate, saintess_vessel, other elemental rebalancing or broad bounds consumer. No program code changes in this planning turn. All runtime state remains solely owned by deterministic rules; AI output never changes policies or world facts directly.

### D7 — Common verification contract
Use unittest.TestCase for pure synthetic policies and the smallest Evennia fixture for real state. Every new test must fail on a plausible behavioral error: formula order, boundary, transition, routing, immunity, persistence or rollback. No source-string assertions, field-copy checks or count snapshots. New modules must be assigned to exactly one .github/evennia-shards.json shard, then run the ownership contract locally with MUD_TEST_SETTINGS=1 through the tool environment.

Focused Evennia invocation: uv run --locked evennia test --settings test_settings.py --keepdb <changed-module-labels>, with MUD_TEST_SETTINGS=1 supplied through the tool env object, never shell prefix. Run tools.observability_lint check in the same final batch as focused tests whenever logging paths change; every new state workflow uses the facade and existing action/clock events with identifiers in context. Run tools.test_data_lint check and tools.spec_traceability check plus openspec validate <change> --strict. Full browser/evidence/aggregate coverage gates remain CI-owned. No local command above ten minutes, no speculative full-suite run.

For the implementation smoke, exercise the actual engine/command/OOB path once offline; do not merely run a test file and call it smoke. No new permanent browser suite for unchanged rendering. Clean temporary scripts only after proof. None of these implementation commands is required to validate the proposal-only artifacts themselves.


## Risks / Trade-offs

- Shared resolver/metadata edits can conflict → follow the integration schedule in ../light-spell-catalog/design.md and serialize common mutation boundaries.
- Lazy Evennia handlers and indirect reactions can write beyond the obvious field → use no-create reads and snapshot every transitive surface before commit; exercise late failures and refetch.
- Broader abstractions can hide unfinished behavior → use the closed typed contracts above, neutral defaults and synthetic cross-school behavior tests, not generic callbacks or placeholders.

## Migration Plan

Implement only after explicit user authorization, in dependency order. No saved-data migration or compatibility alias is planned for this unreleased game. Land code and focused behavior evidence together; defer shipped light definitions to the final catalog integration. If a slice fails its gate, fix or revert that slice before applying dependents, never publish fake fallback effects. Archive/main-spec synchronization and branch merges remain separately authorized operations.
