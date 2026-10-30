# Design

## Context

Observed owners and nearby test targets: world/maps/wilderness_population.py ensure_population/population_for_coordinates/species_rule_for_coordinates and site/session branches; provider at_prepare_room; test_wilderness_population.py and test_wilderness_population_species.py.

## Goals / Non-Goals

Project live and prospective population without materializing objects. Keep the named slice complete and independently runnable after prerequisites; dependent behavior is owned elsewhere.

## Decisions

The current materializer includes hunting-band baseline, authored ambient species slots, monster sites, foreign registered objects and persisted-session protection. Extract one immutable PopulationDecision shared by ensure_population and new population_view(wilderness,cells). Materialization remains the exclusive create/remove/register owner; the view never prepares rooms, invokes ensure_population, changes Attributes, registers objects or ticks time. Preserve all current branch semantics, including hunting-band behavior, living individual retention and protected combat participants. No density rebalance or respawn cooldown.

Model-owned observation keys must survive prospective-to-real entry: population:<wilderness>:<x>:<y>:<branch>:<slot>; existing registered materializations occupying a slot use that same key, site slots use stable site/slot identity, foreign registered objects use object:<dbid>. Never key by pooled room or by a newly assigned object ID for an expected slot. Living/dead/departed visibility follows what the shared decision would retain or spawn now. No approximate second baseline hash. Other registered characters/NPCs use existing hostility rules; do not mark all objects hostile.

Return frozen internal records observation_key/cell/kind/hostile/allowed label facts, not protocol payloads. Internal cell coordinates support later sight filtering. Iterate requested cells and existing coordinate registrations, never the whole frame. Synthetic tests compare view then ensure_population on hunting/baseline/species/site/foreign/protected branches and assert stable keys. Before/after snapshots cover object counts, room pools, registries, stored Attributes and clock. Existing expected-population semantics may predict an eventual respawn; the read itself creates nothing. Document read-versus-materializer API in existing population notes.

## Dependency contracts

Independent root slice.

## Planning and implementation boundaries

This artifact set covers sub-project1 only. Read the [blueprint](../../../docs/superpowers/specs/2026-10-30-wilderness-travel-mode-blueprint-design.md) §7.1, the [detailed sight design](../../../docs/superpowers/specs/2026-10-30-wilderness-sight-and-fog-reveal-design.md) and [engine architecture](../../../docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md) §§2/3/6.5/10. Preserve single-writer ownership and server exploration mode. No travel HUD/input queue/log/tint, camping/dream/art changes, authored geography/landmark-content changes, new roads, migrations or compatibility paths. Generated elevation and the approved sight rulebook are explicitly allowed.

Implementation will be performed by gpt-luna-level workers. Follow the named owners and exact contracts; read each prerequisite design first. Do not invent downstream stubs or leave unresolved behavior to a worker. Each change is capped at one workday including focused evidence/docs. Independent roots can run concurrently only with one owner integrating shared test-manifest/doc edits.

## Evidence and requirement shape

Use synthetic documents, policies and parties with independent expected results. Do not pin shipped data, text, markup or counts. Appearance/wording judgments are human-reviewed against the approved detailed design, outside SHALL requirements. For each requirement implement a discoverable test named from its mechanism, covering every delta scenario and both raising/non-raising cases. Test paths are named in Context. New package-local server tests join exactly one shard in .github/evennia-shards.json; avoid new modules when an existing test file is sufficient.

Requirement IDs must come from tools.spec_traceability list on the equivalent merged spec tree, never hand-composed. Before sync associate only the nearest current canonical requirement and report the temporary mapping per docs/development/spec-test-traceability.md. Sync remounts to the generated IDs with no uncovered requirements or waiver. Modified requirements retain identity except an explicit RENAMED window title. Mechanism tests must exist before that sync.

## Risks / Trade-offs

[Read side effects] -> Pure projections and object/Attribute/clock snapshots in integration tests. [Shared files] -> Serialize shard-manifest, schema and documentation changes even when roots are independent. [Data echo tests] -> Assert mechanics on synthetic fixtures and treat visual review separately. No new permanent lighting or walking state is allowed.

## Rollout / Rollback

Apply only after dependencies land. Development database reset is needed for the schema2 cutover; never automate deleting the user's database. No migration or dual decoder is added. Rollback is source reversal and a deliberate development reset where applicable. This proposal task does not start apply, sync or archive.
