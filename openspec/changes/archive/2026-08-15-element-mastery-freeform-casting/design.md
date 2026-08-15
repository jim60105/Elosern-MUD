## Context

Element mastery (`<element>_mastery`, all eight elements registered) currently does one thing: it
overrides the numeric-magic-level cast gate in `world/rules/progression.py::can_cast_spell_tier`, so
a direct owner can cast every spell of that element (checked via `owned_keys()`, never conferred
grants). The five-tier spell catalog (`world/skills/registry.py`) carries 80 elemental spells with
fixed §4.3 MP costs, and `ActionResolver` (`world/rules/action.py`) resolves every cast through one
eight-step pipeline: ownership → resources → targets → capability → effects → deduction →
event-log → time cost, committed atomically. Damage (`damage:<element>:<school>`), heal
(`heal:single|area`), and self-heal (`self_heal`) magnitudes are computed inside the handlers in
`world/rules/combat.py` at staging time (the damage handler rolls the d100 hit itself), so any
magnitude scaling must happen inside those handlers, not after the fact. Resource availability is
checked against `_adjusted_costs()` in both step 2 (preflight) and step 6 (deduction), sharing one
bundle-adjusted cost read.

World lore (`tmp/story_settings/`, gitignored) describes a 主宰 as transcending the spell frame —
「不拘泥於形式，能量隨意念而動」 — and the player request is concrete: a 風之主宰 holder may cast
wind spells at a chosen proportion, e.g. 1/2 MP for 1/2 wind-blade damage, or 2× MP for 2× damage.

The webclient combat flow is exact-schema: `combat.cast` payloads are validated in
`web/webclient/actions/combat_actions.py`, skills are presented by `combat_view.py` from the shared
side-effect-free preview (`action_preview.py`), the keyboard dock lives in
`web/static/webclient/js/elosern/combat_menu.js`, and the panel descriptor schema is validated in
`web/webclient/presentation/combat_panel.py`. The text `cast` command (`commands/action.py`) parses
`<skill_key>[=<target_key>]` and routes through `settle_out_of_combat_cast` or the combat-session
facade `submit_player_action(actor, skill_key, targets)`.

## Goals / Non-Goals

**Goals:**
- A mastery holder can cast the element's scalable spells at any scale from a small closed set,
  with MP cost and damage/heal magnitude scaled by the same factor (strictly proportional).
- Scaling is deterministic, atomic with the cast, and works identically in and out of combat
  (including simulated guild-exam battles).
- `scale == 1` changes nothing and is always allowed — every existing caller keeps current behavior.
- The UI (text command and webclient dock) exposes the choice without duplicating rounding logic.

**Non-Goals:**
- No mastery acquisition mechanism (future change).
- No AI/companion scale selection: `monster_behaviour` and every deterministic policy submit `1.0`.
  The request interface supports a future AI consumer; nothing more is built here.
- No scaling of buff/status/DoT magnitudes, durations, or rates; spells carrying such effects are
  simply not scalable (mixed-effect spells like `scorching_wave`, `paralyzing_bolt`,
  `absolute_zero` reject any `scale != 1`).
- No scaling of `sp`-cost or non-elemental skills, and no scaling of non-`mp` resource components.
- No change to the EventLog schema: scaled amounts naturally appear in the existing
  `resource_spend`/`damage`/`heal` entries.

## Decisions

- **A closed, data-driven scale set instead of an arbitrary continuous factor.** `progression.yaml`
  gains `freeform_cast_scales`: `[{1/4, "1/4"}, {1/2, "1/2"}, {1, "1"}, {2, "2"}, {4, "4"}]`,
  validated at load (positive, finite, unique, sorted, exactly one `1.0`, non-empty labels). A
  continuous range would complicate the wire schema, the text parser, and rounding guarantees for
  zero design benefit; a small set renders as a deterministic keyboard menu and gives the player the
  requested granularity (finish/cast/crisis tiers). Powers of two keep scaled costs exact for every
  even MP cost in the catalog. The `4×` ceiling plus MP-pool availability bounds burst casting
  naturally (a 150-MP 主宰 spell at `4×` costs 600 MP, beyond every human pool).
