# Design: Confirm before a combat cast crosses sides

See `proposal.md` and `specs/`. Builds on `webclient-combat-stage-target-picking` (the stage target step, its pure
model `stores/elosern/stage_targets.js` and `view.stageTarget`).

## Context

- The combat skill descriptor (`web/webclient/presentation/combat_panel.py` `_serialize_skill`; client
  `protocol/panels/combat.js` `validateSkill`, exact fields) carries key, label, description, cost, `target_spec`,
  element, enabled, disabled reason, `targets`, `shorthands`, optional `freeform_scales` — **no effect facts**. The
  description is free prose and the element says nothing about direction, so the client cannot decide "harmful" or
  "restorative" without a new fact.
- The registry declares typed effects: `SkillDef.parsed_effects` (`DamageEffect`, `HealEffect`, `CleanseEffect`,
  `SelfHealEffect`, buffs, sexual effects, …) with a parallel `effect_policies`, each carrying an `audience`
  (`EffectAudience.SELECTED` default, `SELF`, `ALLIES`, `ENEMIES`; `world/skills/effects/policies.py`). Only a
  `SELECTED` effect lands on whoever the player picked; `ALLIES`/`ENEMIES` effects are already side-filtered by
  the resolver and `SELF` effects land on the actor regardless of the choice.
- Participants carry `team` `party` | `foes`; the actor is always on `party`.
- `QuestionCard.vue` is the room cards' modal yes/no (role `dialog`, `aria-modal`, labelled by its question, traps
  focus, Escape → `close`, `locked` + `reason`), currently focusing 是 first.
- Submission paths in the target step: `target-*` rows and `area-confirm` in `onRouterEvent` (`frames.js`), and
  `self-confirm` through the generic `item.actionId` branch; Enter, digits and the stage pointer entry all end in
  `router.confirm` → `onRouterEvent("submit")`.

## Decisions

### D1. Two booleans derived from declarations

`SkillDescriptorView` gains `harms: bool` and `restores: bool`, computed in `_build_skills` from the registry entry:

```python
selected = [eff for eff, pol in zip(skill.parsed_effects, skill.effect_policies)
            if pol.audience is EffectAudience.SELECTED]
harms = any(isinstance(e, DamageEffect) for e in selected)
restores = any(isinstance(e, (HealEffect, CleanseEffect)) for e in selected)
```

`_serialize_skill` emits both; the server validator and `validateSkill` require both as booleans. Not counted:
`SelfHealEffect`, `SELF`/`ALLIES`/`ENEMIES`-routed effects (the player's choice cannot redirect them), buffs/debuffs,
gauge transfers and sexual effects (their direction is not a plain harm/restore; see Open Questions). Rejected: a
client table keyed by skill key (drifts from the registry), parsing the description (heuristic), a single
`intent` enum (cannot express a skill that does both).

### D2. No schema version bump

The two fields are additive and required. The server presenter, the client validator and the bundle ship from one
commit in this pre-release repository, so no peer ever pairs an old validator with a new presenter; bumping
`context_actions` to 6 would rename requirement headers in three capabilities and rewrite every fixture's version for
no compatibility benefit. Accepted risk: a long-open tab running the old bundle rejects the new payload (its exact
validator sees unknown fields) until it reloads — a version bump would not help that tab either. Making the fields
optional like `freeform_scales` would degrade gracefully but reintroduce "no fact" as a silent no-confirm path, so
they stay required. Note that `world/rules/tests/test_combat_view.py` constructs `SkillDescriptorView` with keyword
arguments and must pass the new fields. If the user prefers a bump, it is a
mechanical follow-up.

### D3. The predicate: `stores/elosern/cross_side.js`

Pure and DOM-free:

```js
crossSide({ harms, restores }, targets /* [{ identity, team }] */, actorIdentity)
// → null | { sides: "ally" | "self" | "foe" | "both", question }
```

`ally` hit = `harms && targets.some(t => t.team === "party")`; `foe` hit = `restores && targets.some(t => t.team ===
"foes")`; both hits → `both`; an ally hit whose party members are only the actor → `self`. The question is
`確定要對{友方|自己|敵方|友方與敵方}使用〈{skill.label}〉？`. The target set comes from the item being submitted
(D4) and the committed participants; shorthands expand to that side's candidates (`all` → every candidate).

### D4. Interception at submission, one dispatch afterwards

In `onRouterEvent("submit")`, before the existing `target-*`, `area-confirm` and `self-confirm` dispatches, the
store builds the payload exactly as now, computes the target set, reads `harms`/`restores` from the committed panel's
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

### D5. Presentation

AppClient renders, in combat, `<QuestionCard v-if="store.view.crossSideConfirm" test-id="cross-side-question"
:question initial-focus="no" :locked="skipDisabled" reason="上一個行動尚未完成，請稍候。" @yes @no @close>` in the
`choices` slot after the teleported dock; the dock carries `inert` while it is shown and the question card stacks
above it (`z-index` within the anchor), centred in the anchor's span. `view.stageTarget` stays as it was, so the
stage's dim, lit set and markers do not change. `QuestionCard` gains `initialFocus: "yes" | "no"`; `focusFirst`
and the lock-release watcher use it.

### D6. Storybook

`Core/AppShell` (via `combatKeys`): `CrossSideAllyHarm` (Attack → companion → Enter), `CrossSideSelfHarm`,
`CrossSideFoeHeal`, `CrossSideAreaMixed` (harmful AREA with a foe and a companion selected), `CrossSideBothFacts`
(`all`), `CrossSideNoConfirm` (Attack on a foe; the story shows the echo, no card). `Core/QuestionCard`: `SafeDefault`.
Fixtures gain a healing SINGLE skill, a harmful SELF skill, a harmful AREA skill with `all` and a both-facts skill.

## Risks / Trade-offs

- [A new required field breaks hand-written fixtures] → tasks list the grep and the focused runs that surface them.
- [Skills whose harm is not a `DamageEffect` (debuffs, drains)] → never ask; recorded as an open question rather than
  guessed.
- [Enter reaching the router behind the dialog] → the `focusPress` guard (D4) plus a Vitest that Enter with the
  question open dispatches nothing.

## Migration Plan

Pre-release; no data migration. Rollback is reverting the change's commits.

## Open Questions

- The user specified two wordings (友方, 敵方); this change adds 自己 (only the actor is hit) and 友方與敵方 (a
  skill with both facts hitting both sides, or an unresolvable target). Confirm or reduce to the two.

- Should debuff-polarity buffs, gauge transfers or sexual effects aimed across sides also ask? This change counts only
  damage (harm) and heal/cleanse (restore).
- Should the two fields come with a `context_actions` schema bump to 6 (D2)?
