## Why

`world/skills/sexual_acts/divine.py` ships pre-declared and empty. The 神之秘法 line's gating
machinery is already fully shipped and unrelated to this proposal: `_step1_divine_arts_gate` (race
check), `RaceProfile.can_use_divine_arts` (currently `true` for `elf` only), and the
`divine_sexual_mastery`/`reincarnation_boon_yuna` blanket-unlock skills, already recategorised into
`SkillCategory.SEXUAL_ACT`/`group="精通"` in `world/skills/registry.py`. A divine-capable character
today has nothing to cast on this line beyond the generic entry-level `divine_sexual_arts` skill — the
seven acts `docs/superpowers/specs/2026-08-15-divine-sexual-arts-design.md` (the "design doc" below)
specifies do not exist yet.

This proposal fills the three acts the design doc calls `C7a`: 絕頂律令, 時姦, and 神域搾取, described
there as "reusing existing mechanisms" with "no new `SexualState` surface at all." That is true of
`SexualState` itself — every mutator these three acts need already exists
(`stage_climax_extension(count)`, the `entity.traits` MP/SP/HP surface). It does not extend to the
layer above `SexualState`: `_act_family()`'s fixed row shape can only ever attach the
`pleasure:`/`sexual_counter:`/`sexual_event:` effect triad to a `SkillDef`, computed by the one shared
sensitivity/shame/ratio formula, and none of the three acts wants that formula. Each one either
bypasses it entirely (時姦, 神域搾取) or needs to set the gauge outright rather than add to it, in a way
that also has to walk the `climax_phase` cycle further in one action than any ordinary act ever does
(絕頂律令 — see design.md D-2 for why the obvious approach of emitting the already-shipped
`extreme_stimulus_applied` rulebook event does not actually reach 進行中 within the same cast). All
three acts are therefore hand-built directly in `divine.py` rather than through `_act_family()`, each
adding one new, general-purpose (not divine-only) effect prefix to `action.py`'s dispatch table. See
design.md D-1 through D-4.

## What Changes

- Add three acts to `world/skills/sexual_acts/divine.py`'s `DIVINE_ACTS` tuple, each hand-built as a
  `(SkillDef, SexualActDef)` pair (not via `_act_family()`) and registered exactly as `_act_family()`
  output would be — `world/skills/sexual_acts/__init__.py`'s `_register_rows()` treats every pair
  identically regardless of how it was constructed. Every one declares `requires_divine_arts=True`,
  `unlock={}` (counter thresholds do not apply to this line — design doc §1.1), `target_part=None`
  (神之秘法 is one of `_builder.py`'s two `_PARLESS_LINES`, and `test_registry_structure.py`'s
  `check_external_acts_declare_a_target_part` already exempts this line by name), `resistible=True`
  (ordinary hostile-act convention — see design.md D-6 for why this line's "breaks a balancing
  mechanism" framing does not extend to resist for these three; that is 絕對從屬's job in the
  follow-on `C7b`), `actor_counters=()`, `participant_counters=()` (no counter tracks this line):
  - **絕頂律令** (`TargetSpec.AREA`): declares one new effect, `divine_pleasure_max:絕頂律令`. Its
    handler applies to every target (never the actor) two sequential calls to the already-shipped,
    already-tested `_apply_pleasure_gain(target, gain)` — first `gain=100` (sets `pleasure` to its
    ceiling, clamped, regardless of starting value), then `gain=0` (a second pass through the same
    function's climax-phase check, which now observes the first call's already-updated
    `climax_phase`). Two calls, not one, because `_apply_pleasure_gain` deliberately advances
    `climax_phase` by at most one cycle edge per call — see design.md D-2 for why this act needs both
    edges (未達→接近 and 接近→進行中, or 餘韻→接近 and 接近→進行中) walked in the same action, and why
    that is a disclosed, deliberate third exemption this act demonstrates, not a bug. No `pleasure:`
    effect is declared for the actor — nothing in this act's effects list ever touches the caster.
  - **時姦** (`TargetSpec.SINGLE`): declares one new effect, `divine_climax_extension_stage:3`. Its
    handler applies to every other participant (never the actor) one call to
    `SexualState.stage_climax_extension(count)`, parsing `count` from the effect string. `count=3`
    stages three consecutive climax extensions in one cast, so a target already in 進行中 climaxes
    three times from one caster action instead of the ordinary one-extension-per-caster-action trade.
    A target not currently in 進行中 stages a `pending_climax_extension` value that the already-shipped
    `climax_settlement_action()` silently discards at the next settlement point — unchanged shipped
    behaviour, disclosed in design.md D-5 rather than special-cased, since 時姦 is framed by the design
    doc as amplifying an in-progress suppression fight, not starting one.
  - **神域搾取** (`TargetSpec.SINGLE`): declares one new effect, `divine_drain:神域搾取`. Its handler
    reads the single target's current `pleasure.value`, adds that amount to the caster's `mp`, `sp`,
    and `hp` (each independently clamped at that trait's own maximum — the trait's existing bound
    enforcement, no new clamping logic), then sets the target's `pleasure` to `0`. One-to-one, unlike
    the catalogue's own 搾取 (deferred by `sexual-catalog-combat`/C5, and bounded by a ratio that act
    never got to define). No `pleasure:` effect is declared for either participant — the target's
    gauge moves only through the drain.
