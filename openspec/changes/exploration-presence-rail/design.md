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

## Risks / Trade-offs

- **Extraction regressions in the dialogue screen.** Mitigation: D1 ordering and unchanged existing tests, plus a live dialogue screenshot compared before and after at both viewports.
- **Generalizing the store gate.** One shared gate is the point; a second gate would let rail picks bypass in-flight protection. A store test asserts suppression for every consumer.
- **Spec text spread.** `webclient-desktop-shell` and `webclient-pointer-activation` name the verb popover and the popover's inert overview; task 6.2 authors the MODIFIED deltas.
- **Standee handover timing.** The handover relies on stable keys across the mode commit. A Vitest mount test asserts the element is retained; the live client confirms there is no flicker.

## Open Questions

None blocking.
