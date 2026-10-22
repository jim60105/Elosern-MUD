# Design

## Context

fulfill_record_for currently dispatches completion observers; settle_exam_outcome handles promotion atomically inside encounter settlement. Combat terminal outcomes distinguish hostile victory/defeat/fled from exam_passed/exam_failed. Narrative source IDs already support encounter occurrences.

## Goals / Non-Goals

Deliver the behavioral slice in proposal.md in one engineer-day. Preserve subsystem writers and consent. No source-history duplication, schema migrations, backfill, or compatibility paths.

## Decisions

Write required deterministic evidence inside the owner settlement, before optional observer dispatch. Observer isolation is unsuitable for required deed persistence because a swallowed write failure would commit gameplay without evidence. Reuse stable quest occurrence, exam_id and encounter session source identities. Include completed objective and actual outcome, attained rank on pass, terminal combat outcome with participants/opponents and encounter mode.

Reuse existing encounter source identity builders and record_narrative_event. Existing encounter_protection projections remain available to their other consumers; nomination adapters will never consume their classification. Summarize terminal encounters rather than emitting each hit as an encounter victory. Simulated examinations retain their nonlethal mode and cannot be represented as lethal wins.

Collect all source-associated award results from the prerequisite and write finalized events in the same outer transaction with snapshot restoration. Quest acceptance and partial progress do not create completion facts. This change creates evidence only; no new nomination registrations or source histories are introduced.

## Risks / Trade-offs

Completion callbacks may run before an outer transaction commits. Persist inside that transaction; nomination remains an after-commit concern of the final change.

## Cutover Plan

Apply dependencies first. Replace affected callers and tests together, retain no obsolete aliases. Roll back by reverting this code change before later dependents are deployed; no persisted-data conversion is planned for this pre-release project.
