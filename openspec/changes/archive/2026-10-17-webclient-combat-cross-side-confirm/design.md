# Design: Confirm before a combat cast crosses sides

See `proposal.md` and `specs/`. Builds on `webclient-combat-panel-v6` (the skill descriptor's `hostile`/`beneficial`
from the registry's per-effect-kind classification) and `webclient-combat-stage-target-picking` (the stage target
step, `stores/elosern/stage_targets.js`, `view.stageTarget`).

## Context

- `hostile` is true when any effect routed to the chosen targets is classified hostile (damage, drain, debuff,
  sexual stimulus …); `beneficial` when any is beneficial (heal, cleanse, buff, restore purity …). Both are static
  registry facts.
- Participants carry `team` `party` | `foes`; the actor is on `party`.
- `QuestionCard.vue` is the room cards' modal yes/no (role `dialog`, `aria-modal`, labelled by its question, traps
  focus, Escape → `close`, `locked` + `reason`) and currently focuses 是 first.
- Every target-step submission (Enter, digits, the stage pointer entry, the prompt chips) ends in `router.confirm` →
  `onRouterEvent("submit")` (`stores/elosern/frames.js`).

## Decisions

### D1. The predicate: `stores/elosern/cross_side.js`

Pure and DOM-free:

```js
crossSide({ hostile, beneficial }, targets /* [{ identity, team }] */, actorIdentity)
// → null | { sides: "ally" | "self" | "foe" | "both", question }
```

`ally` hit = `hostile && targets.some(t => t.team === "party")`; `foe` hit = `beneficial && targets.some(t => t.team ===
"foes")`; both hits → `both`; an ally hit whose party members are only the actor → `self`. The question is
`確定要對{友方|自己|敵方|友方與敵方}使用〈{skill.label}〉？`. The target set comes from the item being submitted
(D2) and the committed participants; shorthands expand to that side's candidates (`all` → every candidate).

### D2. Interception at submission, one dispatch afterwards

In `onRouterEvent("submit")`, before the existing `target-*`, `area-confirm` and `self-confirm` dispatches, the
store builds the payload exactly as now, computes the target set, reads `hostile`/`beneficial` from the committed panel's
descriptor for `combat.focusSkillKey`, and calls `crossSide`. On `null` it dispatches as today. Otherwise it stores
`ctx.crossSideConfirm = { actionId, payload, display, question, focusKey }` and publishes; nothing is sent.

- **是** → `confirmCrossSide()`: dispatch the stored `actionId`/`payload`/`display` through `dispatchAction`
  (the same in-flight lock and echo), then clear.
- **否 / ✕ / Escape** → `cancelCrossSide()`: clear, `router.focusItemByKey(focusKey)`, and request DOM focus on
  `#action-dock` (`dockFocusRequest`). The AREA selection lives in the model and is untouched.
- **Invalidation**: a committed `context_actions` replacement that removes or disables the pending skill or drops a
  pending target (or the shorthand) from its candidates, `beatLocked()` turning true, or a mode change clears
  `crossSideConfirm` without sending; an unrelated replacement (e.g. a resync with the same candidates) keeps it.
- **Unresolvable target**: an identity with no committed participant row counts as both sides (fail closed), so a
  harmful or restorative skill asks with the 友方與敵方 wording.
- **Pointer**: while `crossSideConfirm` is set, `stageTargetPointer` is a no-op and the line-ups' hit areas and the
  prompt chips get `pointer-events: none` (AppClient passes the flag), so no click or hover behind the modal moves the
  router focus or sends a cast.
- **Focus on close**: `confirmCrossSide` and every invalidation request DOM focus on the mode's focus home
  (`#action-dock` in combat) through `dockFocusRequest` / `restoreFocusHome`, so closing never leaves focus on body.
- **Keys**: while `crossSideConfirm` is set, `focusPress` claims nothing for the dock (returns `false` for arrows,
  digits, Enter, Space, Escape), so the router cannot re-submit; the QuestionCard handles its own keys.

### D3. Presentation

AppClient renders, in combat, `<QuestionCard v-if="store.view.crossSideConfirm" test-id="cross-side-question"
:question initial-focus="no" :locked="skipDisabled" reason="上一個行動尚未完成，請稍候。" @yes @no @close>` in the
`choices` slot after the teleported dock; the dock carries `inert` while it is shown and the question card stacks
above it (`z-index` within the anchor), centred in the anchor's span. `view.stageTarget` stays as it was, so the
stage's dim, lit set and markers do not change. `QuestionCard` gains `initialFocus: "yes" | "no"`; `focusFirst`
and the lock-release watcher use it.

Implementation notes:

- `skipDisabled` is true whenever the mode is not exploration, so it would lock 是 for the whole fight. The lock is
  the combat submission gate instead: not connected, an inactive phase, `mutationsLocked`, a mutation in flight or a
  declared revision not yet committed. `confirmCrossSide` re-checks it and keeps the card open when it refuses.
- The room cards' question disables both answers while locked. The spec here keeps 否 working, so `QuestionCard`
  also gains `noWhileLocked` (default false), plus a visual `tone="caution"` with a decorative `caption`.
- The card sits in the anchor's column below the collapsed prompt, so it never covers the prompt. It is centred on
  the stage and vertically centred in the span the prompt leaves free.
- The commit-time settle re-runs the predicate on the held payload: a replacement that ends the crossing closes the
  card, and a changed label or side rewords it.

### D4. Storybook

`Core/AppShell` (via `combatKeys`): `CrossSideAllyHarm` (Attack → companion → Enter), `CrossSideSelfHarm`,
`CrossSideFoeHeal`, `CrossSideAreaMixed` (harmful AREA with a foe and a companion selected), `CrossSideBothFacts`
(`all`), `CrossSideNoConfirm` (Attack on a foe; the story shows the echo, no card). `Core/QuestionCard`: `SafeDefault`.
Fixtures gain a healing SINGLE skill, a harmful SELF skill, a harmful AREA skill with `all` and a both-facts skill.


## Risks / Trade-offs

- [Enter reaching the router behind the dialog] → the `focusPress` guard (D2) plus a Vitest that Enter with the
  question open dispatches nothing.
- [A misclassified effect kind] → the classification lives in one reviewed table (`webclient-combat-panel-v6` D3);
  the client never second-guesses it.

## Migration Plan

Pre-release; rollback is reverting the change's commits.

## Open Questions

None. The user confirmed the four wordings (友方, 自己, 敵方, 友方與敵方).
