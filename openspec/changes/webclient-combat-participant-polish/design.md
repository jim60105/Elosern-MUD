## Context

ParticipantFrame hpCurrent() reads displayHp by portrait_ref; current contextual-hud requirements explicitly require visible session tokens and decorative foe gauges. Report combat participant and stage foe bullets.

Architectural sources: `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md` (read-only browser, deterministic authority, offline operation) and `docs/superpowers/specs/2026-09-23-webclient-avg-stage-redesign-design.md` (desktop AVG stage). Current main specifications, not historical archives, define preserved contracts. The report's screenshots are review observations; no new live/browser verification is claimed by this proposal-only work.

## Goals / Non-Goals

**Goals:** Make participant and foe identities legible while preserving canonical HP and round semantics.

**Non-goals:** no game-rule change, new gameplay capability, generic UI framework, mobile design, image-service work, compatibility adapter or persisted-data migration. Keep this slice to the named owners and focused checks; do not fold other batch surfaces into it.

## Decisions

ParticipantFrame already groups by server team and substitutes displayHp during playback. Preserve that rule and every participant, including those beyond the three standing foes. Replace microcopy inside thumbnails with one initial and an accessible truthful art state; keep a compact visible session token because typed targeting and the existing spec depend on it. The report's aria-only tokens are rejected.

Show the foe display name above each decorative HP gauge; acting/target focus gets a non-colour shape/rule keyed to existing beat/selection identities. It must never make stage actors selectable. Keep gauges decorative and numeric HP in the participant frame. Compact participant rows and reserve head clearance by moving the entire foe row left within its existing horizontal bounds, not chopping heads or violating depth ratios. If the six-row frame still intersects at 1280, bound its content with internal scrolling while keeping names and gauges clear; no stage scroll.

Replace the dashed combat status border with a solid subdued ribbon. Do not blindly add one to session.round: it is the canonical completed-round count. At zero show a localized preparation label rather than 'round 0'; positive values retain their actual count.

## Risks / Trade-offs

- Longer localized strings and raised type sizes can exceed fixed boxes. Use bounded internal scrolling and preserve keyboard focus/complete text; exercise 1280x720, 1440x900 and 1920x1080 instead of shrinking text until it disappears.
- Existing tests may encode retired CSS spelling or wording. Delete such incidental tests rather than re-pin them; keep behavioral invariants and update changed consumer contracts.
- Browser aesthetic acceptance is not proven by component tests or by this proposal. During application run the actual changed surface with deterministic fixtures and inspect it; do not claim screenshots or runtime coverage that were not exercised.
- New permanent tests are for uncertain transitions, error paths and consumer-visible boundaries only. Do not pre-invent traceability IDs. Discover canonical IDs with the project tool after main-spec sync during application and annotate only tests that establish the requirement.

## Delivery boundary

One engineer-day covers the named surface, focused regression work and visual smoke. The matrix explicitly assigns all report findings, including rejected suggested fixes. Keyboard and pointer behavior remain supported; no gamepad mapping is added because the current client has no gamepad contract. Reduced/off motion, truthful unavailable state and native browser zoom remain required.
