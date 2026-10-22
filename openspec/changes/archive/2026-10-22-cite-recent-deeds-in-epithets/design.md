# Design

## Context

The proposer currently requests five display/basis candidates, then filters to three. summarize_event_logs drops structured entry data. Display form is 2–8 CJK characters; wire display cap is 64 and basis cap is 80. The service strips candidates to display/basis before persist_nomination_ballot.

## Goals / Non-Goals

Deliver the behavioral slice in proposal.md in one engineer-day. Preserve subsystem writers and consent. No source-history duplication, schema migrations, backfill, or compatibility paths.

## Decisions

Replace NominationContext.event_logs and summarize_event_logs with detached authorized recent-deed data from the prerequisite. The composition root obtains that feed after admission; the generative module receives no live entity or unrestricted raw dictionary. Keep player name, full title and bounded declined/removed-name advisory preferences in the prompt. Fixed-title names and live owned-epithet displays stay deterministic collision inputs outside prompt text.

Render provenance, occurrence times, location, participant identities plus readable labels/roles, action and actual outcome. Prompt for exactly five candidates with display, basis and nonempty distinct source_ids. Bound source arrays by the count of supplied rendered source IDs. Citation validation uses that exact set, excluding dropped, inaccessible or oversized-group sources. Invalid, duplicate or empty citations eliminate that candidate. A citation array larger than the request-bound count is a response field-size violation and voids the round; malformed field types or closed-shape violations retain round-void behavior.

Keep existing display/basis limits and ordered display-form, fixed-name collision, live-collection collision and duplicate filters. Validate citation eligibility before ballot admission without allowing a citation-invalid candidate to reserve a duplicate display. Keep first three survivors; one or two are valid. The generation boundary consumes citation fields and returns only display/basis to the existing rules writer. Existing transcripts retain the request and response provenance; operational logs never duplicate private prose.

Prompt prohibitions cover fabricated outcomes, role reversals, consent/relationship inferences from numerical effects and invented public witnesses or recognition. Citation membership does not prove semantic faithfulness, and no second model review is added. Keep empty feed/profile-disabled checks before any model call. Query, transport and invalid-output failures create no ballot/cooldown and never roll back gameplay. Remove obsolete event-log input callers, serializer constants and tests in the same cutover.

## Risks / Trade-offs

JSON schema validation could accidentally turn membership errors into whole-round failures. Test schema-invalid responses separately from well-shaped candidates with empty, duplicate, unknown or non-rendered citations.

## Cutover Plan

Apply dependencies first. Replace affected callers and tests together, retain no obsolete aliases. Roll back by reverting this code change before later dependents are deployed; no persisted-data conversion is planned for this pre-release project.
