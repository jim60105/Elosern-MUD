## Context

`sexual-act-registry` shipped `SexualActDef`, `_act_family()`, `SEXUAL_ACT_REGISTRY`, the
`SexualState.unlocked_act_keys()` query, and `SkillHandler.owned_keys()` integration — with all six
line modules exporting empty tuples. `sexual-act-effects` shipped the `pleasure:`/`sexual_counter:`
effect handlers, `resolve_part()`, `participants()`, `compute_pleasure_gain()`, and the explicit
counter-mutator table — again against zero registered acts, proven only by one synthetic act
installed and torn down inside `world/skills/sexual_acts/tests/test_acceptance.py`.

Both landed changes disclosed the same gap, in `sexual-act-effects`'s design.md: with zero acts
registered, several risks stay unreachable, including "Exposure- and shame-raising acts... cannot be
expressed through this proposal's mechanisms at all" and "An act declaring a part-requiring event
(`frequent_stimulation`) cast through the ordinary player command path fails at commit, because
nothing in the shipped cast path supplies the recipient's body part as event context." This proposal
is the first to actually register acts, so it is the first proposal that must resolve — or explicitly
continue deferring — each of those disclosed gaps.

This document is written directly against the landed contract in
`openspec/specs/sexual-act-registry/spec.md` and `openspec/specs/sexual-act-effects/spec.md`, not
against the original prose design set (`docs/superpowers/specs/2026-08-15-*.md`), which predates
several implementation-time corrections (English counter attribute names rather than the design set's
Chinese mnemonics, the exact `_act_family()` row-tuple shape, and the disclosed gaps above).

## Goals / Non-Goals

**Goals:**
- Register the seven `unlock={}` seed acts the design set calls for, one per targeting shape, so
  every line except 異種 and 神之秘法 has an always-available entry point before any catalog proposal
  lands.
- Add the one `sexual.yaml` rule row a shame-line act needs to move its own `exposure` field, since no
  existing rule expresses that and the gap was explicitly disclosed as "the next proposal's job."
- Prove the full pipeline — ownership, no-threshold availability, cast, pleasure gain, counter
  increment, EventLog — against real (not synthetic, not torn-down) content for the first time.

**Non-Goals:**
- The remaining 55 catalog acts (`sexual-catalog-solo` through `sexual-catalog-interspecies`,
  `divine-sexual-arts-reuse`/`-mutators`) — this proposal ships seeds only.
- Sensitivity training via `frequent_stimulation`. That event requires per-recipient body-part event
  context that no cast path currently supplies (`sexual-act-effects`'s disclosed risk, unchanged
  here). None of this proposal's seven acts declare it. A future proposal that lands the
  `cast_settlement.py`/`commands/action.py` plumbing is required before any act can use it.
- `docs/game/commands.md`/`command-reference.md` updates. Documenting seven acts now and revising the
  same section nine more times as each catalog proposal lands is worse than documenting the completed
  catalog once, in `sexual-act-docs`.
- Wiring `resistible` to an actual resist contest. `sexual-resist-turn-cost` (`B6b`) is proposed but
  not yet implemented; `resistible` is declared here as honest data (matching each act's real
  targeting shape) with no consumer yet, exactly as `sexual-act-registry` declared the field with no
  consumer.
- Extending `BODY_PARTS`. `sexual-body-parts` (`C1`) is archived; adding a part is that capability's
  territory and is out of scope here even though one seed's flavor would benefit from one (D-4).

## Decisions

### D-1: The seven seed rows

