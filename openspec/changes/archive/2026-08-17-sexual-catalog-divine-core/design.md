## Context

`docs/superpowers/specs/2026-08-15-divine-sexual-arts-design.md` (the "design doc") splits the 神之秘法
line into `C7a` (three acts "reusing existing mechanisms," this proposal) and `C7b` (four acts needing
one new `SexualState` mutator each, a separate follow-on proposal). Every piece of gating
infrastructure this line needs is already shipped: `_step1_divine_arts_gate`, `RaceProfile.
can_use_divine_arts`, and the two mastery skills recategorised under `group="精通"`. This proposal's
only job is populating `DIVINE_ACTS`.

The design doc's "reusing existing mechanisms" framing is accurate at the `SexualState` layer — every
mutator these three acts touch (`stage_climax_extension`, `entity.traits`'s MP/SP/HP surface) already
exists and needed no change. It does not hold one layer up, at `_act_family()`/`action.py`'s effect
vocabulary, which is where most of this design's real decisions live.

**Correction made during review:** an earlier draft of this design assumed the resist contest was
still unwired, inert declarative metadata (matching every prior catalog proposal's disclosed state at
the time each was written). That assumption was stale: `sexual-resist-cast-wiring` (commits `0d6d0ef`/
`91a9afd`) landed in this same repository, in parallel, while this proposal was being drafted, and
`world/rules/action.py::_step4b_sexual_resist_gate` now rolls a real `resist_verdict()` per non-actor
target of any `resistible=True` sexual act and drops any target whose contest is resisted before
`_step5_effect_resolution` ever sees them. D-6 and D-7 below were rewritten against this corrected,
verified fact — see D-6 for what it means for these three acts' handlers specifically.

## Goals / Non-Goals

**Goals:**
- Ship 絕頂律令, 時姦, and 神域搾取 exactly as the design doc specifies their player-facing behaviour.
- Keep every new effect prefix general-purpose: nothing in `action.py`'s three new handlers reads
  `requires_divine_arts` or checks the caster's line. The exemption lives entirely in which acts choose
  to declare these effects, not in the handlers themselves — matching how every other line-crossing
  mechanism in this catalogue already works (`resolve_part`, `participants`, `compute_pleasure_gain`
  are all read by every line, never divine-specific).
- Leave `_act_family()`, `sexual_state.py`, and `sexual.yaml` untouched. If a later proposal (`C7b`)
  needs a real change to one of those files, it makes its own case independently.

**Non-Goals:**
- Building 感度創世, 恥辱剝奪, 絕對從屬, or 無垢回歸 (`C7b`).
- Changing anything about `_step4b_sexual_resist_gate` or `sexual_resist.py` — that mechanism is
  already shipped and live; this proposal only makes sure its three new handlers behave correctly
  under it (D-6).
- Changing `sexual-catalog-combat`'s deferred 搾取 or giving the catalogue a general cross-entity
  resource-transfer primitive. 神域搾取's drain is bespoke to this one act, not a reusable schema field
  (D-4).

## Decisions

### D-1: All three acts are hand-built directly in `divine.py`, not through `_act_family()`

`_act_family()`'s row tuple has exactly thirteen fixed positions, and every row it builds gets exactly
the same three effect kinds: `pleasure:{key}`, `sexual_counter:{key}`, and one `sexual_event:{name}`
per declared event. There is no row field for an arbitrary additional effect string. None of this
proposal's three acts can be expressed inside that shape:

- 絕頂律令 needs to *set* `pleasure` to a fixed value across two chained calls (D-2), not add a
  formula-computed delta.
- 時姦 needs to call `stage_climax_extension(3)`, a `SexualState` method with no `pleasure:`/
  `sexual_counter:`/`sexual_event:` counterpart.
- 神域搾取 needs to move a value between two entities' different trait surfaces (target's `pleasure`,
  caster's `mp`/`sp`/`hp`), which no existing prefix expresses in either direction.

Two ways to close this gap were considered and rejected in favour of hand-building:

1. **Add a fourteenth, optional row field to `_act_family()`'s tuple** (e.g. `extra_effects: tuple[str,
   ...] = ()`), letting a row declare arbitrary bonus effect strings. Rejected: Python tuple unpacking
   of a fixed-arity row has no notion of a trailing optional field without also changing every existing
   line module's row tuples (`solo.py`, `shame.py`, `partner.py`, `combat.py`, `interspecies.py`) to
   carry a fourteenth `()` element, for a capability only this proposal's three acts would ever use.
   That is a wide, five-file blast radius to solve a three-act problem.
2. **Route everything through `sexual_events`/`apply_event()`**, treating each act as "just" a new
   rulebook event. Rejected outright for 時姦 and 神域搾取 (neither operation is expressible as a
   `sexual.yaml` `then` clause: `stage_climax_extension(3)` is a method call with an argument, and a
   cross-entity transfer has no `field: X, delta/set: Y` shape at all — `sexual.yaml`'s schema is
   single-entity, single-field per rule). For 絕頂律令 specifically, this was the first design tried and
   is the one place a plausible rulebook event (`extreme_stimulus_applied`) already exists — D-2 covers
   why it was abandoned anyway.

All three handlers filter `actor` out of the entities they act on explicitly (`if entity is actor:
continue`), rather than trusting the resolved `targets` list to already exclude the actor. This was
tightened during review: `TargetSpec.AREA`'s `"all"` shorthand (`world/rules/targeting.py::
expand_target_shorthand`) returns every non-knocked-out roster member with no self-exclusion — unlike
`"all-enemies"`/`"all-allies"`, which filter through `context.relation_to` — so an actor casting 絕頂律令
with shorthand `"all"` would otherwise appear in its own `targets`. `_step4b_sexual_resist_gate`
doesn't remove that risk either: it explicitly keeps the actor in `surviving` targets when present
(skipping only their resist *roll*, per its own D-2 comment, "the actor never resists their own act"),
so an actor present in `targets` reaches `_step5_effect_resolution` unfiltered. The explicit
per-handler check is one line and removes the dependency on an assumption about a different module's
behaviour; see the delta spec's explicit actor-exclusion scenarios for 絕頂律令.

Hand-building means writing the `(SkillDef, SexualActDef)` pair directly in `divine.py`. This is safe:
`world/skills/sexual_acts/__init__.py`'s `_register_rows()` (the sole consumer of every line module's
tuple constant) treats every pair identically regardless of construction path — it checks key
agreement, key uniqueness, and collision against the pre-existing `SKILL_REGISTRY`, nothing about
`_act_family()` provenance. `test_registry_structure.py`'s whole-registry structural checks
(`check_registries_agree`, `check_external_acts_declare_a_target_part`,
`test_every_named_counter_and_event_resolves`) all scan `SEXUAL_ACT_REGISTRY`/`SKILL_REGISTRY`
directly and are equally satisfied by a hand-built entry, provided it declares real counter/event
names and a `None` target part on this `_PARLESS_LINES` line — both true here. Only the checks that are
properties of the `_act_family()` *function itself* (the forbidden-events check, the
`actor_pleasure_ratio` positivity check, ...) — tested by calling `_act_family()` directly, never by
scanning the registry — do not apply to a hand-built row. That is exactly the escape hatch this
proposal needs: none of the three acts declares a forbidden event or a `pleasure:` effect for its own
actor, so nothing here needed those checks weakened for anyone.

### D-2: 絕頂律令 does not use `sexual_events`/`extreme_stimulus_applied`, despite that rule existing for exactly this purpose

The design doc says 絕頂律令 is "implemented by emitting the shipped `extreme_stimulus_applied` event,"
and `sexual.yaml`'s `arousal_extreme_stimulus_to_max` rule (`{field: pleasure, set: 100}`) was built by
an earlier change with this act's Chinese-language design note attached to it verbatim ("極端刺激…可直接
躍升至「極限」"). That approach was tried first and traced through `world/rules/sexual_transitions.py`'s
`apply_event()` before being abandoned — it does not deliver "everyone caught climaxes at the next
upkeep" for the common case, and the reason is specific enough to write down so nobody re-attempts it.

`apply_event()` runs a fixed-point loop. The triggering event name (`extreme_stimulus_applied`) is only
present in the condition context (`context["event"]`) during **pass 1**; every pass after that runs with
`current_event = None`. Trace a target starting at `climax_phase="未達"` and `pleasure` below the `極限`
band, hit by `apply_event(target, "extreme_stimulus_applied")`:

- **Pass 1**: `arousal_extreme_stimulus_to_max` fires (event-conditioned), setting `pleasure` to `100`.
  `climax_gate` (condition: `arousal == 極限`) evaluates against the *pre-pass* context snapshot, taken
  before this pass's own mutations — arousal there is still whatever it was before the cast — so it does
  **not** fire yet. One field changed (`arousal`), so the loop continues.
- **Pass 2**: a fresh context is built, now reflecting `pleasure=100`/`arousal=極限`, but `context["event"]`
  is `None`. `climax_gate` now fires (未達→接近). `wetness_follows_arousal` fires too
  (`field_changed: arousal, direction: up`, reading pass 1's recorded change). One field changed
  (`climax_phase`), so the loop continues.
- **Pass 3**: context now reflects `climax_phase=接近`. The one rule that could advance 接近→進行中,
  `climax_phase_critical_point_to_in_progress`, requires `event: stimulus_applied` in its condition —
  but `context["event"]` has been `None` since pass 1, and the literal event name was
  `extreme_stimulus_applied`, not `stimulus_applied`, even in pass 1. The rule never fires. No field
  changes this pass, so the loop terminates.

Final state: `pleasure=100`, `climax_phase=接近` — one valid edge short of 進行中. Nothing later promotes
a `接近` entity into `進行中` on its own: `climax_settlement_action()` (the "next upkeep" mechanism) is a
no-op for any entity not already `進行中`, and the ordinary path to that edge is
`_apply_pleasure_gain()`'s own hand-coded, single-call, pre/post-mutation comparison — a completely
different code path from `apply_event()` that this act was never going through. So an enemy caught by
絕頂律令 while below 極限 would sit at the brink until some *other* stimulus finished the job — the
opposite of the design doc's "one free action, whole-team lockout" claim.

**Resolution:** don't use `apply_event()`/`sexual_events` for this act at all. Call the existing
`_apply_pleasure_gain(target, gain)` — the exact function every ordinary act's `pleasure:` effect
already calls, unmodified — **twice**, sequentially, per target:

1. `_apply_pleasure_gain(target, 100)`: sets `pleasure` to its ceiling (`+= 100`, clamped by the
   trait's own `max=100` bound regardless of the starting value) and walks at most one `climax_phase`
   edge (未達→接近, or 餘韻→接近 — both valid per `_VALID_CLIMAX_TRANSITIONS`; a target already at
   進行中 or already at 接近 is unaffected by this step beyond the gauge set).
2. `_apply_pleasure_gain(target, 0)`: applies no further gauge delta, but re-runs the same
   pre/post-mutation `was_at_critical_point` check — which now observes call 1's already-applied
   `climax_phase=接近` (if that is where call 1 left it) and walks the second edge, 接近→進行中.

Worked outcomes for every starting `climax_phase`:

| Starting phase | After call 1 | After call 2 |
|---|---|---|
| 未達 | 接近 (edge 1 walked) | 進行中 (edge 2 walked, `was_at_critical_point` now true) |
| 接近 | 接近 (no valid self-edge; gauge already maxed) | 進行中 (`was_at_critical_point` true from the start) |
| 進行中 | 進行中 (unaffected) | 進行中 (unaffected) |
| 餘韻 | 接近 (the 餘韻→接近 edge is valid) | 進行中 |

Every starting phase lands at 進行中 (or stays there), in one action, using nothing but two calls to an
already-shipped, already-tested function — a stronger "reuses existing mechanisms" claim than the
rulebook-event route it replaces, not a weaker one. No new cascade logic is written; `_apply_pleasure_gain`
is not modified. `wetness_follows_arousal`'s equivalent bump fires once, not twice — call 2's `arousal.value`
does not change relative to its own pre-call snapshot, since call 1 already maxed it, so the "arousal
increased" condition inside `_apply_pleasure_gain` is false on call 2.

One incidental, undesigned-but-harmless interaction: if a target is already `進行中` when hit, and
`climax_extension_threshold` (`20`) is less than `100`, call 1's `gain=100` independently satisfies
`_apply_pleasure_gain`'s own extension-staging condition (`was_in_progress and gain >=
climax_extension_threshold`) and stages one ordinary extension, on top of everything above. This falls
directly out of reusing the unmodified function and is consistent with the act's theme (catching someone
already mid-climax extends them further); it is not a bug and is asserted, not treated as a defect, in
the test plan.

`sexual.yaml`'s `arousal_extreme_stimulus_to_max` rule and the `extreme_stimulus_applied` event stay
exactly as shipped, exercised by their own existing test coverage (`test_sexual_transitions.py`) and
available to any future direct caller — unused by this proposal, not removed by it.

### D-3: 時姦's `climax_extension_stage:<count>` effect and the count=3 choice

The new prefix's handler is deliberately thin: `count = int(effect_id.partition(":")[2])`, then one call
to `target.sexual.stage_climax_extension(count)` per entry in `targets` (never the actor).
`stage_climax_extension` is already public, already validates `count` is a positive integer, and already
accumulates (`self.pending_climax_extension + count`) rather than overwriting — this act needs none of
that reimplemented.

`count=3` is a chosen constant, not derived from any existing balance table (the design doc says "several,"
not a number). Three consecutive extensions at the shipped SP cost per extension (`-15..-10`,
`sp_cost_on_climax_extension`) charges roughly triple the ordinary per-extension SP drain from one caster
action instead of three, matching the design doc's framing ("時姦 pays once and collects several rounds")
without being large enough to single-handedly exhaust a typical SP pool from one cast against a fresh
target — consistent with the line's own containment (the race gate is the binding constraint, not this
act's individual magnitude).

### D-4: 神域搾取's drain is one-to-one and bespoke, not a reusable schema field

The handler reads `target.sexual.pleasure.value`, adds that amount to `caster.traits.mp.current`,
`caster.traits.sp.current`, and `caster.traits.hp.current` (each trait's own existing bound
enforcement clamps at its maximum — no new clamping code, mirroring `sexual_transitions.py`'s own
`vital_gauge` handling of `sp`), then sets `target.sexual.pleasure.base = 0`. No ratio, no
participant-count multiplier: the design doc is explicit that this is "uncapped by the ratio that
bounds the catalogue's 搾取" (`sexual-catalog-combat`/C5's deferred act).

The pleasure read is **no-create**: `_handle_sexual_drain` reads the stored `sexual_traits`
attribute through `_stored_pleasure_value` rather than constructing `target.sexual`, because
`SexualState.__init__` writes the traits on first access — a storage write at effect-planning time,
before the commit snapshot, so a cast rejected after planning would leave the created trait behind
and break the action workflow's all-or-nothing boundary. This is the same discipline
`_sensitivity_level` (`sexual_act_effects.py`) and `_stored_sexual_level` (`combat_modifiers.py`)
document; an unmaterialized target reads as the 0 floor, which is exactly the "draining a
`pleasure=0` target is a harmless no-op" scenario. The drain is staged as **two** `PendingEffect`s
(one on the actor for the resource gain, one on the target for the zeroing) so the commit's
per-entity snapshot/rollback covers both mutated entities; the actor-side effect uses the no-log
`divine_drain_actor` description kind so the EventLog carries exactly one `divine_drain` entry
targeting the drained entity, not a duplicate actor-targeted entry.

This is intentionally **not** a step toward a general cross-entity resource-transfer primitive for the
catalogue. C5 deferred 搾取 for exactly this missing primitive; this proposal does not build one. The
`divine_drain:` prefix is scoped narrowly to what 神域搾取 needs (pleasure-in, MP/SP/HP-out, one-to-one),
not parameterised for reuse. A future proposal that wants a general drain schema for the ordinary
catalogue is free to generalise this handler, but that is out of scope here — grafting generality onto a
divine-only act's implementation, unvalidated against any other caller's needs, would be speculative.

### D-5: 時姦 on a target not currently `進行中` silently discards the staged count — accepted, not special-cased

`climax_settlement_action()` resets `pending_climax_extension` to `0` whenever `climax_phase != 進行中`
(existing, unmodified `sexual_state.py` behaviour, predating this proposal). Casting 時姦 on such a
target stages a value that is discarded at the very next settlement point without ever producing an
observable `climax_extended` emission. This is accepted as correct, not patched around, because the act's
own framing — "breaks the *per-round cost of suppression*" — presupposes suppression (climax) is already
underway; 時姦 is an amplifier for an existing chain-suppression fight, not a way to start one. Forcing a
target into 進行中 first would duplicate 絕頂律令's job with different mechanics for no narrative gain. No
error is raised — matching the design doc's own error-handling table precedent (`restore_purity()` on an
already-virgin entity is "no-op, no error").

### D-6: All three acts are `resistible=True`, and every handler must tolerate a fully-resisted cast

The design doc's headline claim — "every balancing mechanism the other five lines depend on has exactly
one 神之秘法 built to break it" — could be read as implying every divine act should bypass resist too.
It does not: §3 names 絕對從屬 (`C7b`) as the one act that "breaks the consent system," specifically by
short-circuiting the resist contest via a new `submission_marks` state, described as an addition
alongside the affinity `auto_comply` short-circuit, not a wholesale removal of resist. That framing
implies resist itself is not one of the mechanisms broken by C7a's three acts — only by that one C7b act.
`resistible=True` for all three here follows the same convention `sexual-catalog-combat` and
`sexual-catalog-interspecies` already use for every hostile-targeted act on their own lines.

**This has a real, live runtime effect, corrected from an earlier draft of this design that assumed
otherwise.** `_step4b_sexual_resist_gate` (`world/rules/action.py`, shipped by
`sexual-resist-cast-wiring`) fires for any skill whose key is in `SEXUAL_ACT_REGISTRY` with
`resistible=True`: it rolls `resist_verdict()` per non-actor target and drops any target whose contest
resolves `resisted=True` from the list `_step5_effect_resolution` receives. For `TargetSpec.SINGLE`
(時姦, 神域搾取), a successful resist reduces `targets` from one entity to **zero** before this
proposal's handlers ever run. For `TargetSpec.AREA` (絕頂律令), a successful resist against some (not
all) targets shrinks the list without emptying it.

Every one of this proposal's three new handlers is written to tolerate an empty or shrunken `targets`
list as an ordinary, non-error outcome — the same shape every pre-existing handler
(`_handle_pleasure_effect`, `_handle_sexual_counter_effect`, `_handle_sexual_event`) already uses (a
plain `for entity in targets` loop that produces zero `PendingEffect`s for zero survivors). This
matters most for 神域搾取, whose `TargetSpec.SINGLE` guarantee ("`targets` contains exactly one entity")
only holds at `_step3_targeting`, *before* the resist gate runs — by the time
`_handle_sexual_drain` executes, `targets` can legitimately be empty. The handler treats that as a
graceful no-op (cast still succeeds; the resist verdict is still logged via
`_step4b_sexual_resist_gate`'s own `_resist_pending_effect`; nothing is drained), never as a rejection.
A defensive rejection is reserved for `len(targets) > 1`, which stays structurally unreachable for a
`SINGLE`-target act regardless of resist and would indicate a genuine caller error if it ever happened.

Since resist is genuinely live, C7b's 絕對從屬 is not "the one place resist doesn't apply, whenever a
future wiring proposal lands" (the earlier framing) — it is, today, the one act in this whole catalogue
whose entire purpose is to make a specific caster/target pair's contest stop rolling at all. Every other
resistible act, including this proposal's three, resists normally, right now.

### D-7: 神域搾取's uncapped resource generation is accepted, not additionally costed or capped

神域搾取 converts a target's `pleasure` (0-100) one-to-one into the caster's `mp`, `sp`, and `hp`
simultaneously, at zero cost to the caster (every `_act_family()`-style act in this catalogue is
`cost={}`, and this hand-built act follows the same convention) and with no cooldown (no skill in this
engine has a cooldown primitive — the only throttle on repeated casting anywhere is the flat per-action
time cost). Read in isolation, this is net resource *generation*, a mechanic category no other act in
any of the five ordinary lines has (every other act only ever manipulates `SexualState` fields, never a
caster's core combat resources).

This is accepted as designed, not additionally gated, for three reasons that already bound it:

1. **It requires a target whose `pleasure` is already elevated.** That value had to be generated first,
   through the ordinary sexual-act economy (this act converts existing accumulated value; it does not
   create pleasure out of nothing the way, say, casting it on a fresh `pleasure=0` target does — D-4's
   own no-op scenario).
2. **It is `resistible=True` (D-6).** A target can refuse the contest and deny the drain entirely; this
   is not a free, unconditional resource tap against an unwilling target.
3. **It is gated by the same narrow race+skill door as the rest of the line** (`_step1_divine_arts_gate`,
   currently `elf`-only). The design doc's own framing for the whole line is that magnitude is not the
   containment mechanism — the gate is.

No SP/action cost is added to the caster and no cap beyond each trait's own maximum is added, resolving
the design doc's own unresolved Q4 rather than leaving it open. A future balance pass remains free to
revisit this once real playtesting data exists; nothing here forecloses that.

### D-8: This change amends `unlocked_act_keys_for`'s mastery branch — the shipped blanket grants divine acts, and the delta spec scenario requires otherwise

The proposal's original task 1.3 assumed the 神之秘法 line's blanket-unlock exclusion was already
enforced by `unlocked_act_keys_for`'s existing logic ("not by any special-casing this change adds").
**That assumption is false, verified empirically before planning**: the shipped mastery branch is
`if mastery: return frozenset(SEXUAL_ACT_REGISTRY)` — the *entire* registry, divine acts included once
registered. The delta spec scenario "SexualMasteryEffect ownership alone does not unlock any of the
three" and the divine design doc §1.1 ("The 性魔法主宰 blanket unlock does not reach them. That unlock
covers the counter-gated catalogue only") both require the mastery result to exclude
`requires_divine_arts=True` acts.

So this change amends `unlocked_act_keys_for` in `world/skills/sexual_acts/__init__.py`: the mastery
branch becomes

```python
if mastery:
    return frozenset(
        key
        for key, act in SEXUAL_ACT_REGISTRY.items()
        if not SKILL_REGISTRY[key].requires_divine_arts
    )