- **Registers three new effect prefixes in `action.py`'s `_EFFECT_HANDLERS` table**:
  `divine_pleasure_max:`, `divine_climax_extension_stage:`, and `divine_drain:`, plus their typed
  `effects.py` dataclasses (`DivinePleasureMaxEffect`, `ClimaxExtensionStageEffect`,
  `SexualDrainEffect`). Each is a general dispatch-table entry usable by any future `SkillDef` that
  names it, matching how every other prefix in that table is already line-agnostic — nothing about
  the handler implementations reads `requires_divine_arts` or checks the caller's line.
- **Amends the design doc's stated Scope** (`divine.py`, `sexual_state.py`, `sexual.yaml`) to add
  `world/rules/action.py` and `world/skills/effects.py`. Neither `_builder.py` nor `sexual.yaml` needs
  a change: see design.md D-1 for why the three-effect-prefix approach needed no `_act_family()`
  relaxation, once 絕頂律令 was redesigned in D-2 to not go through `sexual_events` at all. The design
  doc itself authorizes such amendments: "the design document wins unless a change amends it
  explicitly" (§3, 無垢回歸).

- **Every handler explicitly filters the acting entity out of the entities it touches**, and every
  handler tolerates an empty or partial `targets` list as an ordinary outcome, never a rejection. Both
  are load-bearing given already-shipped, already-live behaviour discovered during review: `_step4b_
  sexual_resist_gate` (from the already-merged `sexual-resist-cast-wiring` change) rolls a real resist
  contest per non-actor target of every `resistible=True` sexual act and drops resisted targets before
  effect resolution — for 神域搾取's `TargetSpec.SINGLE`, a successful resist legitimately empties
  `targets` before this proposal's handler ever runs, which must be a no-op, not a rejection; and
  `TargetSpec.AREA`'s `"all"` shorthand has no self-exclusion, so 絕頂律令's actor-safety needs an
  explicit filter rather than relying on the resolver. See design.md D-1/D-6.

## Capabilities

### New Capabilities
- `sexual-catalog-divine-core`: the three `C7a` 神之秘法 acts and the three new effect prefixes'
  handlers.

### Modified Capabilities
- `sexual-act-registry`: "the six line modules ship pre-declared and pre-imported; 異種 and 神之秘法
  remain empty" loses its "remain empty" claim for 神之秘法 — this proposal is what fills it. (異種 was
  already filled by the already-implemented `sexual-catalog-interspecies`, which left this requirement's
  text unaddressed at the time; this proposal is the one that finally makes the clause untrue for both
  named lines and updates it.) Every other requirement this capability defines (the `_PARLESS_LINES`
  rule, the forbidden-`sexual_events` rule, ...) is exercised, not changed — this proposal's three acts
  comply with all of them despite bypassing `_act_family()` itself.

## Impact

- Code: `world/skills/sexual_acts/divine.py` (fills `DIVINE_ACTS`); `world/skills/effects.py` (three
  new frozen dataclasses); `world/rules/action.py` (three new handler functions plus their
  `_EFFECT_HANDLERS` registrations); a new test module,
  `world/skills/sexual_acts/tests/test_divine_core_catalog.py`; one existing test updated,
  `world/skills/sexual_acts/tests/test_registry_structure.py::test_every_line_module_is_importable_
  with_only_divine_empty` (its `DIVINE_ACTS == ()` assertion becomes false by design — see design.md's
  Migration Plan).
- No change to `world/skills/sexual_acts/_builder.py`, `world/rules/sexual_state.py`, or
  `world/rules/rulebook/sexual.yaml` — every `SexualState` mutator and every rulebook row already
  exists; this proposal only adds callers, and 絕頂律令 specifically does not call into
  `sexual.yaml`'s `extreme_stimulus_applied` rule at all (design.md D-2).
- No change to `world/rules/sexual_resist.py`, `world/lore/races.py`, or `world/skills/registry.py` —
  the divine-arts gate, race gate, and the three already-shipped skills in this line are exercised, not
  changed.
- Deferred to `C7b` (a separate proposal): 感度創世, 恥辱剝奪, 絕對從屬, 無垢回歸 — the four acts
  needing a new named `SexualState` mutator each, including the one that actually breaks resist
  (絕對從屬) and the one that touches a live shipped requirement (無垢回歸).
