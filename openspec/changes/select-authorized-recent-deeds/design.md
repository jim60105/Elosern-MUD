# Design

## Context

NarrativeEvent stores source_id, content, participants, location, tick, visibility and salience. It also stores generated statements, so persistence alone does not establish nomination eligibility. The service currently receives empty event_logs from production triggers.

## Goals / Non-Goals

Deliver the behavioral slice in proposal.md in one engineer-day. Preserve subsystem writers and consent. No source-history duplication, schema migrations, backfill, or compatibility paths.

## Decisions

Add a detached recent-deed reader under world/narrative/ and leave scheduling/AI composition in server/. Query the sole durable narrative event store using player identity and a tick frozen at admitted request T. Derive two days from canonical clock configuration, currently 172800 game seconds. Never copy fatigue balance constants or dynamically resize the duration. The approved fatigue numbers justify 48 hours only.

Use a closed set of adapters for completed quests, passed exams, completed combat, settled skills, adult acts and transition milestones. Exclude model-authored statements, self-reports, narrator prose, routine movement/waiting/commerce/conversation and encounter_protection. Apply inclusive time limits, player personal involvement, existing visibility rules and field-level knowledge authorization before any counting or grouping. Participant membership alone grants no access to another participant's private state. Malformed eligible records are dropped individually with a diagnostic; unsupported/inaccessible records are omitted.

Group encounter action facts with their outcome, combine effects/milestones sharing an action source, then compress consecutive eligible actions only when action type, participant IDs/roles and encounter context match. Never merge encounters. Outside combat a field change ends repetition. Retain distinct results and milestones; count retained unique committed occurrences only. Each group has latest included tick and a stable source identity tie key, without a persisted aggregate ID.

Order latest tick descending then source identity ascending; select at most eight groups. Render one JSON envelope at at most 8000 Unicode code points, including all reference lists. Drop older complete groups until within budget. Omit a group that cannot fit alone, rather than truncating claims or results. Retain every source needed for every retained fact. No rendered group means an empty feed. Selection never consumes events, so later requests can reuse them within their windows.

## Risks / Trade-offs

Aggregation before authorization can leak counts or private milestones. Test mixed visibility and out-of-window repetitions before summaries and inspect complete JSON rather than string prefixes.

## Cutover Plan

Apply dependencies first. Replace affected callers and tests together, retain no obsolete aliases. Roll back by reverting this code change before later dependents are deployed; no persisted-data conversion is planned for this pre-release project.