| Key | Label | Line | Target | Part(s) | `base_pleasure` | `actor_pleasure_ratio` | Counters | Events | Resistible |
|---|---|---|---|---|---|---|---|---|---|
| `solo_self_touch` | 自撫 | 獨處 | SELF | 私處 / — | 12 | 1.0 | actor: `masturbation_count` | `masturbation_climax` | No |
| `solo_fondle_breasts` | 揉捏胸部 | 獨處 | SELF | 乳房 / — | 9 | 1.0 | actor: `masturbation_count` | — | No |
| `solo_thigh_rub` | 摩擦大腿 | 獨處 | SELF | 大腿 / — | 8 | 1.0 | actor: `masturbation_count` | — | No |
| `shame_hem_lift` | 撩起衣襬 | 羞恥 | SELF | — / — | 6 | 1.0 | actor: `exposure_act_count` | `self_exposure` | No |
| `partner_caress` | 愛撫 | 關係 | SINGLE | 腰腹 / 腰腹 | 10 | 0.5 | both: `duo_act_count` | — | Yes |
| `partner_hand_hold` | 牽手交纏 | 關係 | SINGLE | 腰腹 / 腰腹 | 3 | 0.5 | both: `duo_act_count` | — | Yes |
| `combat_tease` | 挑逗 | 戰鬥 | SINGLE | 腰腹 / 腰腹 | 7 | 0.4 | actor: `hostile_act_count` | — | Yes |

All seven declare `unlock={}` — always available from `SkillHandler.owned_keys()` regardless of
counter state, per `sexual-act-registry`'s existing `unlocked_act_keys_for()` contract (an act with
an empty mapping trivially satisfies `all(... for counter, threshold in act.unlock.items())` over an
empty iterable).

The three `SINGLE`-target seeds (`partner_caress`, `partner_hand_hold`, `combat_tease`) each
automatically receive `sexual_act_effects.yaml`'s existing two-participant multiplier (`"2": 1.1`) on
both sides' gain, which the four `SELF`-target seeds (single-participant, `"1": 1.0`) never do. This
proposal's hand-picked `base_pleasure` values were not adjusted to compensate — the ladder is a
pre-existing, deliberately-shipped balance table intended to reward partnered/group play in general,
so a partnered seed reading 10% stronger than an equivalently-labelled solo magnitude is accepted as
correct, not an oversight.

Every `actor_pleasure_ratio` is strictly positive, required by `_act_family()`'s existing structural
check for any family not passing `requires_divine_arts=True` (`sexual-act-registry`'s own invariant,
re-verified here against real rows rather than a hypothetical one).

### D-2: `exposure_up_on_self_exposure`, the one new rulebook row

```yaml
- id: exposure_up_on_self_exposure
  when: {event: self_exposure}
  then: {field: exposure, delta: "+1"}
```

`exposure` is already an `OrderedLevelTrait` `FIELD_KINDS` entry (via the existing
`clothing_damaged_in_combat` row), so this needs no `FIELD_KINDS` change — only the new rule row and
its structurally-required `test_rule_exposure_up_on_self_exposure` in
`world/rules/tests/test_sexual_transitions.py` (`sexual-transition-rulebook`'s existing
`test_every_rule_id_has_a_test()` check enforces this pairing; skipping it fails that test, not a new
one written for this change).

This event is deliberately generic (`self_exposure`, not `hem_lifted` or similar) so
`sexual-catalog-shame`'s remaining nine acts — 半露出, 全露出, 公開自慰, 獻身姿態, 無恥宣言, and
others — reuse the identical row with no further rulebook change, matching this document set's
established pattern of one shared event serving an entire tier family (`_act_family()`'s own design
principle, applied one level up to the rulebook).

**Why this fires `shame_up_on_exposure_increase` for free.** `sexual.yaml`'s existing
`shame_up_on_exposure_increase` rule (`{field_changed: exposure, direction: up}` → `{field: shame,
delta: "+1"}`) is unconditional on cause — it fires whenever `exposure`'s ordinal rises during any
`apply_event()` call, regardless of which event triggered the rise. Because
`sexual_event:self_exposure` routes through the ordinary `apply_event()` cascade (not the
direct-write path `pleasure:`/`sexual_counter:` effects use), the shame bump the catalog design
document's growth arc depends on ("early exposure acts raise shame... a trough that must be pushed
through") is already correct with zero additional code — this proposal only needed to make `exposure`
movable by an act at all.