- **Eligibility is "every effect is magnitude-scalable", not "has a damage effect".** A spell is
  scalable iff it is ACTIVE, carries an element and an `mp` cost, and every effect prefix is
  `damage`/`heal`/`self_heal` (e.g. `wind_blade`, `tornado_blade`, `sea_of_life`,
  `phoenix_eternal_flame` (damage+self-heal) qualify; `scorching_wave` (damage+DoT),
  `gale_step`, `haste_domain`, `purify` do not). *Alternative rejected:* scaling only the damage part
  of a mixed spell at full cost would preserve proportionality but hands players a discounted CC
  tool (`paralyzing_bolt` at 1/4 cost with full paralysis), and scaling the buff too has no defined
  magnitude semantics. Strict all-or-nothing keeps the cost↔magnitude ratio honest and the rule
  explainable: 「威力與消耗同比例增減，不受術式其他效果干擾」.
- **Scale lives on `ActionRequest` as a first-class field, not in `event_context`.**
  `scale: float = 1.0` on the frozen request is the natural home: step 2's resource check, step 6's
  deduction, step 5's handlers, and the preview all need it. `event_context` is caller-supplied
  handler data validated per-prefix; smuggling an internal key in would be an invisible contract.
  All existing constructions are keyword-based or positionally complete with four arguments, so a
  defaulted fifth field is backward-compatible without any migration.
- **Scale validation joins step 1 (ownership), and reuses one new rejection category.**
  The tier gate already rejects at the ownership step, so the freeform gate (membership in the
  allowed set ∧ direct mastery ownership ∧ eligible spell) lives beside it. All four failure shapes
  (unknown scale, no mastery, ineligible spell, unscalable mixed spell) return the same new
  `RejectReason.SCALED_CAST_FORBIDDEN` — the browser never sends an invalid scale from its own menu,
  so a single stable code for tampered/stale requests is sufficient and keeps the pipeline's
  rejection vocabulary small. `scale == 1.0` short-circuits the whole check and can never reject.
  **The check order is fixed and crash-safe**: scale-table membership first, then
  `is_freeform_eligible(skill)` (which itself requires an element), and only then
  `freeform_scales_for(actor, skill.element.key)` — so a non-elemental MP skill like
  `concentration` rejects cleanly instead of dereferencing `None.key`. The resource path mirrors
  this: `_adjusted_costs` gains a `scale=1.0` parameter (bundle adjustments on the unscaled base,
  then `scaled_mp_cost` on the `mp` amount), and both step 2 and step 6 pass `request.scale`, so
  preflight and deduction share one computation.
- **The effect-handler signature gains `scale: float`; only the three magnitude handlers use it.**
  `_step5_effect_resolution` is the single call site (plus test registrations). The damage handler
  rolls the hit and computes the final amount at staging time, so the scale is applied there:
  `scaled = scaled_magnitude(amount, scale)` with the existing `combat.yaml` damage floor applied
  afterwards (`max(scaled, floor)` — the floor itself is not scaled, so even a 1/4 cast lands its
  minimum hit). Heal/self-heal mirror this with `_heal_magnitude`. Buff/cleanse/conferral/movement
  handlers accept and discard the parameter; they only ever run at `scale == 1` because eligible
  spells contain no such effects. *Alternative rejected:* a context-injected key (hidden contract)
  and per-handler optional args (untyped drift); the uniform signature is mechanical but explicit.
- **Rounding is round-half-away-from-zero, shared by cost and magnitude.**
  `scaled_mp_cost(base_mp, scale)` and `scaled_magnitude(base, scale)` both compute
  `floor(value * scale + 0.5)` for positive values — symmetric for cost and damage so the
  proportionality claim stays true modulo one half-unit, deterministic across Python versions
  (unlike banker's rounding), and identical wherever cost is displayed (panel, preview, command
  echo, deduction). `scaled_mp_cost` is additionally clamped to a minimum of `1`: a scaled cost can
  never be zero, so a quarter-scale cast always still costs at least 1 MP and no scale combination
  can ever produce a free cast (the invariant holds even for hypothetical future 1-MP spells).
  Scaled MP deduction flows through `_adjusted_costs` so step-2/step-6 can never
  drift, and an unaffordable scaled cost rejects with the ordinary `INSUFFICIENT_RESOURCE`.
