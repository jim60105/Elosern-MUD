# Proposal: Confirm before a combat cast crosses sides

## Why

Friendly fire and healing a foe are allowed by design: the player may aim a damaging skill at an ally or a healing
skill at a foe. With targets now picked directly on the stage (`webclient-combat-stage-target-picking`), one stray
arrow press or click can do either. The user asked for one extra review step before such a cast is sent, without
taking the choice away and without any client-side combat maths.

## What Changes

- **Server fact (read-only, smallest addition).** Each combat skill descriptor gains two required booleans,
  `harms` and `restores`: true when the skill's registry declares a damage effect (`harms`) or a heal/cleanse
  effect (`restores`) routed to the chosen targets (`EffectAudience.SELECTED`, the default). Derived statically from
  `SkillDef.parsed_effects` and `effect_policies`; no amounts, no formulas. Mirrored in the server serializer and
  validator and the client wire validator. Today the client receives no effect facts at all, so this is the minimum
  needed to avoid heuristics on labels or descriptions.
- **Static trigger.** A submission is cross-side when `harms` and the target set holds a `party` participant (the
  actor included), or `restores` and it holds a `foes` participant. Target set: SINGLE → the focused candidate;
  SELF → the actor; AREA explicit → the selection; AREA shorthand → that side's candidates (`all` → both); NONE → empty.
  Any cross-side member in a set asks once.
- **Confirmation.** Instead of dispatching, the client opens the existing `QuestionCard` centred in the `choices`
  anchor: `確定要對友方使用〈技能〉？`, `確定要對自己使用〈技能〉？` (only the actor), `確定要對敵方使用〈技能〉？`, or
  `確定要對友方與敵方使用〈技能〉？` (both facts hit). Focus starts on 否; 否, ✕ and Escape return to the target step
  unchanged; 是 sends the same payload through the same dispatch entry. The stage keeps the step's dim and markers;
  the collapsed card is inert beneath. A panel replacement, playback or a mode change cancels it.
- `QuestionCard` gains `initialFocus` (`"yes"` default, `"no"` here).
- Stories: ally-harm, self-harm, foe-heal, AoE mixed, both-facts, and the no-confirm normal case on `Core/AppShell`;
  a `SafeDefault` story on `Core/QuestionCard`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-combat-menu`: adds "A cast across sides asks for confirmation first"; amends "Combat presentation
  enumerates complete deterministic choices" (the descriptor's `harms` / `restores`).

## Impact

- Server: `world/rules/combat_view.py` (`SkillDescriptorView.harms` / `.restores`, derived in `_build_skills`),
  `web/webclient/presentation/combat_panel.py` (`_serialize_skill`, the skill validator's exact field set).
- Client wire: `web/static/webclient/js/elosern/protocol/panels/combat.js` (`validateSkill`).
- Client app (`web/webclient-app/`): new pure module `stores/elosern/cross_side.js`; `stores/elosern/frames.js`
  (submission interception for `target-*`, `self-confirm`, `area-confirm`); `stores/elosern/view.js`
  (`view.crossSideConfirm`); `stores/elosern/interaction.js` (no dock key while the question is open);
  `AppClient.vue` (`choices` slot); `components/QuestionCard.vue` (`initialFocus`); `components/ActionDock.vue`
  (inert while the question is open; chips take no pointer); `components/FoeLineup.vue` and
  `components/CompanionLineup.vue` (hit areas take no pointer while the question is open).
- Fixtures: every hand-written combat skill descriptor that passes a wire validator gains the two fields (server
  `_support.py` helpers, `web/static/webclient/js/tests/protocol_fixtures.js`, Storybook fixtures).
- Tests: Python presenter/view tests, the Node wire test, a new Vitest file, one new browser method registered in
  `.github/browser-shards.json`. No new Python test module.
- `context_actions` stays at schema version 5 (design D2). No telnet or player-command change.

## Batch: webclient combat card and stage targeting

- depends-on: webclient-combat-stage-target-picking
- Code conflicts: with `webclient-combat-stage-target-picking` — reads its `stores/elosern/stage_targets.js` and
  `view.stageTarget`, and edits the same `AppClient.vue`, `components/ActionDock.vue`, `stores/elosern/interaction.js`
  and `stories/Core/AppShell.stories.js`. With `webclient-combat-command-card-centred` — `stories/Core/AppShell.stories.js`
  only (transitively ordered). Apply after both are archived.
