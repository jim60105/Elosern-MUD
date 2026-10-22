# Design

## Context

schedule_rest_boundary_nomination checks daily_reset events. register_nomination_triggers currently registers exam and quest observers. settle_fatigue_intervals already computes start/end SleepPosture and schedules observability after commit; write_fatigue_state also serves reconciliation, initialization and rollback contexts that must not manufacture awakening.

## Goals / Non-Goals

Deliver the behavioral slice in proposal.md in one engineer-day. Preserve subsystem writers and consent. No source-history duplication, schema migrations, backfill, or compatibility paths.

## Decisions

Observe true committed voluntary/forced sleep-to-awake transitions at authoritative settlement boundaries with stable transition occurrence identities. Avoid hooks on low-level state writes, projection reconciliation, initialization or temporary replay segments. Notify the composition-root service only after the outer transaction commits. Deduplicate replayed transitions by their occurrence identity independently of the in-flight slot, so a repeated notification after a finished attempt does not generate another attempt. No deferred wake queue is introduced; a committed wake while live combat remains active is ineligible.

Remove schedule_rest_boundary_nomination and every call, exam nomination observer/registration and obsolete rest-point documentation. Keep canonical midnight/day-reset behavior for other consumers and decline cooldown calculation. Keep logout and actual qualifying quest-completion notifications after commit, forwarding stable source identity and finalized award results. Neither arbitrary award/evidence events nor ordinary skill settlements register nomination triggers.

For any eligible source trigger, suppress immediately only when its authoritative automatic-award results include the nominated player. Do not inspect event type, display name, unrelated owned titles or a producer Boolean. Awards to others and already-owned titles on a new occurrence do not suppress. Several awards suppress once; original replayed award results remain authoritative. Later wake/logout can use that deed. Synthetic new event/title tests use an otherwise eligible immediate notification; they do not add a production trigger type.

Reserve one in-flight slot keyed by durable player identity before asynchronous work. An overlapping wake/logout joins no new call and replaces no request. Freeze T once on admission and use the same feed/citation set through completion. Release on success, query failure, disabled profile, empty feed, void output, transport error, cancellation and persistence failure. The rules writer rechecks pending-ballot/cooldown and existing fail-closed title suppression at result arrival, so late responses cannot replace ballots. Restart preserves stored ballots but neither resumes abandoned generation nor persists in-flight work.

Use world.observability and existing narrative boundary events. Workflow context carries player, trigger, frozen tick and bounded source counts; exceptions use exc=. Never log full private deed prose operationally. Post-commit read/generation failures cannot roll back completed gameplay. Existing consent, non-expiring ballots, decline-only cooldown and display availability remain unchanged.

## Risks / Trade-offs

Low-level fatigue writes include restoration and combat posture reconstruction. Emit at actual committed owner transitions only and test temporary transitions, rollback and combat suppression. Smoke tests must replace external model transport only, never settlement or persistence.

## Cutover Plan

Apply dependencies first. Replace affected callers and tests together, retain no obsolete aliases. Roll back by reverting this code change before later dependents are deployed; no persisted-data conversion is planned for this pre-release project.