- **The server computes per-scale costs; the browser only renders.** The combat skill descriptor
  gains `freeform_scales` (ascending `{scale, label, mp_cost}` built from `scaled_mp_cost`), so the
  JS never re-implements rounding. The payload validator accepts the exact `scale` number members
  (all allowed values are exactly binary-representable, so float equality is safe). The keyboard
  dock inserts one scale-choice menu (「威力」) between skill selection and target selection for
  eligible skills, keeps the choice in the client-local selection state that a panel replacement
  rebuilds deterministically, and includes `scale` in every emitted cast payload
  (`commandDisplay` echoes the label, e.g. 「施展 風刃術（威力×2）」).
- **Text command token = yaml label.** `cast <skill_key>[@<scale>][=<target_key>]`, e.g.
  `cast wind_blade@2=wolf`, `cast wind_blade@1/2=wolf` (skill keys are the registry keys; Chinese
  labels are display-only and never accepted as skill keys); default `1`. `CmdCast` partitions the
  skill key on
  `@`, maps the token through the label table, and passes the scale into both the out-of-combat
  settlement path and the combat-session facade (`submit_player_action(..., scale=...)`). An unknown
  token or a token on a non-eligible spell produces a friendly Traditional Chinese message
  (`player_messages.py` gains the `SCALED_CAST_FORBIDDEN` text) rather than a usage error, so the
  player learns why the frame was rejected.
- **`element-mastery` stays pure-query; `freeform-casting` owns the execution.** The new
  `freeform_scales_for(entity, element)` query (element validated against `ELEMENT_REGISTRY`,
  empty tuple when mastery is not directly owned) extends the element-mastery spec's meaning of
  mastery; every state-changing or UI-facing behavior lands in the new `freeform-casting` spec so
  the single-writer and generative boundaries stay intact. **The element system itself is
  untouched**: `ELEMENT_REGISTRY`, `SkillDef.element`, and element-affinity mechanics change
  nothing; the gate simply compares the spell's own element against the mastered elements the
  actor owns. Mastery is strictly per-element — 風之主宰 scales wind spells only and never any
  other element's spells, and the UI and command rejection enforce the same boundary.
- **Freeform casting is invisible until mastered.** The feature is a deliberate surprise: a player
  without the element's mastery sees no scale selector, no `freeform_scales` field, and no mention
  of proportional casting anywhere in the UI. Only the text command can be used blind, and it
  rejects with a fixed Traditional Chinese explanation (「尚未掌握該屬性精髓，無法自由調整威力」) —
  so discovery happens when the character actually becomes 主宰.

## Risks / Trade-offs

- [Risk] Changing the effect-handler signature touches every registered handler and several test
  registrations; a missed call site breaks the pipeline at import/use time.
  → Mitigation: the change is mechanical with exactly one production call site; tasks require
  `grep register_effect_handler` across `world/rules/` and updating test registrations in the same
  task, plus running the full `action-resolution-pipeline` scenario suite before/after.
- [Risk] A scaled magnitude could interact subtly with existing consumers (overwhelm projection,
  upkeep, defeat credit, nonlethal knockout floor). → Mitigation: scaling changes only the final
  integer amount already produced today; every consumer reads amounts from staged effects/EventLog
  entries unchanged. The nonlethal floor (HP clamped at 1) and defeat crossing logic operate on the
  already-scaled amount, so existing invariants hold by construction; integration scenarios cover a
  scaled lethal cast and a scaled exam cast.
- [Risk] Float scale values on the wire invite tampered non-member values. → Mitigation: the
  validator enforces exact membership in the allowed set read from the same data table; any other
  float rejects with `malformed_payload`, and the adapter re-validates eligibility against current
  state before initiative (stale scale ≠ authoritative).
- [Risk] 1/4-scale casts of high-tier spells (e.g. a 130-MP 主宰 spell for 33 MP) could be spammed
  as cheap utility. → Mitigation: damage-per-MP is unchanged by design (linear scaling), and the
  `combat.yaml` damage floor caps the minimum so chip damage cannot go arbitrarily low; the 1/4
  scale mostly serves finishing blows and MP conservation, not efficiency gains.
- [Risk] The mixed-effect exclusion (e.g. `paralyzing_bolt`) may surprise players who expect every
  mastered spell to scale. → Mitigation: the panel shows the scale menu only for eligible spells,
  and the cast rejection explains the rule; the exclusion is documented in the command reference.

## Migration Plan

No data migration. `freeform_cast_scales` is a load-time-validated table; `ActionRequest.scale`
defaults to `1.0`, so existing callers and persisted sessions are unaffected. Lands after
`element-mastery`/`element-affinity` (already archived); no dependency on other active changes.

## Open Questions

None.
