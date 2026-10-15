# Proposal: Confirm before a combat cast crosses sides

## Why

Friendly fire and helping a foe are allowed by design: the player may aim a hostile skill at an ally (or at
themselves), or a beneficial skill at a foe. Targets are now picked directly on the stage
(`webclient-combat-stage-target-picking`), so one stray arrow press or click can do either. The user asked for one
extra review step before such a cast is sent. It must not take the choice away and must not involve client-side
combat maths. The user also widened the trigger: debuffs, drains/gauge transfers, sexual effects and any declared
hostile effect on an ally count, and so do buffs and other beneficial effects on a foe.

## What Changes

- **Static trigger** from `webclient-combat-panel-v6`'s skill facts. A submission is cross-side when the skill is
  `hostile` and the target set holds a `party` participant (the actor included), or `beneficial` and it holds a
  `foes` participant.
- **Target sets:**
  - SINGLE → the focused candidate;
  - SELF → the actor;
  - AREA explicit → the selection;
  - AREA shorthand → that side's candidates (`all` → both);
  - NONE → empty.

  Any cross-side member asks once. A target identity that cannot be resolved fails closed.
- **Confirmation:** instead of dispatching, the existing `QuestionCard` opens, centred in the `choices` anchor, with
  one of:
  - `確定要對友方使用〈技能〉？`
  - `確定要對自己使用〈技能〉？` (only the actor is hit)
  - `確定要對敵方使用〈技能〉？`
  - `確定要對友方與敵方使用〈技能〉？`

  Focus starts on 否. 否, ✕ and Escape return to the target step unchanged; 是 sends the same payload through the
  same dispatch entry. The stage keeps the step's dim and markers; the collapsed card, the hit areas and the chips
  are inert. A panel replacement that invalidates the pending cast, playback, or a mode change cancels it. Focus
  returns to `#action-dock` on every close path.
- `QuestionCard` gains `initialFocus` (`"yes"` default, `"no"` here).
- Stories: ally-hostile, self-hostile, foe-beneficial (heal and buff), AoE mixed, both facts, and the no-confirm
  normal case on `Core/AppShell`, plus a `SafeDefault` story on `Core/QuestionCard`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-combat-menu`: adds "A cast across sides asks for confirmation first".

## Impact

- Client app (`web/webclient-app/`):
  - new pure module `stores/elosern/cross_side.js`;
  - `stores/elosern/frames.js`: submission interception for `target-*`, `self-confirm` and `area-confirm`;
  - `stores/elosern/view.js`: `view.crossSideConfirm`;
  - `stores/elosern/interaction.js`: no dock key while the question is open;
  - `stores/elosern/combat.js`: the pointer entry becomes a no-op while the question is open;
  - `AppClient.vue`: the `choices` slot;
  - `components/QuestionCard.vue`: `initialFocus`;
  - `components/ActionDock.vue`, `components/FoeLineup.vue` and `components/CompanionLineup.vue`: inert or no
    pointer while the question is open.
- No server, protocol or schema change (the facts arrive with `webclient-combat-panel-v6`).
- Tests: a new Vitest file, a QuestionCard Vitest file, one new browser method registered in
  `.github/browser-shards.json`.

## Batch: webclient combat stage

- depends-on: webclient-combat-panel-v6
- depends-on: webclient-combat-stage-target-picking
- Code conflicts: `AppClient.vue`, `components/ActionDock.vue`, `stores/elosern/interaction.js`, the line-ups and
  `stories/Core/AppShell.stories.js` with `webclient-combat-stage-target-picking`. It is the last change of the batch.
