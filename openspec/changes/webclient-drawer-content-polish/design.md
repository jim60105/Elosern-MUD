## Context

Lineage schema exposes nodes[0].display_name_zh; current bag contract already supplies icons and rarity. Report Drawers bullets 4-6,8-9 except full log; empty state and art-layout observations are accepted, suggested fabricated art is not.

Architectural sources: `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md` (read-only browser, deterministic authority, offline operation) and `docs/superpowers/specs/2026-09-23-webclient-avg-stage-redesign-design.md` (desktop AVG stage). Current main specifications, not historical archives, define preserved contracts. The report's screenshots are review observations; no new live/browser verification is claimed by this proposal-only work.

## Goals / Non-Goals

**Goals:** Normalize drawer content hierarchy, honest art placement and empty states.

**Non-goals:** no game-rule change, new gameplay capability, generic UI framework, mobile design, image-service work, compatibility adapter or persisted-data migration. Keep this slice to the named owners and focused checks; do not fold other batch surfaces into it.

## Decisions

Use a left art slot only for character-related status, inventory and party workspaces where that subject is known; remove the player's portrait from codex and quest surfaces instead of inventing chapter artwork. Keep one truthful art state label per slot and never claim pending without a pending payload. Bound the art column to min(360px, 28% of workspace width); content gets min-width:0 and owns scrolling.

Status hero names the committed character, title and guild rank when supplied; absent data is omitted. Place existing skill and party openers in one wrapping secondary-action row and use content-sized, equal-track stat cards rather than filling with blank space. Preserve persona editing and true/disguised stat labels.

Introduce a presentational EmptyState with decorative line glyph, short headline and actionable guidance in a solid ink frame. Apply to empty available quest, codex, inventory and party lists, but never replace an unavailable reason or add a fabricated action. Keep empty and unavailable behavior distinguishable.

Compact collapsed lineage rows around 56px, with progress immediately adjacent to the name (max 320px), and append the first node's supplied display_name_zh as the disambiguating subtitle for equal element/style names. No lineage-key prose or new server field. Audit inventory presentation rather than rebuilding it: the current main spec already requires per-item icons and non-colour rarity. Reuse committed rarity metadata for a restrained frame; unknown items remain neutral. Migrate touched drawer text/radius declarations to shared tokens; no catalog-wide new artwork.

## Risks / Trade-offs

- Longer localized strings and raised type sizes can exceed fixed boxes. Use bounded internal scrolling and preserve keyboard focus/complete text; exercise 1280x720, 1440x900 and 1920x1080 instead of shrinking text until it disappears.
- Existing tests may encode retired CSS spelling or wording. Delete such incidental tests rather than re-pin them; keep behavioral invariants and update changed consumer contracts.
- Browser aesthetic acceptance is not proven by component tests or by this proposal. During application run the actual changed surface with deterministic fixtures and inspect it; do not claim screenshots or runtime coverage that were not exercised.
- New permanent tests are for uncertain transitions, error paths and consumer-visible boundaries only. Do not pre-invent traceability IDs. Discover canonical IDs with the project tool after main-spec sync during application and annotate only tests that establish the requirement.

## Delivery boundary

One engineer-day covers the named surface, focused regression work and visual smoke. The matrix explicitly assigns all report findings, including rejected suggested fixes. Keyboard and pointer behavior remain supported; no gamepad mapping is added because the current client has no gamepad contract. Reduced/off motion, truthful unavailable state and native browser zoom remain required.