```

Keyed on the existing `SkillDef.requires_divine_arts` data field, never a hardcoded key list — the same
discipline overview D-9 demands. Every `SEXUAL_ACT_REGISTRY` key is present in `SKILL_REGISTRY` by the
registration-agreement invariant (`check_registries_agree` enforces it modulo the three mastery
exclusions, which are not acts), so the new dereference is safe without repeating the docstring's
`if key in SKILL_REGISTRY` guard — that guard stays in the mastery `any()` comprehension exactly where
the source-inspection test pins it.

The **counter-driven branch is deliberately unchanged**. The three acts declare `unlock={}`, and the
shipped `sexual-state-handler` contract — "A seed act with an empty unlock mapping is always present",
plus the delta spec scenario "a divine-capable actor with zero counters owning all three — no counter
threshold gates it" — requires an empty unlock mapping to mean unconditionally owned. Restricting the
counter-driven branch would contradict the shipped main spec and break the scenario; the containment
for this line is the race gate at cast time (overview D-9), not the unlock machinery. The asymmetry —
a plain human "owns" the acts in `owned_keys()` but can never cast them, while a mastery holder does
not own them at all — is the design doc's "two unrelated acquisition paths" taken literally.

This is why the delta spec of this change carries a `sexual-state-handler` MODIFIED requirement:
the shipped requirement text ("or unlocks it entirely for a mastery holder") is amended to carve out
`requires_divine_arts` acts, so the main spec stays truthful after this change lands.

## Risks / Trade-offs

- **Three new `action.py` effect prefixes for three acts** → each is a small (10-20 line), independently
  testable handler; none introduces new state, all mutate only already-`SNAPSHOTTED_SURFACES` (`sexual`,
  `traits`), so rollback-on-rejected-action is unchanged. Mitigation: each gets its own unit test calling
  the handler directly (not only through a full cast), matching the granularity `test_registry_structure.py`
  already uses for `_act_family()`'s own checks.
- **Divergence from the design doc's literal implementation note for 絕頂律令** (D-2 replaces "emit
  `extreme_stimulus_applied`" with two `_apply_pleasure_gain` calls) → mitigated by writing the full trace
  above rather than asserting the change is necessary, and by leaving the rulebook rule itself untouched
  so nothing about this decision is a regression for any other consumer.
- **Hand-built acts bypass `_act_family()`'s per-row structural checks** (D-1) → mitigated by every act
  still declaring real, `sexual-act-registry`-compliant field values (no forbidden events, correct
  `_PARLESS_LINES` handling, real counter names in the empty tuples) and by the new test module asserting
  each hand-built pair's shape directly, since `_act_family()`'s own tests cannot cover code that never
  calls it.
- **`神域搾取`'s drain has no upper bound on how much MP/SP/HP one cast can restore** beyond the target's
  current `pleasure` value (at most `100`) and the caster's own trait ceilings → accepted per D-7:
  bounded by requiring pre-existing target pleasure, by resist, and by the race+skill gate, not by
  magnitude.
- **A successful resist against `神域搾取`'s sole target, or against every target of an AREA 絕頂律令
  cast, shrinks or empties `targets` before this proposal's handlers ever run** (D-6) → mitigated by
  writing every handler to treat an empty/shrunken `targets` list as an ordinary no-op, matching every
  pre-existing effect handler's shape, with explicit test coverage for the resisted case per act.
- **`world/skills/sexual_acts/tests/test_registry_structure.py::test_every_line_module_is_importable_
  with_only_divine_empty`, currently green, hard-asserts `DIVINE_ACTS == ()`** → this proposal both
  updates that test (it necessarily fails once `DIVINE_ACTS` is non-empty) and files a `MODIFIED
  Requirements` delta against the already-shipped `sexual-act-registry` capability, whose "異種 and
  神之秘法 remain empty" requirement text is obsolete once this proposal ships (異種 was already filled by
  the already-implemented `sexual-catalog-interspecies`; this proposal is what finally makes the "remain
  empty" clause untrue for both named lines). See tasks.md §6 and the delta spec.
- **The mastery blanket currently grants divine acts (D-8)** → the delta spec scenario "SexualMasteryEffect
  ownership alone does not unlock any of the three" and the divine design doc §1.1 require the exclusion,
  so this proposal amends `unlocked_act_keys_for`'s mastery branch. Two further existing tests break as a
  direct consequence and are updated in this proposal (tasks.md §6): `test_seed_acts.py`'s
  `test_interspecies_and_divine_gain_no_seed` pins `DIVINE_ACTS == ()`, and `test_sexual_unlock.py`'s
  `test_direct_mastery_ownership_unlocks_the_entire_catalogue` asserts the mastery result equals the
  whole registry (now minus the three divine acts). A `sexual-state-handler` MODIFIED delta (D-8) keeps
  the shipped "unlocks it entirely" requirement text truthful.

## Migration Plan

Additive only — a new, previously-empty tuple gains three entries, and `action.py` gains three new
dispatch-table prefixes no existing `SkillDef` names. One existing test is updated to match (it
currently pins `DIVINE_ACTS == ()`, which this proposal makes false by design). No other existing
behaviour changes for any already-shipped act, skill, or rule.

## Open Questions

None outstanding — D-6/D-7 resolve what earlier drafts left open (resist-contest interaction, 神域搾取's
resource-generation balance).