### D-3: Shame-line acts declare `actor_part=None`

`撩起衣襬` declares `actor_part=None`. Per `resolve_part()`'s existing, unconditional contract
(`sexual-act-effects` D-3/§implementation), `None` collapses to `GENERIC_BODY_PART` regardless of
whether the entity is a `Monster` — and `_sensitivity_level()` then reads that channel's sensitivity
(default `普通`, ×1.0) for the pleasure formula. This is the correct behaviour, not a workaround:
exposing oneself is a state of dress, not a stimulation of one erogenous zone, so training a specific
body part's sensitivity from it would be a category error. `sexual-act-registry`'s structural
invariant forbidding `GENERIC_BODY_PART` as a *declared* value (as opposed to a `None`-triggered
runtime collapse) is unaffected — this act never names the constant itself.

This is exempt from the "non-`None` `target_part`" requirement because the act's `target_spec` is
`SELF`, which that requirement explicitly excludes.

### D-4: `partner_hand_hold` reuses `腰腹` for both parts — a disclosed compromise

`牽手交纏` (hand-holding) has no natural home in `BODY_PARTS`
(口唇/頸項/耳朵/乳房/腰腹/臀部/大腿/足部/私處/後庭 — no hand-adjacent entry), and its `target_spec`
is `SINGLE`, so `sexual-act-registry`'s existing structural requirement ("every act outside 異種/
神之秘法 targeting another entity declares a non-null `target_part`") forces a real member of
`BODY_PARTS` to be named.

