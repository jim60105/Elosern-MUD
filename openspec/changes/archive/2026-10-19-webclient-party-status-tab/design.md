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
- **Trait rows** are the four static traits (`atk_phys`, `agility`, `defense`, `magic_power`), a fail-closed allowlist as in the retired drawer and the prototype; the gauges render as gauges from the `party` row and `guild_merit` beside the gem. The hero's name and portrait come from the `party` row; the `character` payload is shown only while its `member_id` is the viewed member.
- **Signed values** on a trait row are the display difference of the two committed totals (effective − base) with a ▲/▼ glyph; layers keep their own kind-formatted amounts.
- **Routing**: `openHudDrawer("status")` aliases the retired drawer name the way `"inventory"` does — it records the 狀態 tab in the live window memory and opens `party`, so an already open window switches to 狀態. The 角色狀態 navigation row no longer sets the `character` sub-dock, because the party window is frameless and closing it would never clear the sub-dock (and opening a reference drawer switches no sub-dock).
- **Art column**: no remaining `HudDrawer` drawer has the current character as its subject, so the host's art wiring is removed; `HudDrawer` keeps its `art` slot for a future subject drawer.
- **Navigation `aria-current`** follows the live party window tab, so only the entry of the open tab (角色狀態 for 狀態, 背包 for 背包) is current.
- **Breakdown stories**: `party_inventory` v1 carries no trait layers, so the 16-layer, bias-bearing and adjustment properties belong to the `character` fixture behind the status tab stories; the bag tab keeps its equipment story's `item_holdings` adjustment strings.
- **Story seam**: `PartyWindow`'s optional `statusTrait` (→ `PartyStatusTab`'s `initialTrait`, the prototype's prop) selects a trait on open; no app opener passes it.

## Risks / Trade-offs

- [Openers relying on the drawer] → All openers are routed in the same change; Vitest covers them.

## Migration Plan

Pre-release clean cutover; revert the implementation commit.

## Verification and documentation ownership

Vitest: first-layered-trait selection, waterfall order and labels, signed buff/debuff text, no gem without rank, condition detail, disguise footer with true values, combat rendering, possession-identical rendering. Stories (trait breakdown, no guild) at both sizes; Storybook build and showcase coverage; `web/webclient-app/AGENTS.md`. `tools.contract_gate`.
