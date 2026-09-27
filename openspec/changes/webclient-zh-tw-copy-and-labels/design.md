## Context

condition_label currently interpolates modifier keys; controls-reference is English; SkillDetailPane renders targetSpec verbatim; gallery presenter makes UTC labels despite separate created_at; report raw-key/localization findings.

Architectural sources: `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md` (read-only browser, deterministic authority, offline operation) and `docs/superpowers/specs/2026-09-23-webclient-avg-stage-redesign-design.md` (desktop AVG stage). Current main specifications, not historical archives, define preserved contracts. The report's screenshots are review observations; no new live/browser verification is claimed by this proposal-only work.

## Goals / Non-Goals

**Goals:** Remove English/raw-key leaks from help, combat labels, conditions, codex and gallery copy.

**Non-goals:** no game-rule change, new gameplay capability, generic UI framework, mobile design, image-service work, compatibility adapter or persisted-data migration. Keep this slice to the named owners and focused checks; do not fold other batch surfaces into it.

## Decisions

Translate client-owned help labels/details and the help heading to Traditional Chinese while preserving literal command syntax and actual key bindings. Do not translate user-authored narrative or identifiers sent over the protocol. TargetSpec display uses a closed display dictionary for the validated enum; unknown values get a neutral unknown label, never guessed mechanics. Party guidance uses the established localized affinity term.

Keep conditionLabel as the single visible/accessible description helper. Localize known modifier keys with the existing stat vocabulary, preserve sign/unit/value and duration verbatim, and use a neutral localized modifier label for unknown keys without dropping their values. Chips show severity shape plus a bounded readable condition label (not arbitrary two-character abbreviations that can collide), duration as a small secondary badge, and retain the full condition text for assistive technology and overflow disclosure. Six-chip/overflow and severity visibility rules remain.

Codex race titles come from the server registry at the read-model serialization boundary; existing title strings change, no new schema field. Creation needs an actual schema label and is isolated in webclient-creation-display-labels.

Gallery already carries created_at separately but the server label repeats a UTC timestamp. Remove only the generated timestamp from generated card labels at presentation time; preserve status/reason text. Render local relative time from created_at in the client with an exact localized date/time available via tooltip/accessibility. Future timestamps use a localized future-relative form, invalid/out-of-calendar finite epochs use a neutral unavailable-date label and retain status. Refresh relative time at most once per minute while the gallery is open and tear it down on close; do not rename persistent records or parse labels to infer dates.

## Risks / Trade-offs

- Longer localized strings and raised type sizes can exceed fixed boxes. Use bounded internal scrolling and preserve keyboard focus/complete text; exercise 1280x720, 1440x900 and 1920x1080 instead of shrinking text until it disappears.
- Existing tests may encode retired CSS spelling or wording. Delete such incidental tests rather than re-pin them; keep behavioral invariants and update changed consumer contracts.
- Browser aesthetic acceptance is not proven by component tests or by this proposal. During application run the actual changed surface with deterministic fixtures and inspect it; do not claim screenshots or runtime coverage that were not exercised.
- New permanent tests are for uncertain transitions, error paths and consumer-visible boundaries only. Do not pre-invent traceability IDs. Discover canonical IDs with the project tool after main-spec sync during application and annotate only tests that establish the requirement.

## Delivery boundary

One engineer-day covers the named surface, focused regression work and visual smoke. The matrix explicitly assigns all report findings, including rejected suggested fixes. Keyboard and pointer behavior remain supported; no gamepad mapping is added because the current client has no gamepad contract. Reduced/off motion, truthful unavailable state and native browser zoom remain required.
