## Context

Report live/14-flee.png is an observation accepted as ground truth. Current SceneBackdrop stageGradient and AppClient beatHold paths were read; live root-cause reproduction remains an implementation task.

Architectural sources: `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md` (read-only browser, deterministic authority, offline operation) and `docs/superpowers/specs/2026-09-23-webclient-avg-stage-redesign-design.md` (desktop AVG stage). Current main specifications, not historical archives, define preserved contracts. The report's screenshots are review observations; no new live/browser verification is claimed by this proposal-only work.

## Goals / Non-Goals

**Goals:** Consolidate truthful stage captions and keep combat decoration through terminal playback.

**Non-goals:** no game-rule change, new gameplay capability, generic UI framework, mobile design, image-service work, compatibility adapter or persisted-data migration. Keep this slice to the named owners and focused checks; do not fold other batch surfaces into it.

## Decisions

The report observes town decoration behind held foes on flee; it labels the cause a possible defect. Current source confirms SceneBackdrop selects gradients from its mode prop and the shell maintains beatHold separately. This supports a mode-decoration mismatch hypothesis, not a newly reproduced live failure and not proof of a stale actual scene asset. First application task reproduces the reported transition with deterministic terminal playback and records which layer changes.

Derive stageMode = beatHold ? combat : committedMode at the existing client composition boundary, and use it consistently for gradient, combat veil and degraded sample choice. The committed mode, art panel, place card, map, focus and actions remain canonical. Do NOT freeze a previous art image: a terminal event may legitimately move location. The hold retains only combat decoration while current/prior imagery follows existing truthful done/pending rules. Reset/skip/flush/reconnect clear hold via the existing queue lifecycle.

Replace repeated sample/placeholder status with one badge retaining both sample disclosure and authoritative availability state. Keep caption only with an actual/prior rendered image; omit repeated alt text but keep accessible image identity and any pending/stale notice. Make full-view an accessible icon control only for a rendered image. Reject hiding the whole caption until hover: truthful pending state and keyboard discoverability must not disappear. Only non-essential decorative caption emphasis may fade; required text/control stay visible and reachable.

Strengthen the existing combat veil modestly (outer alpha .72, subtle scene desaturation) and keep it token-driven. Full crossfades use the existing scene token, reduced is bounded fade and off commits immediately. No new animation lifecycle.

## Risks / Trade-offs

- Longer localized strings and raised type sizes can exceed fixed boxes. Use bounded internal scrolling and preserve keyboard focus/complete text; exercise 1280x720, 1440x900 and 1920x1080 instead of shrinking text until it disappears.
- Existing tests may encode retired CSS spelling or wording. Delete such incidental tests rather than re-pin them; keep behavioral invariants and update changed consumer contracts.
- Browser aesthetic acceptance is not proven by component tests or by this proposal. During application run the actual changed surface with deterministic fixtures and inspect it; do not claim screenshots or runtime coverage that were not exercised.
- New permanent tests are for uncertain transitions, error paths and consumer-visible boundaries only. Do not pre-invent traceability IDs. Discover canonical IDs with the project tool after main-spec sync during application and annotate only tests that establish the requirement.

## Delivery boundary

One engineer-day covers the named surface, focused regression work and visual smoke. The matrix explicitly assigns all report findings, including rejected suggested fixes. Keyboard and pointer behavior remain supported; no gamepad mapping is added because the current client has no gamepad contract. Reduced/off motion, truthful unavailable state and native browser zoom remain required.