Extending `BODY_PARTS` is `sexual-body-parts`'s territory (archived; out of scope here per Non-Goals).
This proposal instead reuses `腰腹` — the same neutral, low-eroticism part `愛撫` already uses — for
both `actor_part` and `target_part`. The act's `base_pleasure` (3, the lowest of any act in this
proposal) keeps the mechanical consequence of that flavor mismatch negligible: even at maximum
sensitivity (`敏感異常`, ×2.5) the gain stays small. This is disclosed as a known compromise, not
silent, matching this document set's established practice
(`sexual-act-effects`'s own Risks section for the two gaps this proposal resolves or defers).

### D-5: `masturbation_climax` fires only for `自撫`, not for the two flavor-variant seeds

All three solo seeds are mechanically identical (SELF, `masturbation_count` on the actor, no
resistance). Only `自撫` declares `sexual_events=("masturbation_climax",)`; `揉捏胸部` and
`摩擦大腿` declare `sexual_events=()`. `masturbation_climax`'s rule
(`experience_masturbation_added` → adds `自慰` to `experience_types`) is idempotent (a set add), so
firing it from every solo act would not be incorrect — but narrating every act, including a light
thigh-rub, as a completed masturbation climax overclaims. Restricting it to the act most clearly
framed as masturbation is an editorial choice, not a structural requirement; a later catalog proposal
may fire it from additional solo acts freely.

### D-6a: Nothing in the stack restricts `SEXUAL_ACT`-category ownership or casting to humanoid/player entities

`.sexual` and `SkillHandler` are mounted on `LivingEntity`, the shared base class for
`PlayerCharacter`, NPCs, and `Monster` alike. Neither `SkillHandler.owned_keys()` nor
`_act_family()`'s structural checks restrict an `unlock={}` `SEXUAL_ACT` skill to a particular
entity kind, and `resolve_part()` special-cases `Monster` only as a *target*, never as an *actor*.
This means a `Monster` whose behaviour tree ever selects a `SEXUAL_ACT`-category skill could cast one
of these seven seeds on itself, gaining `masturbation_count`/`experience_types` accordingly. This gap
predates this proposal (it lives in the already-merged registry/effects contract) and was previously
unreachable only because the registry shipped zero real content; this proposal is the first to make
it observable. Nothing in `world/rules/monster_behaviour.py`'s existing action-selection policy is
known to exclude `SEXUAL_ACT`-category skills, and confirming or adding that exclusion is out of
scope here — recorded as an inherited, disclosed assumption rather than silently relied upon.

### D-6: `resistible` is set from targeting shape, not from B6b's readiness

All four `TargetSpec.SELF` seeds declare `resistible=False` (there is no second party to resist); all
three `TargetSpec.SINGLE` seeds declare `resistible=True`. This is independent of whether
`sexual-resist-turn-cost` (`B6b`) has landed a consumer — `sexual-act-registry` declared the field
precisely so that act data stays honest ahead of its consumer, and `B6b`'s eventual scan of the
catalog should never need to revisit a seed's `resistible` value.

## Risks / Trade-offs

- **[Risk]** None of these seven acts can train body-part sensitivity, because `frequent_stimulation`
  remains unreachable (Non-Goals). A player using only seed acts sees `sensitivity_multipliers`'
  floor (`普通`, ×1.0) forever. → **Mitigation**: already disclosed by `sexual-act-effects`; this
  proposal changes nothing about that gap's status. `sexual-catalog-solo`'s later, larger act count
  makes landing the cast-path plumbing worthwhile in a proposal actually sized for it — not this one.
  **This is a hard blocking dependency, not a soft preference**: every catalog proposal that follows
  this one (`sexual-catalog-solo` through `divine-sexual-arts-mutators`) will re-encounter the exact
  same gap if it declares `frequent_stimulation` on any act before the cast-path plumbing
  (`cast_settlement.py`/`commands/action.py`) lands. Recording it once, here, is meant to spare each
  of those proposals from independently rediscovering it.
- **[Risk]** `partner_hand_hold`'s reuse of `腰腹` (D-4) is a narrative/mechanical mismatch a careful
  player could notice (hand-holding "training" waist sensitivity). → **Mitigation**: disclosed here;
  the act's floor-low `base_pleasure` (3) makes the mechanical consequence negligible regardless of
  sensitivity level, and the alternative (blocking on a `BODY_PARTS` extension proposal) delays every
  other seed for one flavor detail.
- **[Risk]** Registering real content for the first time is exactly the condition under which a
  latent gap in the shipped structural tests would first surface (they have only ever run against a
  synthetic, torn-down act or an empty registry). → **Mitigation**: this proposal's task list runs
  the full existing structural-test suite (`test_registry_structure.py`) against these seven real
  rows before writing any new test, so a failure here is diagnostic of the registry, not the seeds.
  The change also updates the handful of tests elsewhere that pinned the pre-content state —
  exact `owned_keys()`/`active_keys` lists and the D4 classification table's `SEXUAL_ACT` set —
  because seven unconditionally-owned ACTIVE skills change every entity's `owned_keys()` and the
  assembled registries; those updates are enumerated in tasks 7.5 and in proposal.md's Impact list.
- **[Risk]** Two main-spec requirement headings become factually stale the moment this change lands:
  `sexual-act-registry`'s "each exporting an empty tuple" (four modules now carry rows) and
  `skill-category-registry`'s "117 entries" (seven acts make it 124, and the count will keep
  moving as catalog proposals land). → **Mitigation**: both are declared as RENAMED + MODIFIED
  requirements in this change's delta spec, with the covering tests' `covers_requirement` IDs
  updated to the renamed headings at implementation time (tasks 7.5.1/7.5.9).

## Migration Plan

Additive only — a new `sexual.yaml` row, seven new registry rows, one new test. No existing rule,
effect, or `SexualState`/`PLEASURE_CONFIG`/`EffectsConfig` field changes. Zero released users (per
project convention); no backward-compatibility or data-migration concern applies.

## Open Questions

None. The two gaps this proposal touches (exposure-raising, sensitivity training) are each resolved
or explicitly deferred above, not left ambiguous.
