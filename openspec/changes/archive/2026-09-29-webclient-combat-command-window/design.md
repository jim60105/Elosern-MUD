## Context

DockTabBar is combat-only, uses horizontal chrome and floating count; combat_menu.openSkillTargets returns focusKey:null. Main combat-menu and contextual-hud both pin horizontal root behavior. Report Combat bullets 1-4,6.

Architectural sources: `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md` (read-only browser, deterministic authority, offline operation) and `docs/superpowers/specs/2026-09-23-webclient-avg-stage-redesign-design.md` (desktop AVG stage). Current main specifications, not historical archives, define preserved contracts. The report's screenshots are review observations; no new live/browser verification is claimed by this proposal-only work.

## Goals / Non-Goals

**Goals:** Present the unchanged combat hierarchy as a vertical command window with truthful contextual detail.

**Non-goals:** no game-rule change, new gameplay capability, generic UI framework, mobile design, image-service work, compatibility adapter or persisted-data migration. Keep this slice to the named owners and focused checks; do not fold other batch surfaces into it.

## Decisions

Replace the combat-only DockTabBar with a vertical command renderer, deleting the obsolete component, story and manifest entry rather than retaining a tab alias. Root column count becomes one: Up/Down traverse and wrap, Left/Right are no-ops at root; Enter/Space/numeric activation and Escape retain existing meanings. Amend both contextual-hud and combat-menu contracts which currently mandate horizontal navigation. Do not use the report's illustrative root list as authority: keep current resolver items, order, disabled reasons, bag behavior and confirmed Forfeit route exactly as supplied. Recovery mode still exposes only its existing recovery root.

At root, show local explanatory copy for the highlighted command on the right; at category/group depth show that row's payload label and descriptor count, not the previously selected skill. At skill/scale/target depth use the current skill context only. Clear stale detail on frame changes. Skills count is neutral inline secondary text, never an alert bubble. At deeper levels replace the root list with the active frame, preserving one listbox and breadcrumb/back path, not two competing focus regions.

Apply min-height:0 through the complete flex/grid ancestry and reserve legend height. The focused row scrolls within its list, not the band. Do not impose seven 36px rows plus footer into 260px; scroll when necessary.

For basic attack SINGLE targeting only, choose the first enabled server-listed opposing candidate as initial focus. Preserve candidate order and explicit ally selection where legal; fallback to the first enabled candidate, then existing disabled explanatory focus if none enabled. Other skills keep existing focus behavior. Initial focus never selects or submits. Playback lock gets a labelled wait/skip cue and indeterminate tokenized line, never a fabricated percentage; existing lock and skip semantics remain authoritative.

## Risks / Trade-offs

- Longer localized strings and raised type sizes can exceed fixed boxes. Use bounded internal scrolling and preserve keyboard focus/complete text; exercise 1280x720, 1440x900 and 1920x1080 instead of shrinking text until it disappears.
- Existing tests may encode retired CSS spelling or wording. Delete such incidental tests rather than re-pin them; keep behavioral invariants and update changed consumer contracts.
- Browser aesthetic acceptance is not proven by component tests or by this proposal. During application run the actual changed surface with deterministic fixtures and inspect it; do not claim screenshots or runtime coverage that were not exercised.
- New permanent tests are for uncertain transitions, error paths and consumer-visible boundaries only. Do not pre-invent traceability IDs. Discover canonical IDs with the project tool after main-spec sync during application and annotate only tests that establish the requirement.

## Delivery boundary

One engineer-day covers the named surface, focused regression work and visual smoke. The matrix explicitly assigns all report findings, including rejected suggested fixes. Keyboard and pointer behavior remain supported; no gamepad mapping is added because the current client has no gamepad contract. Reduced/off motion, truthful unavailable state and native browser zoom remain required.
