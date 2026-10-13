# Design

## Context

Source of truth: `docs/superpowers/specs/2026-10-10-scene-overview-redesign-design.md` §4, §5.4 (rail part), §7, §8 (rail and card part). The prototype `ScenePrototype.vue`, `ChoiceCardPrototype.vue`, and the `PersonFocus` story are the visual reference; the spec wins on behavior. `web/webclient-app/AGENTS.md` governs.

Observed today (after `exploration-exit-compass`):
- `DialogueChoices.vue` (about 700 lines) owns the card shell, row rendering, digits, the entrance stagger, and the dialogue view-model rows. `ChoiceCardRow.vue` is unrelated (the suggestion `OptionCard` row).
- A person chip is a router item with `openTarget`; activating it pushes the `exploration.target` frame (`verbMenuFor`), rendered by `DockVerbPopover` in the dock's `overlay` slot, with `dockSource === "exploration.target"`.
- The dialogue host stands in `actor-right` through `StageActor` keyed by `dialogueVM.host.identity` inside an `actor-enter` transition.
- `HudFrame.vue` exposes the anchors `actor-left`, `actor-right`, `vitals`, `map`, `choices`, `band-message`, `band-command`, `command-line`.

## Goals / Non-Goals

**Goals:**
- People and objects live on the stage; verbs live on a centred card; no payload changes.
- `ChoiceCard` is the only card shell, and the dialogue screen is pixel- and behavior-stable.

**Non-Goals:**
- Place-card buttons, wait and suggestions cards, the 建議 pill, final readout rules, `SceneOverview` removal: change 3.

## Decisions

### D1. Extract first, with the dialogue tests as the guard

`ChoiceCard.vue` receives rows as data (`{key, label, enabled, reason, trailing}`) and emits `pick(key)` and `back`; it owns the frame, crest, brackets, badges, rule, caret, keyboard composite, `aria-activedescendant`, focus trap hooks, and the entrance. `DialogueChoices` maps its picks, `⌨ 自由對話`, `↦ 移動…`, `✕ 結束對話`, and the exits view onto rows and keeps its emits. Order of work: extract, run `tests/dialogue_choices.test.js`, `tests/app_client_dialogue_choices.test.js`, and the dialogue stories unchanged, and only then add consumers. Any needed test edit is a sign the extraction changed behavior and is fixed in the component instead.

### D2. Person focus is a client-local ref, not a router frame

A small composable holds `focusedIdentity` and `openerKey`. The focused target is re-resolved from the committed exploration panel on every render, so a departed target closes the card in the same commit (spec §7 flash `<name> 已經離開了。`). The verb rows come from `ExplorationMenu.verbMenuFor(target)`, whose items and payloads stay unchanged. Picks go through the store method change 1 added for exits, generalized to take any builder row: it applies the same in-flight, revision, connection, and disabled gates as `focusConfirm`, and handles `navigate` rows (open the drawer) and `explore.wait`-style local opens exactly as the router path did. `openTarget` items, the `exploration.target` resolver, `dockSource === "exploration.target"`, the dock `overlay` slot use for the popover, and the focus-restoration watcher keyed on that source are deleted.

### D3. One standee element for focus and dialogue

The `actor-right` slot renders one `StageActor` whose subject is the dialogue host when `inDialogue && dialogueVM`, otherwise the person-focus target, keyed by identity. Because the key is identical on both sides of the 交談 commit, Vue keeps the element and the transition does not leave and re-enter. The message window shows the target's name as the speaker line while focused. `hostAlreadyInLineup` logic stays as is.

### D4. Placement

The rail mounts in a new `presence` anchor of `HudFrame` (stage floor, right-aligned, inset left of the island column, baseline just above the band). The verb card and overflow card mount in the existing `choices` anchor, which dialogue also uses; the two are never visible together. The place card and minimap step away through the same mode-dependent hiding the dialogue screen uses, keyed on a `personFocus` flag; the command panel gets `inert` and `opacity: 0.35`.

### D5. Digits and focus order

Tab order: compass → rail → dock footer. Digits 1–9 activate the Nth visible rail entry while no card is open and focus is not in the command line or a drawer; while a card is open the card owns them. The interim footer chips lose digit activation (they stay reachable by arrows, Tab, and pointer); this is accepted for one change and removed from the picture entirely in change 3.

### D6. Readout sources

`ExplorationReadout` gains the rail source (`<name>` over the affordance summary or `查看`). The priority helper from change 1 only gains an input; its ordering is unchanged.

### D7. Overflow

Six slots; with more than six entries, five show and the sixth is `＋N`. The overflow card lists the remaining entries (objects marked ◇) through `ChoiceCard`; a pick re-enters the same activation function the rail uses, so there is one activation path.

### D8. Styling

Grep `styles/app-shell.css` for `.elosern-root` duplicates of every restyled class (`.action-dock*`, `.scene-overview*`, dialogue choice classes touched by the extraction) and update them in the same commit.

## Implementation Notes

Recorded during apply; each refines a decision above without changing the delta specs.

