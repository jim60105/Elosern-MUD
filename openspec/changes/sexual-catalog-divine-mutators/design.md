## Context

`sexual-catalog-divine-core` (`C7a`) is a separate, already-committed OpenSpec **proposal** — its
proposal.md/design.md/spec.md/tasks.md artifacts exist and are validated, matching this whole batch's
established convention (every catalog proposal since `sexual-act-seeds` ships as artifacts first, with
implementation following in a later, separate `/opsx:apply` pass). `C7a`'s own `tasks.md` is entirely
unchecked as of this proposal: `DIVINE_ACTS` in the actual source tree is still `()`, and none of `C7a`'s
three effect prefixes exist in `action.py` yet. This proposal is written and sequenced **assuming C7a's
implementation lands first** — it extends the same `DIVINE_ACTS` tuple `C7a`'s tasks.md describes filling
to three entries, taking that as a precondition, not a currently-true fact about the working tree. An
implementer following this proposal's tasks.md §1.1 will find that check failing until `C7a` is actually
applied; that is expected, not a defect in either proposal, and tasks.md §1.1 is written to say so
explicitly.

What `C7a` did establish, as a pattern this proposal reuses without re-deriving (from its committed
design.md, independent of whether its code has landed yet): hand-build each act's `(SkillDef,
SexualActDef)` pair outside `_act_family()` when it needs an effect no existing prefix expresses, filter
the actor out of the entities a handler acts on explicitly (never trust upstream target resolution to
have done it), and treat a resist-emptied `targets` list as an ordinary no-op, never a rejection —
because `_step4b_sexual_resist_gate` (`sexual-resist-cast-wiring`, already merged and live in the
codebase today, independently of either divine-line proposal) runs before every effect handler.

This proposal's four acts (感度創世, 恥辱剝奪, 絕對從屬, 無垢回歸) each need exactly one new
`SexualState` mutator, per the design doc. Three of the four also need a new `action.py` effect prefix
(the same C7a pattern); 絕對從屬 additionally needs a real change to `world/rules/sexual_resist.py`, a
file neither the design doc's stated Scope nor `C7a`'s amendment of it lists — see D-5.

## Goals / Non-Goals

**Goals:**
- Ship all four acts exactly as the design doc specifies, completing the 神之秘法 line (no further
  deferrals after this proposal).
- Keep every new `SexualState` mutator a single, auditable write path for its own state, matching the
  design doc's explicit framing: "None weakens an existing guard; each adds a separate, auditable door
  that no ordinary rule path can reach."
- Wire `submission_marks` into `resist_verdict()` without breaking its documented no-create, pure-function
  contract (`sexual-resist-contest`'s own shipped requirement).

**Non-Goals:**
- Re-litigating `C7a`'s established patterns (hand-building, actor-filtering, resist-tolerant handlers) —
  reused here, not redesigned.
- Clearing `experience_types` for 無垢回歸, or changing the shipped `virgin` public setter's contract —
  both are explicitly out of scope per the design doc §3, and D-4 below is the non-regression argument
  for why this proposal's `restore_purity()` doesn't need either.
- Any change to `恥辱剝奪`'s or `感度創世`'s effect on an entity that already has no valid target (e.g. a
  `Monster` for `恥辱剝奪` — D-3 covers this as a rejection, not a silent no-op, per the design doc's own
  error table).

## Decisions

### D-1: All four acts are hand-built, reusing C7a's established pattern

Same reasoning as `C7a` D-1, not repeated in full here: none of the four fits `_act_family()`'s
pleasure/counter/event effect triad (each needs a bespoke mutator call with no existing effect-string
shape), and `world/skills/sexual_acts/__init__.py::_register_rows()` accepts any `(SkillDef,
SexualActDef)` pair regardless of construction path. `DIVINE_ACTS` grows from three entries (`C7a`) to
seven; this proposal only appends, never edits `C7a`'s three.

### D-2: 感度創世 seeds only the parts an entity can ever resolve to

`saturate_sensitivity()` sets sensitivity to `SENSITIVITY_LEVELS[-1]` (`敏感異常`, ×2.5) for every
`BODY_PARTS` member on an ordinary entity, but for a `Monster` seeds only `GENERIC_BODY_PART`. This
mirrors `resolve_part`'s existing, unconditional collapse: a `Monster` target's `actor_part`/
`target_part` always resolves to `GENERIC_BODY_PART` regardless of what's declared (`sexual-act-effects`'
own shipped behaviour), so seeding all thirteen-or-however-many named `BODY_PARTS` on a `Monster` would
create trait state nothing ever reads — dead writes with no test that could ever observe them, and a
`_SensitivityProxy` entry per unreachable part for the lifetime of that Monster instance.

### D-3: clamp_shame_to's bound-setter ordering, and why it rejects a Monster target

`clamp_shame_to(level)` reuses the exact mechanism `SexualState.__init__` already applies to a fresh
`Monster`'s `shame` (`shame.min = shame.max = 0`), just at the opposite end of the vocabulary. The two
bound setters are not independent: `OrderedLevelTrait.min`'s setter requires `0 <= value <= self.max`,
and `.max`'s setter requires `self.min <= value <= vocabulary_max`, each re-clamping `.value` into the
new range as a side effect. For `level="成癮"` (`SHAME_LEVELS[-1]`, the vocabulary's own maximum), this
proposal sets `.max` first (`self.max <= target` trivially holds pre-mutation since `target` already
equals the vocabulary maximum), then `.min` (`0 <= target <= self.max` now holds since `.max` was just
set to `target`) — an order that is safe for this call's actual argument regardless of the trait's
current bounds beforehand, since widening/no-op-ing `.max` to the vocabulary ceiling can never violate
its own precondition.

A `Monster` target is rejected rather than silently re-pinned: `SexualState.__init__` already
permanently pins a `Monster`'s `shame` bounds to `min=max=0` (`sexual-state-handler`'s own shipped,
tested requirement — "a monster's shame is permanently pinned to 無"). Calling `clamp_shame_to` on a
`Monster` would either silently violate that shipped invariant (if it succeeded) or need a
special-cased "re-pin the floor pin at the ceiling instead" path that contradicts the entire reason that
baseline exists. Rejecting is the design doc's own stated behaviour for this exact case (§5's error
table: "`clamp_shame_to()` on a `Monster`: Rejected").

The `Monster` check happens **twice, at two different layers, for two different reasons**: `clamp_shame_to`
itself raises `ValueError` defensively (so any future, non-hand-built caller of the mutator still fails
closed), but `_handle_clamp_shame` does not rely on catching that exception from inside a staged
`PendingEffect`. Every mutation in this codebase's effect pipeline is staged lazily and applied only at
`_commit()`'s single atomic point (`world/rules/action.py`), specifically so a rejected action leaves no
partial state change; an exception raised from *inside* a `PendingEffect.apply()` closure is caught by
`_commit()` and reported as `CommitFailed`/`RejectReason.COMMIT_FAILED` — a different, and here
incorrect, code path from the synchronous `RejectedAction` every other defensive rejection in this file
produces (`_resolve_act`'s absent-key check is the precedent, and it raises `RejectedAction` from inside
the handler body, before any `PendingEffect` is built, not from inside one). `_handle_clamp_shame`
therefore checks `isinstance(target, Monster)` **eagerly**, inside the handler function itself, before
staging anything, and raises `RejectedAction(RejectReason.EFFECT_RESOLUTION_FAILED, ...)` directly —
`isinstance()` is a pure read, so doing it eagerly introduces no atomicity risk, and
`_step5_effect_resolution`'s existing try/except around the handler call converts any bare exception
raised there into the same `RejectedAction`/`EFFECT_RESOLUTION_FAILED` shape regardless, so the eager
check is not even strictly required for correctness — it exists to make the reject reason explicit and
avoid running the full snapshot/atomic-commit/rollback machinery for a failure known before any
`PendingEffect` is even built.

### D-4: restore_purity() bypasses the public virgin setter without weakening its shipped guarantee

`SexualState.virgin`'s public setter is unconditionally a no-op once `virgin` is `False`
(`if not self.virgin: return`) — `sexual-state-handler`'s own shipped requirement: "once the public
setter sets it False, no later mutation through that public setter SHALL be able to set it back to
True." `restore_purity()` does not call that setter; it writes the underlying attribute directly
(`entity.attributes.add("virgin", True, category="sexual_state")`), the same primitive the setter itself
uses internally.

This is not a regression of the shipped requirement, because the requirement's own text is scoped to
"the public setter" specifically, not to `virgin` as a concept — a distinction the design doc itself
draws out explicitly (§3, 無垢回歸) and this proposal inherits verbatim: every ordinary rule path
(`sexual.yaml`'s `virginity_once` rule, any future `_act_family()`-built act) still writes `virgin`
exclusively through the public setter, still can't reverse it. `restore_purity()` is the *one* second
door, race-gated behind `requires_divine_arts`, exactly as the exemption pattern this whole line
demonstrates elsewhere (D-4's own self-pleasure exemption in `C7a`, applied here to a different shipped
invariant). The shipped requirement's test (`entity.sexual.virgin` stays `False` "regardless of what any
later caller or future rule attempts through the same setter") keeps passing unmodified — this proposal
adds a scenario asserting exactly that non-regression, not a change to the existing one. `experience_types`
is untouched, per the design doc's explicit "the body is restored, the memory is not."

Calling `restore_purity()` on an already-`True` `virgin` entity is a no-op (writing `True` over `True`),
matching the design doc's error table ("no-op, no error") without any extra guard code — the write is
idempotent by construction.

### D-5: 絕對從屬 wires submission_marks into resist_verdict() without breaking its no-create contract

`resist_verdict()` (`world/rules/sexual_resist.py`) is documented and tested as a pure, no-mutation, **no-
create** function: `_climax_turn_short_circuit` reads `climax_turns` via `resister.attributes.get(...)`
directly rather than `resister.sexual.climax_turns`, specifically because materializing `entity.sexual`
on first access persists traits — a side effect this function's contract forbids.
`mark_submission`/`submission_marks` follow the identical discipline: `SexualState.mark_submission`
(the mutator, used only by 絕對從屬's own handler, which already has a materialized `entity.sexual` by
the time any effect handler runs) writes through the ordinary `entity.sexual` surface, but
`resist_verdict()`'s new `_submission_term(actor, resister)` helper reads the same underlying attribute
directly: `resister.attributes.get("submission_marks", default=frozenset(), category="sexual_state")`,
never touching `resister.sexual`.

`resist_verdict()`'s short-circuit condition becomes a three-way `or`:
`affinity_auto_comply or submission_marked or _climax_turn_short_circuit(resister)`. Order does not
matter functionally (each term is independently sufficient and none has a side effect), but
`submission_marked` is checked second, immediately after `affinity_auto_comply`, since both are
per-caster-pair facts resolved once per call, while `_climax_turn_short_circuit` additionally reads a
second attribute (`climax_turns`) — grouping the two single-read checks together keeps the function's
existing read order legible.

**Identity: `str(actor.id)`, not `_entity_key(actor)`.** `_entity_key` (`action.py`'s `str(entity.key)`)
is used everywhere else in this codebase purely for human-readable `PendingEffect` description strings —
never as a stored identity later compared for equality. It is unsuitable here: `world/maps/
wilderness_population.py` spawns monsters via `create_object(Monster, key=expected.name_zh)`, giving
every monster of the same species an identical `.key` string with no per-instance suffix, and nothing
about the divine-arts race gate guarantees a caster is a uniquely-keyed `PlayerCharacter` (an NPC of a
divine-capable race, or two identically-named NPCs, are not ruled out). Since `submission_marks` is
permanent and has no removal path (D-6), a wrong match from a shared `.key` can never be corrected. This
proposal instead stores and looks up `str(actor.id)` — Evennia's database primary key, already used
elsewhere in this codebase as a stable per-instance identifier (`world/rules/map_knowledge.py`'s
`encode_room(int(location.id))`) — guaranteed unique per object regardless of display name.

This is the one file in this proposal outside the design doc's stated Scope (even as amended by `C7a`).
The design doc's own described behaviour for 絕對從屬 — "the resist contest consults it at the same
point it consults the affinity `auto_comply` flag" — is not buildable without editing `resist_verdict()`
itself; there is no hook, callback, or extension point in the shipped `sexual_resist.py` for a caller to
add a short-circuit term from outside. The change is minimal and additive: one new private helper, one
new `or` term, zero changes to any existing parameter, return shape, or short-circuit condition.

### D-6: All four acts are resistible, with the same actor-filter and empty-targets discipline C7a established

`resistible=True` for all four, including 絕對從屬 itself — the *initial* cast that plants the mark can
be resisted like any other hostile act; it is every *subsequent* contest between that caster/target pair
that the resulting mark short-circuits, not this one. Every handler explicitly filters the actor out of
the entities it acts on (never relying on target resolution alone, per `C7a` D-1's finding about the
`"all"` AREA shorthand — moot for these four `TargetSpec.SINGLE` acts, but kept as the same
defense-in-depth line for consistency) and treats an empty `targets` list (a fully-resisted sole target)
as a no-op, never a rejection, per `C7a` D-6.

## Risks / Trade-offs

- **`resist_verdict()` gains a third short-circuit term, in a file this proposal is the first to touch
  outside the design doc's original Scope** → mitigated by the change being a single additive `or` term
  with no change to any existing parameter or return shape, and by `sexual-resist-contest`'s own existing
  test suite continuing to exercise the two pre-existing terms unmodified; this proposal adds coverage
  only for the new term and the three-way interaction.
- **`clamp_shame_to`'s bound-setter ordering is argued, not exhaustively tested against every possible
  prior bound state** → mitigated by the mutator only ever being called with `level="成癮"` (the
  vocabulary maximum) by this proposal's own act, and by design.md D-3's argument holding for any prior
  state where `min <= target`, which is guaranteed for every entity this mutator can legally be called on
  (a `Monster` is rejected — eagerly, before any `PendingEffect` is even staged — before any bound is
  touched).
- **`submission_marks` stores a permanent, unremovable identity with no correction path if the wrong
  identity scheme were used** → this is why D-5 specifically uses `str(actor.id)` (a guaranteed-unique
  database key) rather than `_entity_key`/`.key` (confirmed non-unique across same-species `Monster`
  spawns via `wilderness_population.py`), catching what would otherwise be a silent, permanent
  misattribution risk before it could ship.
- **感度創世's permanent, uncapped ×2.5 sensitivity saturation has no cost or cooldown**, mirroring
  `C7a`'s 神域搾取 finding (D-7 there) → accepted for the same reasons: gated by the race+skill door and
  by resist, not by magnitude, consistent with this whole line's stated design philosophy.

## Migration Plan

Additive only, and sequenced after `C7a`'s implementation: once `C7a` lands, `DIVINE_ACTS` grows from
three entries to seven; `SexualState` gains four new mutators and one new lazily-defaulted attribute
(`submission_marks`); `resist_verdict()` gains one new `or` term. No existing behaviour changes for any
already-shipped act, skill, rule, or the two terms `resist_verdict()` already had — and this proposal's
own tasks.md §1.1 confirms `C7a`'s implementation is present before doing any of the above, rather than
assuming it.

## Open Questions

None outstanding.
