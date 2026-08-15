## 1. Data and pure queries

- [x] 1.1 Add `freeform_cast_scales` (five entries: 0.25/`1/4`, 0.5/`1/2`, 1.0/`1`, 2.0/`2`, 4.0/`4`)
      to `world/rules/rulebook/progression.yaml` and load-validate it in
      `world/rules/progression.py` (exact count and values, ascending, unique labels, exactly one
      `1.0`, finite and positive; named error otherwise). Expose the parsed table as a module
      constant.
- [x] 1.2 Add `scaled_mp_cost(base, scale)` and `scaled_magnitude(base, scale)` to
      `world/rules/progression.py`: `floor(base * scale + 0.5)`, with `scaled_mp_cost` clamped to a
      minimum of `1` (a scaled cost is never zero, so no scale can produce a free cast), raising
      `ValueError` on non-positive base or non-finite/non-positive scale. Unit tests for exact,
      half-away-from-zero, the never-below-one clamp (`scaled_mp_cost(1, 0.25) == 1`), and invalid
      inputs (annotate with `covers_requirement` for
      `freeform-casting::scaled-costs-and-magnitudes-use-deterministic-round-half-away-from-zero`).
- [x] 1.3 Add `is_freeform_eligible(skill)` to `world/skills/cost_tiers.py` (ACTIVE + element +
      positive int `mp` cost + every effect prefix in `{damage, heal, self_heal}`). Unit tests for
      eligible (`wind_blade`, `tornado_blade`, `sea_of_life`, `phoenix_eternal_flame`) and
      ineligible (`gale_step`, `haste_domain`, `scorching_wave`, `purify`, `basic_attack`,
      `flight`) skills.
- [x] 1.4 Add `freeform_scales_for(entity, element)` to `world/rules/progression.py`: validate
      element against `ELEMENT_REGISTRY` (ValueError), return the ascending scale set when
      `f"{element}_mastery"` is in `entity.skills.owned_keys()` (direct ownership only), else `()`.
      Tests cover a master, a non-master, a conferred-grant-only entity, and a fabricated unknown
      element.

## 2. Resolver integration

- [x] 2.1 Add `scale: float = 1.0` to the frozen `ActionRequest` and the
      `RejectReason.SCALED_CAST_FORBIDDEN` member in `world/rules/action.py`; confirm every
      existing construction site still works (default `1.0`).
- [x] 2.2 Extend the `EffectHandler` callable type and `_step5_effect_resolution` to pass
      `scale: float` as the last argument; update every registered handler in `world/rules/action.py`,
      `world/rules/combat.py`, and `world/rules/disengage.py` (magnitude handlers use it, others
      `del scale`), plus test registrations in `world/rules/tests/test_effect_handlers.py` and
      `world/rules/tests/test_disengage.py`. Run the existing action-pipeline suites before/after.
- [x] 2.3 Add the step-1 freeform gate in `world/rules/action.py` (next to the existing
      `can_cast_skill` check), with the fixed crash-safe check order: when `scale != 1.0`, reject
      `SCALED_CAST_FORBIDDEN` unless the scale is a member of the table, then
      `is_freeform_eligible(skill)`, then `freeform_scales_for(actor, skill.element.key)` non-empty
      (never dereference `skill.element` for an ineligible skill). Never fire for `scale == 1.0`.
      Resolver tests cover mastery/non-mastery, ineligible spell, non-member scale, element-scoped
      rejection (`light_arrow` by a `wind_mastery` holder), `concentration` (no crash), and
      `dual_blade_mastery` (SP-only).
- [x] 2.4 Change `_adjusted_costs` to `_adjusted_costs(actor, skill, scale=1.0)` in
      `world/rules/action.py`: bundle adjustments on the unscaled base, then replace the `mp`
      amount with `scaled_mp_cost(base, scale)` (other resource keys unscaled); pass `request.scale`
      from both step 2 (`_step2_resource_check`) and step 6 (`_step6_resource_deduction`).
- [x] 2.5 Apply `scaled_magnitude` in `world/rules/combat.py`: `_handle_damage` scales the final
      per-target amount and clamps at the unscaled `combat.yaml` damage floor; `_handle_heal` and
      `_handle_self_heal` scale the caster-derived magnitude. Add an explicit
      `phoenix_eternal_flame` at `scale == 2.0` test asserting damage, self-heal, MP deduction, and
      the heal cap together. Defeat/knockout/kill-XP/practice staging needs no change.
