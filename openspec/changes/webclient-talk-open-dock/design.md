## Context

See proposal.md (Why). The state below was checked in code, assuming C1 to C8c and C9a (`explore-talk-open-action`) are archived. C9 was split along the server/client seam: C9a owns the server action, the v3 wire contract with its client mirror, the echo resolver, and the `targetMenuFor` 交談 branch; this change owns the client dock cleanup that C9a leaves dead.

- **Exploration menu** (after C9a): `targetMenuFor` maps `explore.talk_open` to the `talk-open` row. `keywordMenuFor` (rows `kw-*`) and `scriptedAffordanceFor` are still exported, but nothing reaches them: the v3 panel carries no `keywords` and no `talk_scripted` affordance.
- **Store** (after C8b, C8c, C9a):
  - `frame-resolvers.js` still registers the `exploration.keywords` source, and `frames.js` still lists it for `gridCols = 1`.
  - `handleExplorationItem` in `interaction.js` still has an `openKeywords` branch (push `exploration.keywords`) and a `freeform` branch (set `ctx.freeformTarget`, bump `drawerRequest`). No row sets either flag any more.
  - The dialogue variant's free row uses `borrowDialogueCommand`, a separate entry that also sets `freeformTarget`. It is now the only borrower of the command line.
  - `settleFrameStack` resets to `EXPLORATION_ROOT_DESCRIPTOR` on a room change inside the `inStackMutation` window (C8b). Nothing resets the stack when the mode changes to `dialogue`, so the popover stays open after a successful `talk_open`.
  - `fillDisplayFor` in `combat.js` fills `npcLabel` for the talk family but not for `explore.talk_open`.
- **Dock panes** (`components/dock-panes.js` `classifyPane`, `components/DockMenu.vue`):
  - `nav` is returned for `kw-*` rows, rows that are all `explore.look`, or `target-*` navigation cells. After C8c and C9a nothing produces any of these: the overview and the popover render through `SceneOverview` and `DockVerbPopover`, and the keyword frame is unreachable.
  - `affordance` is returned for rows carrying `explore.engage`, `explore.party_invite`, or `explore.talk_freeform`. Its only producer was the exploration target frame, which C8b moved into `DockVerbPopover`. The suggestions frame's `action-*` cards classify as `cards` first, and combat frames match earlier kinds.
  - `DockMenu.vue` renders `nav` with `dock-menu__nav*` markup (a `minmax(0, max-content)` track via `sizeFn`) and `affordance` with `dock-menu__aff*` markup whose head reads the `targetName` prop. `AppClient.vue` passes `:target-name="store.view.combatMenu ? store.view.combatMenu.title : null"`, and `targetName` has no other reader.

## Goals / Non-Goals

**Goals:**
- When a conversation opens from any surface, the dock is at the overview in the same commit.
- The keyword frame, the popover freeform borrow, the `nav` pane, and the orphan `affordance` pane are deleted with their tests.
- The dock's specs say 交談 is one step and the dock offers no keyword list, no free-form row, and no affordance pane.

**Non-Goals:**
- The server action, the wire contract, and the 交談 branch (C9a).
- The dialogue stage layout, the dock collapse in dialogue mode, and paging the dialogue line (C10b, C10c).
- Changing how the combat panes size their columns.

## Decisions

### D1. The dock returns to the overview when a conversation opens
Without a new rule, the verb popover stays open after a successful `talk_open`: dialogue mode keeps the exploration form, and the target is still present. `settleFrameStack` records `ctx.lastMode`. When the committed mode changes from `exploration` to `dialogue` and `router.depth() > 1`, it resets to `EXPLORATION_ROOT_DESCRIPTOR` inside the `inStackMutation` window, reusing C8b's room-change reset path. The first settle and every other transition never reset.

The rule covers any opener: dock, typed `talk X kw`, or a suggestion card. It is the dock-side half of "交談 enters the dialogue immediately". C10b then collapses the command panel in dialogue mode.

