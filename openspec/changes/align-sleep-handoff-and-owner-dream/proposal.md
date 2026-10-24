# Proposal

## Why

Browser sleep currently asks about dreams before accepting sleep, then loses the request on narrative-only handoff; dream ownership uses the acting body and can belong to a possessed NPC. Control-view transitions must instead offer contextual selection and owner-only optional dreams while the owner still sleeps, with deterministic recovery when the player declines.

## What Changes

- Automatically open the existing contextual browser selection surface when the controlled body sleeps. Keep every companion visible with reserve/fatigue and availability reasons, lawful owner return, explicit possess semantics and final option `全員一起睡眠`.
- Route that final option to the prerequisite's explicit atomic party-sleep operation. Preserve zero-time choice/cancel and verified transfer compensation.
- **BREAKING**: replace positive-elapsed/recovery-before-dream ordering with accepted owner sleep plus released/no-companion-possession view. Explicit release to a still-sleeping owner asks about dreams even if companions remain awake.
- Revalidate authenticated owner/control/receipt at dream confirmation; NPC companions never own player dreams. Forced sleep requires opt-in and never auto-enters.
- Link all dream exits to the same accepted owner sleep receipt. Exchanges have no independent clock/resource effects.
- After dream decline/close with no possession and all operable bodies asleep, automatically continue to the owner's target, consuming intermediate companion wake boundaries without stopping. Preserve real interaction and combat/hostile safety boundaries.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `companion-possession-core`: automatic contextual complete companion list and return semantics.
- `companion-possession-transition`: release preserves sleep and drives the resulting control view.
- `dream-sleep-surface`: owner-bound pre-recovery prompt and single-receipt departure lifecycle.
- `time-skip-commands`: owner-targeted automatic continuation after dream refusal.
- `webclient-exploration-menu`: server-driven sleep/dream ordering and transport parity.

## Impact

Reuse possession verification, modal focus/stale-choice conventions and existing dream lifecycle/generation. Touch shared rules orchestration, dream_surface/server facade, text sleep/dream/release commands, browser stores/composables/presentation, focused integration/browser tests and command documentation. Explicitly amend the approved design's old positive-elapsed dream rule and first-awake/manual-wait policy during apply. No visual redesign, random encounters, live-save edits, migrations, compatibility paths or new dream-generation engine.

## Batch:

depends-on: fix-body-sleep-lifecycle
depends-on: block-travel-for-all-party-sleep

worker: gpt-luna
branch: feat/align-sleep-handoff-and-owner-dream
worktree: .worktrees/align-sleep-handoff-and-owner-dream

Bounded workday integration unit after the receipt and travel prerequisites land. Reuse existing modal, control writer and dream service; add orchestration and boundary journeys only. Conflicts with lifecycle on time_skip, commands/skip, exploration adapter, command docs, design and manifests; conflicts with travel on design/manifests/traceability only. Preserve unrelated `unify-map-glyphs-across-map-surfaces` and serialize shared manifest/traceability edits. Apply only after explicit user instruction; this proposal authorizes no runtime edits.
