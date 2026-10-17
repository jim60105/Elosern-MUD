# Design: Party window 狀態 tab

## Context

See proposal.md. `CharacterStatusDrawer.vue` renders `status` resources, the condition roster, traits, guild and (since change 15) persona/intimate from `party_member`. The prototype `tabs/StatusTab.vue` defines the hero row, waterfall and disguise footer.

## Goals / Non-Goals

**Goals:** a complete status tab for any member in both modes; deletion of the drawer.

**Non-Goals:** the HUD vitals dock (still `status` v3 for the stage figure), persona (member tab).

## Decisions

- **Gauges** for the viewed member come from the `party` v3 row (HP/MP/SP), not `status`, so a companion's gauges are shown.
- **Waterfall** renders `traits[].layers` in payload order with source text labels and ▲/▼ shapes; colour is never the only signal.
- **Selection** of a trait or condition is client-local; the first trait with layers is selected on open; a viewed-member change resets it.
- **Title** uses `full_title` when present, else nothing (no invented title).

## Risks / Trade-offs

- [Openers relying on the drawer] → All openers are routed in the same change; Vitest covers them.

## Migration Plan

Pre-release clean cutover; revert the implementation commit.

## Verification and documentation ownership

Vitest: first-layered-trait selection, waterfall order and labels, signed buff/debuff text, no gem without rank, condition detail, disguise footer with true values, combat rendering, possession-identical rendering. Stories (trait breakdown, no guild) at both sizes; Storybook build and showcase coverage; `web/webclient-app/AGENTS.md`. `tools.contract_gate`.
