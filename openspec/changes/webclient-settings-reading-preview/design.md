## Context

SettingsOverlay accepts fontScale/textSpeed/motionLevel and emits existing preference intents; report Settings bullets 1-2.

Architectural sources: `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md` (read-only browser, deterministic authority, offline operation) and `docs/superpowers/specs/2026-09-23-webclient-avg-stage-redesign-design.md` (desktop AVG stage). Current main specifications, not historical archives, define preserved contracts. The report's screenshots are review observations; no new live/browser verification is claimed by this proposal-only work.

## Goals / Non-Goals

**Goals:** Give reading preferences a safe live sample and consistent controls.

**Non-goals:** no game-rule change, new gameplay capability, generic UI framework, mobile design, image-service work, compatibility adapter or persisted-data migration. Keep this slice to the named owners and focused checks; do not fold other batch surfaces into it.

## Decisions

Style native checkbox controls as theme switches while retaining real input semantics, checked state, labels and Space activation; do not build a competing switch state store. Lay out settings cards on equal tracks, content-sized rather than forced equal blank height, and use at least the smallest text token for help copy.

Add a small fixed sample above reading controls, using the existing text-speed helper and prose scale. The sample is local, deterministic and isolated: it must not append to narrative history, dispatch a game action, change reader position or consume live response auto-advance. Scale/speed changes restart the sample once; instant shows it fully. Reduced/off suppress decorative motion but the configured reading-speed semantics remain the existing reading contract. Provide replay; prevent endless autoplay and clear timers on close. This is not a second complete MessageWindow mount with store side effects.

## Risks / Trade-offs

- Longer localized strings and raised type sizes can exceed fixed boxes. Use bounded internal scrolling and preserve keyboard focus/complete text; exercise 1280x720, 1440x900 and 1920x1080 instead of shrinking text until it disappears.
- Existing tests may encode retired CSS spelling or wording. Delete such incidental tests rather than re-pin them; keep behavioral invariants and update changed consumer contracts.
- Browser aesthetic acceptance is not proven by component tests or by this proposal. During application run the actual changed surface with deterministic fixtures and inspect it; do not claim screenshots or runtime coverage that were not exercised.
- New permanent tests are for uncertain transitions, error paths and consumer-visible boundaries only. Do not pre-invent traceability IDs. Discover canonical IDs with the project tool after main-spec sync during application and annotate only tests that establish the requirement.

## Delivery boundary

One engineer-day covers the named surface, focused regression work and visual smoke. The matrix explicitly assigns all report findings, including rejected suggested fixes. Keyboard and pointer behavior remain supported; no gamepad mapping is added because the current client has no gamepad contract. Reduced/off motion, truthful unavailable state and native browser zoom remain required.
