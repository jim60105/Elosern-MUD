# Design: Party window shell and 成員 tab

## Context

See proposal.md. `AppClient.vue` mounts `PartyDrawer` for `store.view.hudDrawer === 'party'` and passes slots, affordances and the release affordance; the quest drawer remembers its tab per session (`quest-drawer-memory.js`); `NpcPersonaEditor` opens through `npc.persona.read`. The prototype `PartyWindowPrototype.vue` and `tabs/MemberTab.vue` define the approved layout.

## Goals / Non-Goals

**Goals:** the shell all tabs share; a complete 成員 tab; deletion of `PartyDrawer` in lockstep.

**Non-Goals:** other tabs' content (one change each), navigation and hotkeys (`webclient-main-navigation-hotkeys`), help text.

## Decisions

- **Mount** the window under the existing `party` drawer key so current openers keep working; the shell owns `activeTab` and a session memory module mirroring `quest-drawer-memory.js` (keyed by generation/epoch scope).
- **Selection** is server-truth: the rail's selected entry is `party.viewed_member_id`; a click dispatches `party.view_member {member_id, tab, item_key: null}` and the UI waits for the update (pending state on the entry, no optimistic switch). A changed `viewed_member_id` resets local item and quantity state.
- **Descriptors only**: every action button reads the `party_member` descriptors; 請其離隊 reuses the quest drawer's two-step confirmation pattern; 人物卡 opens `NpcPersonaEditor` with the descriptor params.
- **Empty slot** reads the `explore.party_invite` affordance already in the exploration panel; with none present it shows the committed unavailable text.
- **Unimplemented tabs** render their panel's committed unavailable reason or the existing panel data via a placeholder slot until their change lands; no rule prose.

## Risks / Trade-offs

- [Transitional tabs] → The batch is an unreleased cutover; acceptance happens in `party-management-acceptance`.

## Migration Plan

Pre-release clean cutover; revert the implementation commit.

## Verification and documentation ownership

Vitest: rail dispatch payloads, pending/adoption of server selection, fallback reset, possession-identical rendering, two-step leave with Escape cancel, persona edit submit, empty-slot descriptor, no rule prose (text snapshot); stories for companion, commander, knocked-out, empty slot at both sizes; deletion of `PartyDrawer` with manifest/story/tests; Storybook build and showcase coverage; a browser method (registered in `.github/browser-shards.json`) opening the window and switching members. `web/webclient-app/AGENTS.md` updated.
