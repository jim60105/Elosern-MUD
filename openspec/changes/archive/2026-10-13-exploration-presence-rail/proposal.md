# Proposal

## Why

After the exit compass, the command panel still lists people and objects as chips and opens a verb popover inside a 484×220 panel. People are the second most frequent exploration decision and deserve the stage, where the player already looks at portraits. The approved scene overview redesign (`docs/superpowers/specs/2026-10-10-scene-overview-redesign-design.md`, §4 and §10; visual reference `docs/design/scene-overview-redesign/`) moves them to a presence rail on the stage floor and verbs to a centred card. This is change 2 of 3.

## What Changes

- Extract `ChoiceCard.vue` (card shell, digit-badged rows, trailing rule, keyboard composite, staggered entrance) from `DialogueChoices.vue`, and render `DialogueChoices` through it with no visual or behavioral change.
- New `PresenceRail.vue` on the stage floor: gold medallions for interact targets (face crop or initial), dashed muted medallions for bystanders, a separator, steel lozenges for objects, name plates, a six-entry limit with `＋N` overflow, hover and focus readout feed, one keyboard composite, and digit picks.
- Client-local person focus: opening a target slides its standee into `actor-right`, dims and inerts the command panel, steps the place card and minimap away, and opens a centred verb card (`verbMenuFor` rows plus `✕ 返回`). Picks submit the payloads the popover rows submitted; 交談 hands the standee to the dialogue screen without a break.
- Remove the 人物 and 物件 rows from the overview, `DockVerbPopover.vue` with its story and tests, the `exploration.target` router frame, and the `openTarget` item kind.
- The overflow card lists the rest of the rail through `ChoiceCard`.
- **BREAKING** (UI contract): the verb popover and the 人物 / 物件 chips no longer exist; tests and browser helpers that open a popover use the rail and the verb card.

## Capabilities

### New Capabilities

- `webclient-presence-rail`: the rail, the person focus, the verb card, the overflow card, `ChoiceCard`, the dialogue-unchanged guarantee, and the interim exploration root (compass, rail, footer overview).

### Modified Capabilities

- `webclient-exploration-menu`: removes the root requirement, which `webclient-presence-rail` restates without the people, object, and popover scenarios.

## Impact

New `web/webclient-app/components/ChoiceCard.vue`, `PresenceRail.vue`, and a small person-focus composable; edited `DialogueChoices.vue`, `AppClient.vue`, `components/HudFrame.vue` (a `presence` anchor), `ActionDock.vue`, `SceneOverview.vue` (people and objects rows removed), `composables/use-dock.js`, `stores/frame-resolvers.js` (the `exploration.target` source), `web/static/webclient/js/elosern/exploration_menu.js` (`overviewMenu` drops people and objects, `openTarget`), `lib/controls-reference.js`, `styles/app-shell.css`, `component-manifest.json`; removed `DockVerbPopover.vue`, `stories/Action/DockVerbPopover.stories.js`, `tests/action/dock_verb_popover.test.js`; Vitest `app_client_scene_overview.test.js`, `app_client_dialogue_choices.test.js`, `dialogue_choices.test.js`, `store/store_dispatch_focus.test.js`; stories `ChoiceCard`, `PresenceRail`, and a full-screen story; browser tests under `web/tests/browser/` that open a person's verbs.

## Non-goals

No server or protocol change, no new action identifier, no change to the dialogue screen's `↦ 移動…` list or to combat, and no place-card buttons, wait or suggestions cards, or 建議 pill (change 3).

## Batch:

```text
depends-on: exploration-exit-compass
code-conflicts: exploration-room-actions (ActionDock.vue, AppClient.vue, SceneOverview.vue, exploration_menu.js, use-dock.js, controls-reference.js, component-manifest.json); exploration-exit-compass (same pane, resolved by ordering)
```

Batch 2, after `exploration-exit-compass` is archived. `exploration-room-actions` must wait for this change. Archive strictly in order: `exploration-exit-compass` → `exploration-presence-rail` → `exploration-room-actions`. This change's delta REMOVES a requirement that `exploration-exit-compass` MODIFIES, so archiving out of order fails `openspec archive`.

## Worker profile

**Visual.** Assign a worker that can read screenshots and drive `agent-browser`: medallion and lozenge styling, the standee slide, the dimmed panel, and the dialogue handover are judged against `Design/SceneOverviewRedesign` in Storybook and in the live client at 1451×790 and 1920×1080.

## Size and standalone delivery

About 8 hours: ChoiceCard extraction with the dialogue guard (2h), PresenceRail and stories (2h), person focus, standee handover, and card wiring (2.5h), removals and test migration (1h), live-client verification (0.5h). The client works fully on its own afterwards: people and objects through the rail, exits through the compass, room actions through the footer chips.
