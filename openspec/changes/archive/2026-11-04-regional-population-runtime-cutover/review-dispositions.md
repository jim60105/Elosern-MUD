# Proposal Review Dispositions

## Review boundary

One blocking rubber-duck critique reviewed the actual proposal, design, delta specification and task artifacts for all nine changes against the regional population design, architecture and current source/contracts. No implementation or independent field-behaviour/content proposal was authorized. The reviewer requested revisions; this document records adopted fixes, without claiming a second reviewer approval.

## Adopted blocking findings

| Finding | Resolution |
| --- | --- |
| Runtime delta targeted a nonexistent renamed startup requirement | Retained the exact current requirement heading, Startup restores combat sessions before wilderness population reconciliation, while changing its body and scenarios. |
| Future losses could disappear after an earlier recovery episode ended | Recovery now replays complete presence transitions as chronological boundaries; L3/local2/due110/loss118 starts a fresh due128 after recovery or earlier explicit cancellation. Delta scenarios and implementation tasks require both cases. |
| A whole-interval site stage could expose later recoveries to earlier regional waves | One maps-owned population_lifecycle coordinator replaces the existing site stage callback, merges exact site/transition/wave boundaries and applies same-tick site births before regional births. It does not add a separately ordered whole-interval regional stage or another time authority. |
| Existing explicit mutation routes were omitted | Owner tasks register actual GM/quest wilderness creation. Recovery enumerates GM spawn/delete, HP setters, existing relocation, quest materialization, combat/upkeep and site lifecycle transitions, with before-write facts and rollback controls. No new verbs or movement gameplay are introduced. |
| Site-composition and saved-seed prerequisites were missing | Hunt supply now depends on manual compositions; recovery also depends on its member-ID/composition contract. The population owner establishes an explicit saved world-seed API before manual sampling, without enabling ordinary births or a missing-seed default. |
| Historical accounting/protection shapes and signatures were incomplete | Recovery defines complete JSON-safe before/after presence, home/site ownership, transition sources, durable coordinate protection intervals, session fields, at_tick projection, timeline initialization/retirement and enclosing compensation. Deleted away-home and protected-session restart scenarios are required. |
| Disengage retained incompatible implementation-freeze and presence language | Its delta now requires stable-ID roster presence, range rejection, no turns and zero active power, preserving contests and confirmed party retreat without prohibiting the necessary identity implementation changes. |

## Additional review notes adopted

Identity tasks now assign shared identity/resolver, session, AI and downstream event/presentation work separately, with subsystem-specific checks while retaining one atomic production cutover. Focused module lists are inventories; workers must select bounded methods/classes rather than concatenate an overlarge test command. The hunt selector's ordinary-variant rationale and the manual-site capability Purpose are explicitly assigned for authoritative-document cleanup during implementation.

## Explicit requirement replacement shape

The following obsolete contracts use REMOVED plus ADDED rather than a partial MODIFIED block that would silently lose current scenarios. Their mutually incompatible old scenarios are deliberately retired; substantively preserved mechanisms remain in the replacement scenarios. Implementation must update assertion-role ledgers and use traceability-tool-generated IDs, with no aliases or empty coverage claims.

| Old requirement | Replacement |
| --- | --- |
| A SINGLE skill opens against the named monster and an AREA skill opens against every living hostile monster in the room | Whole-cell field membership is independent of opening recipients |
| Placement honors capacity and determinism | Placement samples complete deterministic occurrences |
| Published regional species hunts are legally provisionable in their authored region | Published regional hunts require lawful authored sources |
| accept_quest creates one deterministic active record | Quest acceptance persists validated records without ordinary provisioning |
| Population reads share materialization decisions | Population reads report actual living registrations |
| Observation identities survive materialization | Observation identity belongs to persistent individuals |
| Population reconciliation never destroys an active-session participant | Active encounters retain protected individuals and cells |

The changed acceptance requirement has a short mechanism sentence; its preserved issuance, escort, binding, deadline and atomicity detail lives in scenarios. Human ecology, tutorial wording and presentation judgments are assigned to the implementation review document, not requirements whose evidence could only pin shipped copy or balance values.

## Exercised final planning verification

All nine completed changes passed `openspec validate <change> --strict` without warnings. Initial validation rejected omitted scenarios in five changed contracts; those contracts were corrected through explicit retirement/replacement or preserved scenario names, and only the affected validations were rerun successfully.

`uv run --locked python -m tools.contract_gate` passed. Its output reported reference context current, 2694 main requirements covered by 12258 associations with zero uncovered/errors, observability zero violations, test-data zero violations, manifests accepted and 19 contract tests passing. Environment notices about absent secret_settings and unloaded database game-time offset did not prevent the gate from passing.

No game build, focused gameplay test, formatter or runtime smoke was run during proposal drafting. All implementation tasks and runtime smoke evidence remain future work; the contract gate establishes current main contracts rather than coverage or implementation of these unarchived deltas. Planning artifacts alone are committed on the primary branch.
