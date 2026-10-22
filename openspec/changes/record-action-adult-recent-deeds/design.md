# Design

## Context

ActionResult exposes a transient EventLog and notifications. SexualState stores lifetime counters and experience types. The existing nomination serializer reads entry templates but drops structured entry data such as sexual_transition, sexual_counter and sexual_resist.

## Goals / Non-Goals

Deliver the behavioral slice in proposal.md in one engineer-day. Preserve subsystem writers and consent. No source-history duplication, schema migrations, backfill, or compatibility paths.

## Decisions

Add the deterministic action-to-narrative adapter at final settlement, after all effects and title awards have committed inside the still-open source transaction. Include stable occurrence ID, tick, location, encounter context, durable actor/recipient identities and display snapshots, skill/act identity and actual effects. Use one action source association for its effects and milestones, so selection can combine them without double-counting the occurrence.

Read committed structured outcomes including sexual_transition, sexual_counter and sexual_resist. Detect newly acquired experience, actual unlock crossings and significant transitions by before/after comparisons within the authoritative settlement. Do not synthesize a new occurrence when reading a handler or importing pre-existing lifetime state. If a transition happens outside the general action resolver, its actual owner emits the same evidence contract in its transaction.

Keep facts detached and typed rather than copying unrestricted EventLog data. Mark visibility and field-level knowability for the later authorization adapter. Actor/recipient roles must survive including resistance semantics; arousal, climax or automatic compliance do not become willingness, affection or relationship claims. Party membership or proximity never establish participation. Preserve mechanics unchanged and create no ordinary skill-use immediate nomination hook.

## Risks / Trade-offs

Multiple entry kinds can represent one action. Use stable action provenance and transition discriminators; replay and milestone tests must prove one occurrence, no invented recency and retained distinct outcomes.

## Cutover Plan

Apply dependencies first. Replace affected callers and tests together, retain no obsolete aliases. Roll back by reverting this code change before later dependents are deployed; no persisted-data conversion is planned for this pre-release project.