### D2. Client deletions
- `exploration_menu.js`:
  - Delete `keywordMenuFor` and `scriptedAffordanceFor`, and both exports.
  - The header comment drops "scripted keyword buttons, free-form dialogue".
- `frame-resolvers.js`: delete `exploration.keywords`. It becomes an unregistered source, so a stray push pops, as in C8c D2.
- `interaction.js`: delete the `openKeywords` and `freeform` branches, and update the `borrowDialogueCommand` comment, which names the deleted 互動 → 自由對話 row.
- `dock-panes.js`: `classifyPane` loses the `nav` kind (the `kw-*`, all-look, and `target-*` clauses) and the `affordance` kind. The kind-list comment follows.
- `DockMenu.vue`: loses the nav template, `dock-menu__nav*` CSS, the `nav` `sizeFn` branch, and the `openKeywords` chevron clause; and the affordance template, `dock-menu__aff*` CSS, and the `targetName` prop. `AppClient.vue` drops the `:target-name` binding.
- `dialogue-view.js`: its comment stops citing `keywordMenuFor`.

*Why delete `affordance` here:* no change in the series owns it, it has had no producer since C8b, and C9a's panel removes `explore.talk_freeform` from every target, the last code its classifier test named that an exploration frame could still carry. A frame that once classified as `affordance` now falls through to `plain`, which renders the same rows with the shared row renderer.

### D3. The echo's central fill
C9a added the `talk <NPC>` resolver and the popover row carries `commandDisplay.npcLabel`. `fillDisplayFor` adds `explore.talk_open` to its `npcLabel` family, so any other surface that dispatches it without a descriptor (a test harness, a future keyboard shortcut) echoes the same line. The Vitest echo table gains the popover row activation and a central-fill row.

### D4. Spec strategy
- C8b's dock requirement has a scenario, "交談 keeps the scripted keyword frame", that became false with C9a, and a MODIFIED block cannot drop it. That requirement is REMOVED and ADDED ("The keyboard-first exploration dock roots at the scene overview and opens dialogue directly"), and every annotation C8b, C8c, and C9a anchored to it is re-anchored.
- The contextual-hud blocks are MODIFIED on C8c's text, with all scenario titles kept.
- The pointer-activation block is MODIFIED on C8c's text. Its form list loses "a navigation row" (the `nav` pane) and "an affordance row" (the `affordance` pane), so the list names only forms that a frame still produces.

## Risks / Trade-offs

- [A frame shape that used to classify as `nav` or `affordance` appears later] → It renders as `plain` through the shared row renderer, with the same rows, focus, and disabled contract. A later change that wants a dedicated form adds it with a producer.
- [Deleting the `nav` `sizeFn` branch leaves no pane on a content-sized track] → The fixed-column requirement's no-stretch rule (C8c's text, kept here) names combat panes, which have used `repeat(n, 1fr)` since before this series. That pre-existing gap is not widened by this change: the moved C9a journey asserts in-pane bounds and the fixed two-column mapping, which `1fr` satisfies. Whether combat panes should switch to `minmax(0, max-content)` is a visual decision left to the coordinator.
- [Browser journeys already rewritten by C8b, C6c, and C9a are edited again] → The edits only add the dock-at-overview assertions and remove nav-pane assertions. Section 6 of tasks.md lists the files from `git grep`.

## Migration Plan

None: the client is unreleased.

Archive order: **C8a → C8b (`webclient-scene-overview-swap`) → C8c (`webclient-retire-exploration-submenus`) → C9a (`explore-talk-open-action`) → C9b (this change) → C10a (`dialogue-panel-host-portrait`)**.
- The dock requirement this change removes and restates is C8b's.
- The contextual-hud and pointer-activation blocks are written on C8c's text.
- The code this change deletes becomes dead only after C9a's wire change, so this change must archive after C9a.
- C10b (`webclient-dialogue-stage-actors`) modifies this change's dock requirement.
