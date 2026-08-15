## Why

Owning an element's mastery skill (`<element>_mastery`) today only flips the cast gate: it unlocks every
spell of that element regardless of numeric magic level, but each cast still costs the spell's fixed MP
and produces its fixed magnitude. World lore describes a 主宰 as someone for whom magic is
「不拘泥於形式，能量隨意念而動，已然超脫術式框架」— energy flows with intent instead of following the
spell's fixed frame. Nothing in the game implements that: a master has no way to pour less energy into
a spell (a cheap finishing cast) or more (a burst cast). This change adds proportional ("freeform")
casting for mastery holders: a chosen magnitude scale multiplies both the MP cost and the
damage/heal magnitude of the element's scalable spells (1/2 MP → 1/2 damage, 2× MP → 2× damage).
How mastery skills are acquired is deliberately out of scope and reserved for a future change.

## What Changes

- Add `freeform_scales_for(entity, element) -> tuple[float, ...]` to `world/rules/progression.py`: a
  pure query returning the closed allowed-scale set when the entity directly owns
  `<element>_mastery` (same direct-ownership rule as `can_cast_spell_tier`), else an empty tuple.
  The allowed set is data in `world/rules/rulebook/progression.yaml`
  (`freeform_cast_scales`: `1/4`, `1/2`, `1`, `2`, `4`), each entry carrying a display label and a
  positive finite scale, validated at load (sorted, unique, exactly one `1.0`).
- Add `is_freeform_eligible(skill) -> bool` to `world/skills/cost_tiers.py`: an ACTIVE elemental
  spell with an `mp` cost whose every effect is magnitude-scalable (`damage`, `heal`, `self_heal`).
  Buff, status, cleanse, movement, and conferral effects make a spell unscalable — strict
  cost↔magnitude proportionality with no free rider.
- Add deterministic rounding helpers `scaled_mp_cost(base, scale) -> int` and
  `scaled_magnitude(base, scale) -> int` (round half away from zero) to `world/rules/progression.py`.
  The scaled MP cost is clamped to a minimum of `1`, so no scale combination can ever produce a
  free cast (e.g. a quarter-scale cast of even a hypothetical 1-MP spell still costs 1 MP).
  Scaled damage stays clamped at the existing `combat.yaml` damage floor (the floor itself is not
  scaled). Scaling applies to `mp` cost only; other resources are untouched.
- `ActionRequest` (world/rules/action.py) gains a `scale: float = 1.0` field. `scale == 1.0` is
  always a no-op and always allowed; any other scale requires (a) membership in the allowed set,
  (b) direct mastery ownership of the spell's element, and (c) an eligible spell — otherwise the
  cast rejects with a new `RejectReason.SCALED_CAST_FORBIDDEN` at the existing ownership step.
- The effect-handler signature gains a `scale: float` parameter (one call site,
  `_step5_effect_resolution`); `damage`, `heal`, and `self_heal` handlers multiply their computed
  magnitude by the scale; all other handlers accept and ignore it (they only ever run at `scale == 1`).
  Scaled MP deduction flows through the existing `_adjusted_costs` path, so step-2 preflight and
  step-6 deduction can never drift, and a scaled cast whose cost exceeds the current MP pool rejects
  with the ordinary `INSUFFICIENT_RESOURCE`.
- Preview and the webclient combat panel advertise freeform casting: each eligible skill descriptor
  gains `freeform_scales` (ascending `{scale, label, mp_cost}` entries computed server-side with the
  same rounding), and the combat menu inserts a scale-choice step before target selection for those
  skills. The `combat.cast` payload validator accepts an optional `scale` field (exact membership in
  the allowed set, default `1`), and the cast adapter threads it through `revalidate_submission` and
  `submit_player_action(actor, skill_key, targets, scale=1.0)`.
- The text `cast` command gains an optional scale token: `cast <skill_key>[@<scale>][=<target_key>]`
  (tokens are the yaml labels, e.g. `cast wind_blade@2=wolf`, `cast wind_blade@1/2=wolf`; skill keys
  are the registry keys and labels are never accepted as skill keys; default `1`), in and out of
  combat. Command docs (`docs/game/commands.md`, `docs/game/command-reference.md`) and
  the curated manifest in `tests/test_command_docs.py` update in the same change.
- `player_messages.py` gains a stable Traditional Chinese message for the new rejection reason.

## Capabilities

### New Capabilities

- `freeform-casting`: the closed allowed-scale contract, eligibility and rounding rules, mastery
  entitlement, resolver scale validation, scaled effect magnitude and MP deduction, preview support,
  and the text-command/webclient cast paths for proportional casting.

### Modified Capabilities

- `element-mastery`: mastery ownership additionally entitles freeform scaling of that element's
  eligible spells (new pure `freeform_scales_for` query).
- `action-resolution-pipeline`: `ActionRequest` gains the `scale` field, the effect-handler
  signature gains `scale`, and a new `RejectReason.SCALED_CAST_FORBIDDEN` member is added.
- `webclient-action-dispatch`: `combat.cast` payload gains the optional bounded `scale` field.
- `webclient-combat-menu`: the skill descriptor gains `freeform_scales` and the keyboard flow gains
  the scale-choice step.
- `game-command-docs`: the `cast` syntax changes to carry the optional `@<scale>` token.

## Impact

- `world/rules/progression.py` (three new pure functions), `world/skills/cost_tiers.py`
  (one new predicate), `world/rules/action.py` (`ActionRequest.scale`, step-1 scale validation,
  new `RejectReason`, handler call-site change), `world/rules/combat.py` (scale application in the
  three magnitude handlers), `world/rules/rulebook/progression.yaml` (scale table),
  `world/rules/action_preview.py` and `world/rules/combat_view.py` (preview + panel scale data),
  `world/rules/combat_session.py` (facade parameter), `world/rules/player_messages.py` (rejection
  text), `commands/action.py` (cast token parsing), `web/webclient/actions/combat_actions.py`
  (payload validator + adapter), `web/webclient/presentation/combat_panel.py` (descriptor
  validation), `web/static/webclient/js/elosern/combat_menu.js` (scale-choice step), docs and the
  command-docs manifest.
- Effect-handler signature change touches every registered handler (action.py, combat.py,
  disengage.py) and test registrations — mechanical, one call site.
- No data migration: the scale set is a load-time constant and `ActionRequest.scale` defaults to
  `1.0`, so every existing caller keeps its current behavior unchanged.
- Out of scope: mastery acquisition, AI/companion choice of scale (all deterministic AI paths submit
  `1.0`; the request interface already supports future use), scaling buff/status/DoT magnitudes,
  and scaling `sp`-cost or non-elemental skills.
