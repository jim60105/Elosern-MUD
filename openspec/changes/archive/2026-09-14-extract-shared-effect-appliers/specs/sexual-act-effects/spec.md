## RENAMED Requirements

- FROM: `### Requirement: The pleasure handler replicates wetness_follows_arousal and the climax-phase progression directly, preserving the two-step 未達→接近→進行中 semantic`
- TO: `### Requirement: One shared pleasure entry point replicates wetness_follows_arousal and the climax-phase progression directly, preserving the two-step 未達→接近→進行中 semantic`

## ADDED Requirements

### Requirement: Every deterministic pleasure write lives in one shared module
Every deterministic caller that mutates an entity's pleasure — the sexual-act pleasure handler, the
divine maximum handler, the drain handler's forced reset, the defeat-aftermath settlements, and any
future non-skill caller — SHALL apply its change by calling a function in the one shared pleasure
module, never by assigning `entity.sexual.pleasure` directly. That module SHALL NOT import the cast
pipeline, so a caller that is not a cast can use it without depending on skill resolution.

The rulebook transition engine and the clock decay are the only other sanctioned deterministic
writers: `sexual_transitions._apply_then` SHALL write the pleasure trait only for an effect its
`sexual.yaml` rulebook declares (the `bounded_counter` kind), and `sexual_state.decay_tick` SHALL
keep its own floor-relative decay step. Neither is an effect-applier entry point; neither SHALL gain
callers beyond its existing rulebook- and clock-driven paths.

The module SHALL expose exactly two writer functions, because two genuinely different semantics
exist: a signed gain carrying the arousal-coupled cascade, and a forced reset to zero carrying none.
A reset SHALL NOT be expressed as a negative gain: doing so would run the gain path's
already-at-接近 branch and advance the target's climax phase, which draining a target to zero must
never do.

#### Scenario: No production code outside the sanctioned writers assigns pleasure
- **WHEN** the deterministic production core is inspected for assignments to a pleasure trait — an
  assignment to the `base` or `value` attribute of `entity.sexual.pleasure`, of a local bound to it,
  or of a `getattr(entity.sexual, ...)` field-dispatched trait in a function whose dispatch covers
  `pleasure`
- **THEN** every one of them is one of the shared module's two writer functions, the rulebook
  engine's `_apply_then` `bounded_counter` branch, or `decay_tick`'s pleasure branch — and no other
  production module assigns the trait directly

#### Scenario: A forced reset does not advance the climax phase
- **WHEN** a target whose `climax_phase.level` is `"接近"` has their pleasure forcibly zeroed by the drain path
- **THEN** their pleasure is `0` and their `climax_phase.level` is still `"接近"` — the reset carries
  no cascade

#### Scenario: A non-cast caller can apply pleasure without the cast pipeline
- **WHEN** a caller that resolves no skill imports the shared pleasure module
- **THEN** the import succeeds without importing the cast-resolution module, and the applied change
  produces the identical cascade a cast would produce for the same magnitude

## MODIFIED Requirements

### Requirement: One shared pleasure entry point replicates wetness_follows_arousal and the climax-phase progression directly, preserving the two-step 未達→接近→進行中 semantic
Applying a participant's computed pleasure gain SHALL go through one shared entry point that, in the
same `PendingEffect.apply()` call and in this order: (1) captures the participant's arousal ordinal
and whether `climax_phase.level` is `"接近"`, both **before** mutating `pleasure`; (2) mutates
`entity.sexual.pleasure.base`; (3) if the arousal ordinal strictly increased, increments
`entity.sexual.wetness.value` by exactly one; (4) if `entity.sexual.arousal.level` is now `"極限"`,
calls `_apply_climax_phase_set(entity, "接近")`; (5) if the pre-mutation capture found
`climax_phase.level == "接近"`, calls `_apply_climax_phase_set(entity, "進行中")`. Neither call in
steps 4-5 SHALL be gated by any condition beyond what `_apply_climax_phase_set` itself already
enforces (its own no-op on an invalid edge).

#### Scenario: A first-time crossing into 極限 moves climax_phase to 接近 only
- **WHEN** a participant's `climax_phase` is `"未達"` and a pleasure gain raises their arousal to the
  `極限` band for the first time
- **THEN** `climax_phase.level` becomes `"接近"` after the effect applies, not `"進行中"` — the
  進行中 transition requires a **separate**, later gain application while already at 接近

#### Scenario: A further gain while already at 接近 moves climax_phase to 進行中
- **WHEN** a participant's `climax_phase` is already `"接近"` (from a prior act) and a further
  pleasure gain resolves against them, regardless of whether arousal was already at `極限`
- **THEN** `climax_phase.level` becomes `"進行中"` after the effect applies

#### Scenario: An arousal-ordinal increase raises wetness by exactly one
- **WHEN** a pleasure gain raises a participant's arousal from one band to a higher band
- **THEN** `entity.sexual.wetness.value` increases by exactly one, clamped at its own configured
  bounds by `OrderedLevelTrait`'s own setter

#### Scenario: A gain that does not cross an arousal band leaves wetness unchanged
- **WHEN** a pleasure gain is applied but the participant's arousal ordinal is unchanged afterward
  (the gain was absorbed within the same band)
- **THEN** `entity.sexual.wetness.value` is unchanged by this effect

#### Scenario: The capture happens before mutation, not derived from post-mutation state
- **WHEN** the shared pleasure entry point's implementation is inspected
- **THEN** the arousal-ordinal and climax-phase captures are the first two statements, both reading
  `entity.sexual` before any line that mutates `entity.sexual.pleasure`