- [x] 2.6 Add `RejectReason.SCALED_CAST_FORBIDDEN` to `world/rules/player_messages.py` with a fixed
      Traditional Chinese message that does not teach the mechanic to non-masters.

## 3. Preview, facade, and adapter

- [x] 3.1 Thread `scale` through `world/rules/action_preview.py`: `preview_skill` and
      `revalidate_submission` accept `scale=1.0`, apply the same step-1 gate, and check resources
      against the scaled cost (reporting `INSUFFICIENT_RESOURCE` for an unaffordable scaled cast).
- [x] 3.2 Thread `scale` through `world/rules/combat_session.py::submit_player_action` (default
      `1.0`) into the preview, preflight, and the round's `ActionRequest`; rejection before
      initiative consumes no round or world time.
- [x] 3.3 Update `web/webclient/actions/combat_actions.py`: the `combat.cast` validator accepts an
      optional `scale` (exact numeric membership in the table, rejects booleans/non-members as
      `malformed_payload`, default `1.0`, allowed on every target form) and `_cast_adapter` threads
      it into `revalidate_submission` and `submit_player_action`. Add validator tests.

## 4. Combat panel and webclient dock

- [x] 4.1 Extend the skill descriptor build in `world/rules/combat_view.py`: include
      `freeform_scales` (ascending `{scale, label, mp_cost}` via `scaled_mp_cost`) only when the
      skill is eligible and the actor owns the element's mastery; omit otherwise. Extend the
      descriptor validator in `web/webclient/presentation/combat_panel.py` (exact fields, bounds,
      ascending order, mp_cost consistency).
- [x] 4.2 Extend `web/static/webclient/js/elosern/combat_menu.js`: for a skill carrying
      `freeform_scales`, insert a 威力-choice menu (ascending entries with label and scaled
      `mp_cost`, `1` preselected) between skill selection and the target flow; include the chosen
      `scale` in cast payloads for every target form; Escape pops back; panel-replacement rebuild
      preserves a still-valid choice and resets to `1` otherwise; skills without `freeform_scales`
      keep today's byte-identical flow and payloads. Add Node tests in
      `web/static/webclient/js/tests/`.
- [x] 4.3 Add one Playwright scenario to the combat browser suite: a `wind_mastery` fixture casts an
      eligible spell at scale `2` (payload carries `scale: 2.0`, scaled MP deducted in the status
      panel), and a non-master fixture's panel contains no scale selector and emits no `scale` field.

## 5. Text command and documentation

- [x] 5.1 Extend `commands/action.py::CmdCast` to parse an optional `@<scale>` token from the skill
      key (labels `1/4`, `1/2`, `1`, `2`, `4`, default `1`) and thread the scale into the
      combat-session facade and `settle_out_of_combat_cast`; a non-label token or a token the actor
      cannot use rejects with the `SCALED_CAST_FORBIDDEN` message before any MP change or clock
      advance. Add command tests for scaled combat, scaled out-of-combat, invalid token, missing
      mastery, and ineligible spell.
- [x] 5.2 Update `docs/game/command-reference.md` (cast entry syntax
      `cast <skill_key>[@<scale>][=<target_key>]` + description with the mastery requirement),
      `docs/game/commands.md` (cast row), and the curated manifest syntax in
      `tests/test_command_docs.py`; keep `tests/test_command_docs.py` green.

## 6. Traceability and verification

- [x] 6.1 Run `uv run --locked python -m tools.spec_traceability list` and copy the canonical
      requirement IDs verbatim into the new discoverable tests' `covers_requirement` decorators for
      every requirement in `freeform-casting`, `element-mastery` (the `freeform_scales_for`
      requirement), `action-resolution-pipeline` (the scale-modifier requirement),
      `webclient-action-dispatch`, `webclient-combat-menu`, and `game-command-docs` delta specs —
      never hand-derive IDs from titles; run
      `uv run --locked python -m tools.spec_traceability check` until clean.
- [x] 6.2 Run the affected test ownership domains: the Evennia suites for `world.rules`,
      `world.skills`, `commands`, and `web.webclient`, the Node test directory, and the focused
      browser file; then `uv run --locked python -m compileall -q world typeclasses commands server`
      and `git diff --check`.