- **D2, where the state lives.** The focus slice (`presenceCard`: the verb card `{identity, name, openerKey}` or the overflow card) is client-local state on the store, not refs inside the composable, because the store's digit path must open a card and must know whether one is open, and because a departed person or a committed move must close the card in the commit that publishes it. It is never a router frame and opening it sends nothing. `composables/use-person-focus.js` derives everything else (card rows, the standee subject, the speaker line, focus restoration, the departed flash, the Tab chain). The settle checks, in order: mode not exploration → close; committed location key (room identity plus current node) changed → close quietly; the exploration panel unavailable → keep; departed interact target → close with the `<name> 已經離開了。` notice, deferred while a submission is in flight or awaiting its revision (so 交談's intermediate commit never closes the card or flashes).
- **D2, settle details.** A move is a changed room identity, or two known current nodes that differ; a node that only appears or disappears in the same room (the local map turning unavailable or available) is not a move. The departure check waits while any submission is in flight or awaiting its revision (not only 交談's), and the publish that releases the lock settles it. A verb card stays open beneath the drawer its navigate row (交易, 公會服務) opened, and focus returns to it when the drawer closes.
- **D2, one gate.** `activateExplorationRow(row)` is the generalized gate (`activateExit` delegates to it); it gates every row, local drawer opens included, exactly as the router's `confirm` does.
- **D5, digits.** The rail claims digits 1–9 in every `exploration.*` dock frame (the root and its waiting and suggestions frames) while it is on the stage (`view.railVisible`: exploration mode, entries present, no card, no held combat round, no degraded root, no drawer or overlay); an empty or hidden rail claims none and the router digit path is not used there, so nothing falls through to the footer chips or the child frames' rows. While a card is open its own keydown takes the digits, and the store routes a digit that reaches it with focus elsewhere to the card's rows.
- **D5, digits under a drawer.** While a drawer or overlay is open the card's digits are unclaimed (the drawer owns its keys); an open card otherwise owns digits 1–9 whatever dock frame is beneath it. Card rows past the ninth carry a `·` badge and are reached by the arrows.
- **D3/D4, the rail under a card.** The rail stays mounted (hidden with `v-show` and `inert`) while a card is open, so closing the card returns focus to the opener entry in the same tick; a card reached through `＋N` returns focus to the `＋N` slot.
- **D5, Tab chain.** Compass → rail → footer is stitched with keydown handlers (the rail's anchor precedes the band in DOM order); a hidden rail leaves Tab native.
- **D6, readout order.** The rail joins the aimed-or-hovered tier above the compass aim (hovering or focusing the rail is the latest attention; focusing it blurs the compass): flash, rail, compass aim, idle.
- **Portraits.** The exploration panel's schema v3 publishes `portrait_ref: null` on every interact target and look entity, so in the live client every medallion shows its initial and the focus standee uses the dialogue silhouette treatment. The face-crop path is implemented and covered at the component level and in Storybook, and lights up without client change once the presenter publishes refs (out of scope: no server change).
- **Live-client check (7.2).** With agent-browser against an isolated exploration-fixture server at 1451×790 and 1920×1080: the rail (four medallions; seven entries folding into five and `＋2`) stands right-aligned above the band and clear of the island column (at 1920×1080 its right edge is 32px left of the column and its bottom 13px above the band); the guild clerk's verb card is centred over the stage above the band with the map column stepped away, the command panel inert and dimmed, the standee in `actor-right`, and the speaker line; Escape returns focus to the opener medallion (to `＋N` from the overflow card); 交談 keeps the same `StageActor` element across the dialogue commit. The dialogue choice card was captured before (pre-extraction `DialogueChoices.vue`) and after the extraction at both viewports: identical boxes and row offsets and a zero-pixel diff over the card region. Recorded deviations from `Design/SceneOverviewRedesign`: the verb card keeps the dialogue card's command-row face (sans, quieter) rather than the prototype's larger serif rows, so the two cards stay one shell; the medallions show initials live (schema v3 null refs, above); at the 交談 handover the standee's placeholder becomes the dialogue panel's catalog silhouette when that panel names a portrait (StageActor's own crossfade on the same element); the overflow card hides the rail and stops the compass but does not dim the command panel (only person focus does, per D4). Fixed during the check: the exploration speaker plate now shares the page column's geometry, and a medallion whose portrait fails to load falls back to the initial.

## Risks / Trade-offs

- **Extraction regressions in the dialogue screen.** Mitigation: D1 ordering and unchanged existing tests, plus a live dialogue screenshot compared before and after at both viewports.
- **Generalizing the store gate.** One shared gate is the point; a second gate would let rail picks bypass in-flight protection. A store test asserts suppression for every consumer.
- **Spec text spread.** `webclient-desktop-shell` and `webclient-pointer-activation` name the verb popover and the popover's inert overview; task 6.2 authors the MODIFIED deltas.
- **Standee handover timing.** The handover relies on stable keys across the mode commit. A Vitest mount test asserts the element is retained; the live client confirms there is no flicker.

## Open Questions

None blocking.
