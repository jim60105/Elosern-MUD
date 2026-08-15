## Why

`sexual-act-registry` (this proposal's direct dependency) makes a `SkillDef` able to *be* a sex act
and makes the unlocked set visible to `ActionResolver`, but every act it can produce still casts as a
no-op: `effects=[]`, because the `pleasure:`/`sexual_counter:` prefixes this proposal adds do not yet
exist. Nothing yet applies pleasure to a participant, resolves which body part a monster collapses to,
or computes the sensitivity/shame-scaled gain the whole system's growth curve depends on. Until this
lands, `SEXUAL_ACT_REGISTRY` is a schema with no working behaviour behind it.

## What Changes

- Add `world/rules/sexual_act_effects.py` (new module — named to avoid colliding with
  `world/skills/sexual_acts/`, the package `sexual-act-registry` added): `resolve_part(entity,
  declared_part)` (the `Monster`-collapses-to-`GENERIC_BODY_PART`/`None`-collapses-to-
  `GENERIC_BODY_PART` rule), `participants(actor, targets)` (actor-first, de-duplicated), and
  `compute_pleasure_gain(participant, part, base_pleasure, ratio, participant_count)` (the
  base × sensitivity × shame × participant-count formula, reading `PLEASURE_CONFIG`'s existing
  sensitivity/shame tables read-only and this module's own new participant-count table).
- Add `world/rules/rulebook/sexual_act_effects.yaml`: the participant-count multiplier table and
  `climax_extension_threshold`, loaded and validated at import by this new module — `sexual_pleasure.
  yaml` (owned by the already-archived `pleasure-gauge` change) is not touched.
- Add two effect prefixes to `world/skills/effects.py`'s dispatch table: `pleasure:<act_key>` →
  `PleasureEffect(act_key)` and `sexual_counter:<act_key>` → `SexualCounterEffect(act_key)`, each
  carrying only the acting `SexualActDef`'s own key — every other parameter (magnitude, parts,
  ratio, which counters) is read from `SEXUAL_ACT_REGISTRY[act_key]` at cast time, so no value is
  duplicated between the registry and the effect string.
- Add `_handle_pleasure_effect` and `_handle_sexual_counter_effect` to `world/rules/action.py`,
  registered through the existing `register_effect_handler` seam (surfaces
  `frozenset({"sexual"})`, no required event context) beside `sexual_event`. The pleasure handler
  stages one `PendingEffect` per participant applying that participant's computed gain to
  `entity.sexual.pleasure`, and — for a participant currently in `進行中` whose computed gain (before
  the trait's own 100-ceiling clamp) meets `climax_extension_threshold` — calls
  `entity.sexual.stage_climax_extension()` (shipped, uncalled since `climax-settlement`). The counter
  handler stages one `record_*()` call per name in `actor.actor_counters` (applied to the actor) and
  per name in `actor.participant_counters` (applied to every other participant), through an explicit
  attribute-name-to-mutator-name table, never a derived string transform.
- Extend `_act_family()` (`world/skills/sexual_acts/_builder.py`, owned by the dependency proposal)
  to set every row's `effects` to `[f"pleasure:{key}", f"sexual_counter:{key}", *(f"sexual_event:{name}"
  for name in row.sexual_events)]`. This is the one place this proposal edits a file
  `sexual-act-registry` created; it runs strictly after that proposal, not alongside it.
- The pleasure handler additionally replicates two `sexual.yaml` rules directly —
  `wetness_follows_arousal` and the `climax_gate`/`climax_phase_critical_point_to_in_progress` pair —
  because both are conditioned on a change `apply_event()`'s own snapshot must observe *within its own
  call*, which a pleasure gain applied outside `apply_event()` cannot produce. Both replications call
  already-public, already-sanctioned functions (`_apply_climax_phase_set`, exported in
  `sexual_state.py`'s `__all__`; the `OrderedLevelTrait.wetness` setter) with no change to either
  function. This is what makes climax-phase progression, and therefore climax extension, reachable
  through the ordinary catalog-act path for the first time.
- Every other declared `sexual.yaml` event an act names in its `sexual_events` tuple (experience-type
  recording, virginity, sensitivity-frequency, shame-from-watching) is emitted by reusing the
  existing, unmodified `sexual_event:<name>` prefix and handler — no new code, one new string per
  declared event. Events that target pleasure/wetness/climax-phase directly, or belong exclusively to
  climax settlement, are forbidden from an act's `sexual_events` (enforced structurally) because they
  would either double-count against the direct replication above or bypass the settlement mechanism's
  own ownership of `climax_ends`/`climax_extended`.

## Capabilities

### New Capabilities
- `sexual-act-effects`: `resolve_part`, `participants`, `compute_pleasure_gain`, the two balance
  tables, and the two effect handlers' full behaviour including extension staging.

### Modified Capabilities
- `skill-effect-model`: adds `PleasureEffect`/`SexualCounterEffect` to the typed dispatch table.
- `sexual-act-registry`: adds the requirement that `_act_family()` populates `effects` with the two
  new prefixes (additive — the dependency proposal's own requirements never pinned `effects=[]` as
  permanent, only as this proposal's precondition).

## Impact

- New: `world/rules/sexual_act_effects.py`, `world/rules/rulebook/sexual_act_effects.yaml`,
  `world/rules/tests/test_sexual_act_effects.py`.
- Modified: `world/skills/effects.py` (two new dispatch branches), `world/rules/action.py` (two new
  handlers plus two `register_effect_handler` calls), `world/skills/sexual_acts/_builder.py` (the
  `effects` list `_act_family()` builds), `world/skills/sexual_acts/tests/test_registry_structure.py`
  (two new structural checks: the solo-act/`participant_counters` invariant and the forbidden-events
  invariant).
- Does not modify `world/rules/sexual_state.py`, `world/rules/sexual_transitions.py`,
  `world/rules/rulebook/sexual_pleasure.yaml`, or `world/rules/rulebook/sexual.yaml` — every read
  against `PLEASURE_CONFIG`, `_apply_climax_phase_set`, `stage_climax_extension()`, and the
  `sexual_event:` dispatch/handler is read-only or reuses an already-public, unmodified surface.
- Still no player-visible act content: this proposal makes the wiring real, but `SEXUAL_ACT_REGISTRY`
  remains empty until the catalog proposals land. Voluntary exposure/shame-raising acts (羞恥線's core
  mechanic) remain unreachable until that line's own proposal adds a `sexual.yaml` row this proposal
  deliberately does not add — see design.md's Non-Goals.
