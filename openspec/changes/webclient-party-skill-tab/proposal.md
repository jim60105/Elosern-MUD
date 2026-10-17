# Proposal: Party window 技能 tab

## Why

Design §6.4 of `docs/superpowers/specs/2026-10-18-party-member-management-ui-design.md`: the SkillBook content moves into the party window with proficiency meters, 新 tags, lineage position, the real freeform 威力與消耗 ladder (1/4, 1/2, 1, 2, 4 from `progression.yaml` `freeform_cast_scales`, shown only with the element's mastery), and 施放 / 排入修煉 for the viewed member, disabled in combat. It replaces `SkillBook`.

## What Changes

- New `PartySkillTab.vue` rendering `character` v9 rows for the viewed member (segment, search, category tree, detail card with ladder and lineage position), action bar 施放 (caster-explicit preview/cast from `companion-field-cast-actions`) and 排入修煉 (`explore.practice {actor_id, skill}`), both disabled in combat; opening the tab sends `party.view_member` with `tab: skills`.
- Lineage-position links switch to the 系譜 tab (rendered by `webclient-party-lineage-tab`; until then the link selects the tab only).
- **BREAKING (pre-release)** delete `SkillBook.vue`, its story `Data/SkillBook`, tests and `.elosern-root` duplicate rules; `SkillDetailPane` stays (dock-owned).
- Command docs' graphical-use paragraph points to 隊伍 → 技能.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-party-window`: adds the skill tab requirements.
- `webclient-skillbook-casting`: the two SkillBook requirements are renamed to the 技能 tab.
- `webclient-contextual-hud`: the reference-drawer skill-book scenarios name the 技能 tab.
- `webclient-component-showcase`: the status/skill surfaces requirement names `PartySkillTab`.
- `webclient-action-dispatch`: the registry scenario no longer names SkillBook.

## Impact

- `web/webclient-app/components/PartySkillTab.vue`, `PartyWindow.vue`, `AppClient.vue`, `composables/use-skill-use.js`, stories, manifest, Vitest, `docs/game/commands.md` paragraph, `web/webclient-app/AGENTS.md`; deletions above; one browser method.

## Effort

**7 hours total, strictly less than 8 hours**, including implementation, focused verification, documentation and integration.

## Batch: party member management

Declared implementation order: **26 of 30**.

- depends-on: webclient-party-status-tab
- depends-on: companion-field-cast-actions
- depends-on: party-practice-booking

### Code and spec conflicts within the new batch

- `webclient-party-status-tab`: shared showcase requirement "The status, character, and skill surfaces…" (S; that first) and `PartyWindow.vue`/`AppClient.vue`/manifest (F).
- `party-practice-booking`, `companion-field-cast-actions`: shared spec `webclient-skillbook-casting` and `webclient-contextual-hud` reference-drawer requirement, shared `SkillBook.vue` (S/F; those first; this delta preserves their edits).
- `party-item-transfer`, `party-panel-v3-view-member`: shared `webclient-action-dispatch` registry requirement (S; this delta keeps `party.transfer` and `party.view_member`).
- `webclient-party-lineage-tab`: lineage-position links target its tab (D).
- `.github/browser-shards.json`: conditional manifest conflict.

### Active change coordination

No active OpenSpec change.
