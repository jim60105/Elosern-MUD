# Webclient Design Direction

The webclient is being redesigned as an AVG (visual-novel) + RPG hybrid in which
artwork is a primary subject, not a MUD text column. Frame UI proposals and
changes accordingly, and ship them as OpenSpec changes (no standalone HTML
prototypes; the real app differs too much for a prototype to be useful).

- Target desktop 16:9 only.
- Layout: full-bleed stage on top; bottom band = message window (2/3 width) plus
  command panel (1/3 width, at the band's right end) outside combat. In combat
  the command menu is a narrow card at the stage's dead centre (the same
  `#action-dock` moved into the `choices` anchor, in the gap the formation
  keeps clear) and the message window spans the band. Keep the image area
  large; do not put a narrative column and minimap side by side eating ~60% of
  the width.
- The player's own generated portrait stands on stage at all times; NPCs and
  enemies stand opposite in dialogue and combat.
- In combat both sides stand in one shared-scale formation around a clear
  dead centre (`components/combat-formation.js`, applied by AppClient): the
  party may leave its single row, every foe that has not fled stands, and
  each figure but the controlled one carries a glance plate (`FigurePlate.vue`,
  the stage's `plates` layer). A knocked-out or defeated foe keeps its slot
  collapsed under a broken seal (`✕ 已擊破`) and a knocked-out ally kneels
  (`▼ 倒地`); both differ from the listener dim by shape and text
  (StageActor's `fallen`). The place card and the participant roster are not
  shown in combat; the controlled figure's values stay in the vitals dock.
- Combat targets are picked on the stage figures (the stage target step,
  `stores/elosern/stage_targets.js`, published as `view.stageTarget`): in the
  target frame of an enabled SINGLE, SELF or AREA skill — and, since
  webclient-party-items-tactics, of a SINGLE item or 挑釁 — the card collapses
  to a target prompt, every figure outside the focused position's lit set
  takes the dialogue listener dim, each candidate carries a gold arrow marker
  above its plate (`components/stage-targeting.js`) and a hit area over its
  figure. The arrow keys walk the positions in stage order (left to right on
  the formation); the digits still pick the frame's items in server order;
  Enter, Space and Escape, the item order and every payload are the card rows'.
  The step's subject is the opened skill, item or basic action (same
  `{key,label,enabled,targetSpec,targets}` shape), never a second model.
- The commanded member's own items and basic actions live in the card, never
  in the bag: 道具 opens that member's committed stock (`item-<key>` rows
  carrying quantity and effect summary, each with its own committed reason),
  one item opens its review/SINGLE-target frame, Defend/Dodge confirm their
  round choice and Taunt picks one server-listed enemy. Every row submits the
  closed wire union through the guarded `combat.command` envelope
  (`{kind:"item", payload:{item_key[, target_id]}}`,
  `{kind:"tactic", payload:{key[, target_id]}}` — the literal wire kind is
  `tactic`; the panel echoes admitted entries back as `tactical`). A hostile
  item on an ally asks through the same actor-bound cross-side question. In
  combat the bag's 使用 routes to that same flow (`store.useCombatItem`) and
  never dispatches the actorless `inventory.use`; inspection and the commander's
  equipment toggles stay free, and there is no companion equipment surface.
- A cast across sides asks first (`stores/elosern/cross_side.js`, held in
  the store as `crossSideConfirm`, published as `view.crossSideConfirm`): a
  target-step submission whose skill is `hostile` and reaches a `party`
  participant (the actor included), or `beneficial` and reaches a `foes`
  one, opens a caution `QuestionCard` (`確定要對{友方|自己|敵方|友方與敵方}使用〈…〉？`)
  below the collapsed prompt with focus on 否, instead of sending. The dock is
  inert beneath it, no dock key or stage pointer acts, the stage keeps the
  step's dim and markers; 是 sends the held payload once, 否 / ✕ / Escape
  return to the step, and a panel that drops the skill or a target, a
  playing round or a mode change cancels it. Only the static facts decide;
  never add client-side combat maths to it.
- Vitals (HP/MP/stamina) are hidden at full and auto-appear when damaged or under a
  condition; always shown in combat.
- Dialogue collapses the action dock, and pressing 交談 enters the dialogue screen
  immediately (the server has `greeting_for()` in `world/rules/dialogue.py` for a
  no-keyword opener).
- The command line is hidden by default and expands via `/` or an icon.
- The message window uses AVG click-to-advance paging with a typewriter effect,
  paged per action response and never breaking mid-sentence; the player may act
  while pages remain (leftover pages flush to the log).
- A motion layer covers scene/mode transitions, typewriter, and beat-by-beat combat
  choreography; structured combat beats in the server protocol are accepted.
- Minimap has no legend and a thin frame, the full map fits the view, the full log
  opens scrolled to the bottom, the dock has a fixed height, and redundant head
  cards, 美術展示, and quick-word chips are removed.

## Styling pitfall

`styles/app-shell.css` contains `.elosern-root …` rules that duplicate or override
component `<style>` blocks, and Storybook does not render under `.elosern-root`.
When restyling a component, grep app-shell.css for its class names and remove or
update the `.elosern-root` duplicates, and verify geometry with a live-client
browser test, not only Storybook.
