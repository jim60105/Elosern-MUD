## Context

See `proposal.md` — Why, and `docs/superpowers/specs/2026-09-14-item-effect-model-design.md` §4,
which this change implements in isolation.

Constraints that shape the approach:

- `world/rules/targeting.py` is on the hot path of every cast, every combat round, and every action
  preview. The refactor must be provably behavior-preserving, not merely intended to be.
- Only four non-test call sites exist (`action.py:394`, `action_preview.py:215`, `:222`, `:327`), so
  the blast radius is small; the cost is concentrated in `test_targeting.py`.
- `AGENTS.md`: the deterministic core is the sole writer of state. This change writes nothing — it
  only changes how the resolver is asked a question.
- The project is unreleased with zero users; no compatibility shim is wanted for the old signatures.

## Goals / Non-Goals

**Goals:**

- `world/rules/targeting.py` imports nothing from `world/skills/` except the vocabulary types it
  resolves against (`TargetSpec`, `FactionConstraint`).
- Every parameter a function receives is a parameter it reads.
- A caller that is not a skill can resolve targets without fabricating one.

**Non-Goals:**

- Changing any targeting *rule*. Presence/alive/range/faction ordering, AREA silent-drop filtering,
  shorthand expansion, and every `RejectReason` stay byte-for-byte.
- Implementing a real `is_in_range`. Dropping the unused parameter is not the start of positional
  combat; that stays owned by the change the spec already names.
- Any item-side work. This change ships with zero item files touched.

## Decisions

### D1 — One `TargetRequirement` value object, not four loose parameters

`resolve_targets(actor, context, requirement, candidates)` takes one frozen value rather than
`(spec, faction, forbid_self)` spread across the signature.

*Why:* the three fields always travel together, callers should be able to name and reuse a
requirement (item scopes map to exactly five constant requirements), and a value object gives the
"the definition owns this, not the caller" invariant a single place to live.

*Alternative rejected:* keep passing the definition but type it as a `Protocol` with
`target_spec`/`faction_constraint` attributes. This preserves the coupling in spirit — the resolver
would still be reading fields off whatever is being used, and an item definition would have to grow
skill-shaped attribute names to satisfy it.

### D2 — `forbid_self` as a requirement flag, not a resolver branch

The sexual-act self-cast prohibition moves from a `SkillCategory` test inside `resolve_targets` to a
boolean the `SkillDef` sets.

*Why:* this is the actual SRP violation. A general resolver that names one skill category will, over
time, name two. As a flag, the rule is stated once by the definition that needs it, and a future
non-skill definition can adopt the same rule without touching the resolver.

*Alternative rejected:* leave the category test and have items pass a sentinel category. That
inverts the dependency the wrong way.

### D3 — Drop `skill` from `is_in_range` rather than pass the requirement through

*Why:* neither implementation reads it, and range is a property of two entities plus the world, not
of what is being used. Threading the requirement through would preserve a coupling that has never
carried information. If positional combat later needs a reach classification, it will need an entity-
or weapon-derived value, not the definition — so the parameter would be wrong even then.

*Trade-off:* `battlefield-action-context`'s "regardless of the skill's own identity" scenario loses
its ability to pass two differently-flavored skills. It is replaced by a structural assertion on the
signature, which is a stronger guarantee.

### D4 — `damage_requires_battlefield()` moves to a new `world/rules/action_gates.py`

*Why:* it answers "may this skill's effects run outside combat", which is neither presence, alive,
range, nor faction. It is in `targeting.py` only because that is where it was written.

*Why a new module rather than folding it into `action_preview.py`:* both `action.py` and
`action_preview.py` call it, and the spec text names it "the ONE shared expression" of that gate —
putting it inside one of its two callers would re-create the import asymmetry.

*Note:* `test_action_pipeline_rejections.py` asserts against the function's source text via
`inspect.getsource`. The body must move unedited, or that sanctioned-gate assertion fails.

### D5 — Validator signature uniformity over minimal parameter lists

All four validators take `(actor, context, requirement, target)` even though presence and alive read
only three of the four.

*Why:* they are dispatched from one `_VALIDATORS` tuple; a uniform signature keeps that dispatch
free of per-validator adaptation. The original sin was not the uniform signature, it was that the
uniform signature carried a `SkillDef`.

### D6 — Verification strategy: the existing suite is the proof

No new behavioral tests are written for the refactor beyond the two structural assertions the specs
require (the resolver imports no skill-category vocabulary; `is_in_range` has two parameters). Every
existing `test_targeting.py` case is ported signature-only, with no assertion text changed.

*Why:* if a ported test needed its expectations adjusted, that would mean behavior moved — which is
exactly what must not happen. Assertion churn in the port is the failure signal.

*Scale:* 18 `resolve_targets` call sites in `test_targeting.py`, plus one `is_in_range` call in
`test_battlefield_action_context.py`.

## Risks / Trade-offs

- **A ported test is silently weakened while its signature is updated** → port mechanically, one
  construct at a time; review the diff for any changed `assert*` argument. An assertion change in
  this diff is a bug, not a fix.
- **`SkillDef.target_requirement` is computed per access and `SkillDef` is frozen and widely
  constructed** → build it as a cached property or compute in `__post_init__` into a frozen field;
  the registry constructs every skill once at import, so either is cheap. Do not add a mutable
  attribute to the frozen dataclass.
- **The `inspect.getsource` assertion breaks on the gate move** → move the function body unedited
  and update only the import in the test.
- **Merge conflict with `extract-shared-effect-appliers`** → both changes edit
  `world/rules/action.py`'s import preamble around `:48-58` (this one swaps the `targeting`/
  `action_gates` imports; the other adds a `pleasure` import and drops a `sexual_state` one). The
  edits are logically independent but textually adjacent: sequence them rather than working both trees
  at once.

## Migration Plan

No data migration. The change is one commit: signatures, the new value object, the gate move, and the
test port land together, because the old and new resolver signatures cannot coexist without a
compatibility shim this project does not want.

Rollback is a revert; nothing persisted changes.
