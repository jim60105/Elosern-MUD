# Design

## Context

The action title planner stages PendingEffect grants. Guild registration and examination promotion call grant_rank_title; first reward claims call grant_first_quest_epithet. NarrativeEvent is immutable and source-keyed. Existing title snapshots cover the collection and equip record.

## Goals / Non-Goals

Deliver the behavioral slice in proposal.md in one engineer-day. Preserve subsystem writers and consent. No source-history duplication, schema migrations, backfill, or compatibility paths.

## Decisions

Use a single automatic-award entry point in world/rules/titles/ accepting stable source occurrence identity, recipient identity and title identity. Return only actually newly granted titles, with a kind-qualified identity covering the authored starter epithet as well as fixed registry keys; accepting a generated epithet never enters this path. Keep low-level bank mutation behind the existing deterministic writer discipline.

Settlement accumulates all grants for its source, forwards the authoritative collection to narrative persistence and finalizes it once, after title effects and before the immutable record write. Stable identities belong to the owning settlement, including registration, first reward claim, examination and action effects; display names and notification strings are not identities. Uncovered occurrences may retain source-linked award evidence without becoming eligible deeds.

Replay first resolves an existing committed source and returns its original award results. A different new source that finds an already-owned title has no new grant. Do not overwrite committed source results with the empty result of replayed bank calls. Use the existing source uniqueness and transaction boundary, including cached attribute restoration. Do not add a separate suppression Boolean or event-type list.

Migrate every automatic caller in the same change, including predicate-planned combat, exploration/skill, sexual-experience/counter and clergy grants, registration, promotion and the authored first-claim epithet. Existing title conditions, notification delivery and auto-equip remain unchanged. This contract does not expand deed or trigger eligibility.

## Risks / Trade-offs

Ordering title effects after event persistence would lose suppression. Tests must inject failures after both sets of writes and assert durable rows and cached attributes restore together.

## Cutover Plan

Apply dependencies first. Replace affected callers and tests together, retain no obsolete aliases. Roll back by reverting this code change before later dependents are deployed; no persisted-data conversion is planned for this pre-release project.
