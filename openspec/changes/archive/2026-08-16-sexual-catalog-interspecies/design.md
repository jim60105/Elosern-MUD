## Context

`world/skills/sexual_acts/interspecies.py` currently reads:

```python
INTERSPECIES_ACTS: tuple[tuple[SkillDef, SexualActDef], ...] = ()
```

`sexual-act-seeds` deliberately shipped it pre-declared and empty so this proposal would own exactly
this one file with no seed row to preserve compatibility with — unlike every other line module, there
is no existing `INTERSPECIES_ACTS` shape to match, only `_builder.py`'s structural rules.

`sexual-act-catalog-design.md` §6 specifies seven 異種線 acts total, all targeting a `Monster`. Unlike
every prior catalog proposal in this batch, this one ships its full source-catalog allotment — no
acts are deferred for schema reasons. The one carried-forward concern (D-4) is a disclosed behavior
gap in already-merged infrastructure, not a missing act.

This document applies two corrections from this batch's own review history rather than repeating
either mistake: `sexual-catalog-partner`'s D-4 (no fixed `base_pleasure`/`ratio` choice can guarantee
non-dominance across *different* body parts, only same-part+same-tier pairs are provable) and
`sexual-catalog-combat`'s D-3 fix (a ratio difference framed as a "cost more" guarantee across
different body parts is false unless it's actually checked against the worst case, not just
asserted).

## Goals / Non-Goals

**Goals:**
- Ship all seven 異種線 acts across Tiers 1-4, each a plain `SexualActDef`/`SkillDef` pair through
  `_act_family("異種", ...)`.
- Satisfy `_builder.py`'s `_PARLESS_LINES` invariant: every act declares `target_part=None`, letting
  `resolve_part`'s `Monster` collapse to `GENERIC_BODY_PART` do the work it already does for every
  other line's monster targets.
- Keep every act's `unlock` gate readable directly off `hostile_act_count`, `climax_count`, or
  `interspecies_act_count` — three counters already wired by prior proposals.
- Preserve `sexual-catalog-combat`'s asymmetric counter-crediting convention
  (`actor_counters=("interspecies_act_count",)`, `participant_counters=()`) for all seven acts — a
  `Monster` target is never credited a lifetime counter, matching how a hostile target is never
  credited `hostile_act_count` in the combat line.
- Leave `world/rules/action.py`, `_builder.py`, `__init__.py`, and every other line module
  byte-for-byte unchanged.

**Non-Goals:**
- Fixing `_handle_sexual_event`'s target-only application (D-4) — named, disclosed, and left for a
  future proposal, exactly as `sexual-catalog-partner` (C4) already established for the identical gap.
- Building any Monster-specific anatomy or per-species variation. `sexual-act-catalog-design.md` §6 is
  explicit that this line's identity comes from monsters' mechanical properties (shame permanently
  clamped to `無`, no affinity record), not their anatomy — the `GENERIC_BODY_PART` collapse already
  in `resolve_part` handles this for free, and this proposal adds no code to work around or extend it.
- Reworking `base_pleasure`/ratio tuning system-wide.

## Decisions

### D-1: The seven acts, exactly as registered

| Key | Label | Tier | Unlock | Actor part | Base | Ratio |
|---|---|---|---|---|---|---|
| `interspecies_touch` | 觸碰異種 | 1 | `hostile_act_count: 10` | 腰腹 | 12 | 0.5 |
| `interspecies_caress` | 異種愛撫 | 1 | `hostile_act_count: 10` | 私處 | 14 | 0.6 |
| `interspecies_entangle` | 異種纏繞 | 2 | `hostile_act_count: 30` | 腰腹 | 18 | 0.7 |
| `interspecies_receive` | 承受異種 | 2 | `hostile_act_count: 30` | 私處 | 18 | 0.9 |
| `interspecies_mating` | 異種交合 | 3 | `hostile:30, climax:20` | 私處 | 26 | 0.7 |
| `interspecies_domination` | 異種支配 | 4 | `interspecies_act_count: 20` | 大腿 | 22 | 0.6 |
| `interspecies_resonance` | 異種共鳴 | 4 | `interspecies_act_count: 20` | 乳房 | 22 | 0.6 |

Every act declares `target_spec=TargetSpec.SINGLE`, `target_part=None`,
`actor_counters=("interspecies_act_count",)`, `participant_counters=()`, `resistible=True`.
`interspecies_mating` alone declares `sexual_events=("sexual_activity_with_nonhuman",)`; every other
act declares `sexual_events=()`.

Body parts repeat across tiers by design, following the pattern `sexual-catalog-combat`'s D-3
explicitly disclosed for its own line: 腰腹 appears at Tier 1 (`interspecies_touch`) and again at
Tier 2 (`interspecies_entangle`); 私處 appears at Tier 1 (`interspecies_caress`), Tier 2
(`interspecies_receive`), and Tier 3 (`interspecies_mating`) — a three-link chain, the same length as
`sexual-catalog-combat`'s 私處 chain.

Unlike a same-tier, different-part pair (D-2), two acts on the *identical* body part are directly
comparable for any given actor: `sensitivity`, `shame`, and `crowd_mult` are all identical between
two `TargetSpec.SINGLE` acts cast by the same actor against the same target in immediate succession,
so only `base_pleasure × actor_pleasure_ratio` differs. An earlier draft of this table left
`interspecies_mating` at `base_pleasure=20`, `ratio=0.7` — `20×0.7=14.0`, *below*
`interspecies_receive`'s `18×0.9=16.2` — making the harder-to-unlock, compound-gated capstone act
deliver strictly less actor-side pleasure than the easier act one tier below it on the same part, the
opposite of intentional progression. This was caught in review and corrected: `interspecies_mating`
now declares `base_pleasure=26`, giving `26×0.7=18.2`, ahead of `interspecies_receive`'s `16.2` by a
margin (`2.0`, in `base×ratio` units) large enough to survive `round()` at every multiplier
combination the live tables can produce — the smallest common multiplier is
`1.0×0.65×1.1=0.715` (`普通` sensitivity, `強烈` shame, two-participant `crowd`), and `2.0×0.715=1.43`
exceeds the maximum single-value rounding error (`0.5`), so the ordering is provably preserved after
rounding, not merely true before it. 觸碰異種→異種纏繞 (腰腹, base `12→18`, ratio held at the tier's
own value) has no ratio drop to check against, so its ordering was never at risk.

### D-2: No same-body-part, same-tier pair exists; no cross-body-part cost/value ordering is claimed as a guarantee

Tier 2's two acts (`interspecies_entangle` 腰腹, `interspecies_receive` 私處) and Tier 4's two acts
(`interspecies_domination` 大腿, `interspecies_resonance` 乳房) are this proposal's only same-tier
pairs, and each pair uses two different body parts. Per `sexual-catalog-partner`'s D-4 and
`sexual-catalog-combat`'s corrected D-3, this proposal makes no claim that one act in either pair
costs the actor more, grants more, or is otherwise "worse"/"better" than its sibling for a given
character — that relationship depends on the character's independently-trained per-part sensitivity
(§1.1) and is not something a fixed `base_pleasure`/`ratio` choice can pin down. `interspecies_
domination` and `interspecies_resonance` share identical `base_pleasure` and `ratio` values
specifically so this document does not need to construct — and then have to defend — a cost-ordering
narrative between them the way `sexual-catalog-combat`'s original D-3 mistakenly did.

### D-3: 承受異種's actor_pleasure_ratio=0.9 is the highest one-way ratio in the catalog so far

The source catalog names 承受異種 as carrying "the highest actor ratio in the catalog." Surveying
every one-way (actor receives less than or equal to the target's fixed `1.0` ratio) act shipped by
this batch's prior proposals: `sexual-catalog-partner`'s highest is `0.6` (`partner_anal_sex`),
`sexual-catalog-combat`'s highest is `0.6` (`combat_relentless_torment`), `sexual-catalog-shame`'s
highest AREA/two-party ratio is `0.6` (`shame_public_performance`). `0.9` exceeds all three. This
comparison excludes `sexual-catalog-partner`'s `partner_mutual_masturbation`
(`actor_pleasure_ratio=1.0`), a deliberately different narrative category: a *mutual* act where the
target's ratio is also `1.0`, not a one-way act where the actor alone receives an unusually large
share. `interspecies_receive`'s `0.9` remains below that one mutual-category outlier while exceeding
every one-way act shipped so far, matching the source catalog's framing without overstating it.

### D-4: 異種交合 ships despite `_handle_sexual_event`'s target-only event application — a more consequential instance of the gap sexual-catalog-partner (C4) already disclosed

`_handle_sexual_event` (`world/rules/action.py`) loops over its raw `targets` parameter rather than
`participants(actor, targets)`, so a declared `sexual_events` entry never reaches the actor of a
`TargetSpec.SINGLE` act — only whoever was chosen as the target. `sexual-catalog-partner` (C4)
disclosed this for 乳交 (D-3): casting it credits `breast_sex_performed`'s `乳交` experience type to
the human partner, not the actor.

異種交合 inherits the identical mechanism, but with a more consequential result: casting it against a
`Monster` target means `sexual_activity_with_nonhuman` fires on the **Monster**, not the actor. The
intended effect — crediting the *player's* `experience_types` with `異種性愛` — never happens under
the currently-shipped handler; the event instead lands on a transient combat entity whose
`experience_types` set is not read, displayed, or persisted meaningfully by anything else in the
shipped system. Unlike 乳交's case (where at least a human partner receives partial, if
asymmetric, credit), 異種交合's intended recipient receives none.

This proposal ships 異種交合 anyway, for the same reasoning C4 gave for 乳交: its
`pleasure:interspecies_mating` and `sexual_counter:interspecies_mating` effects are correctly
participant-expanded (both handlers already call `participants()`) and deliver full value
independent of this gap, and 異種交合 is the catalog's sole planned emitter of
`sexual_activity_with_nonhuman` — deferring it would leave that rule unemitted indefinitely with no
compensating benefit, exactly as deferring 乳交 would have left `breast_sex_performed` unemitted. This
proposal does not attempt to fix `_handle_sexual_event` itself — that file belongs to the already-merged
`sexual-act-effects` (B5), and C4 already established that fixing it is a future proposal's job, one
that would now resolve this gap for both 乳交 and 異種交合 in a single change.

### D-5: Dependency-surface assumptions this proposal reads, not writes

- `sexual-counters` (B2, merged): `hostile_act_count`, `interspecies_act_count`, and their sole
  mutators (`record_hostile_act`, `record_interspecies_act`) are unchanged.
- `climax_count` is credited exclusively by the climax-settlement clock's own mutator call, never by
  an act's `actor_counters` — Tier 3's compound gate reads it but no act in this proposal writes it
  directly, matching the pattern every prior catalog proposal established.
- `resolve_part` (`sexual_act_effects.py`): a `Monster` target collapses to `GENERIC_BODY_PART`
  regardless of the declared `target_part`, and `_act_family()`'s `_PARLESS_LINES` check already
  forbids 異種 acts from declaring one — this proposal's `target_part=None` on all seven rows is the
  only value the structural check allows.
- `world/rules/rulebook/sexual.yaml`'s `experience_interspecies_added` row
  (`when: {event: sexual_activity_with_nonhuman} → then: {field: experience_types, add: 異種性愛}`)
  is unchanged and already shipped; this proposal adds no new rulebook row.
- `Monster`'s `shame` field is permanently clamped to `無` (×1.0) and it carries no affinity record —
  both are properties of the already-merged `Monster` typeclass and `sexual-resist-contest`, not
  something this proposal depends on beyond `resolve_part`'s collapse behavior.

### D-6: Target identity is narrative, not mechanically enforced

The source catalog's "targets must be a `Monster`" is framing, not a claim this
proposal (or any proposal in this batch) mechanically enforces: the shipped
targeting pipeline's only sex-act-specific rule is the SELF-target exclusion in
`targeting.py`, and a `TargetSpec.SINGLE` act accepts any co-located living
non-self entity. A 異種 act cast at a humanoid therefore resolves that target to
`GENERIC_BODY_PART` (the `None` collapse is unconditional in `resolve_part`) and
applies the target-side effects there. The delta spec's scenarios are written
only about `Monster` targets — the generic-channel collapse — and make no
rejection claim, so the implementation matches the contract exactly. Enforcing
target-kind would require a targeting or skill-contract change that no proposal
in the batch owns; the partner line ships under the identical precedent (its
"partner" identity is equally unenforced), and a future proposal that adds
enforcement would fix every line at once.

## Risks / Trade-offs

- **[Risk]** 異種交合's event never reaches its intended recipient under the currently-shipped
  `_handle_sexual_event` (D-4) — a player casting it will never see `異種性愛` appear in their own
  `experience_types`, which may read as a silent failure rather than a known limitation. →
  **Mitigation:** named loudly in proposal.md's "What Changes" and here, not buried; a future fix to
  `_handle_sexual_event` (already motivated by C4's 乳交) resolves both acts at once.
- **[Risk]** All seven acts credit only `interspecies_act_count` on the actor, never
  `hostile_act_count` — a player farming this line exclusively never advances the 戰鬥線's own
  counter, even though Tiers 1-3 of this line are themselves gated on `hostile_act_count`. →
  **Mitigation:** this is intentional separation of ledgers, matching how `sexual-catalog-combat`'s
  acts credit only `hostile_act_count` and never `interspecies_act_count` — each line trains its own
  counter; cross-crediting was never part of either line's design and would blur what each counter
  measures.
- **[Risk]** `interspecies_receive`'s `0.9` ratio is close to `1.0`'s structural ceiling in practice
  (no upper bound is enforced by `_builder.py`, but every other one-way act stays at `0.6` or below),
  making it an outlier that could read as miscalibrated rather than deliberate. →
  **Mitigation:** D-3
  states explicitly why `0.9` is the intended value, sourced from the catalog design document's own
  "highest actor ratio in the game" framing for this specific act, not an arbitrary choice.
- **[Risk]** When `sexual-resist-cast-wiring` merges, every `resistible=True` cast runs a d100
  contest, and this proposal's two target-side-asserting cast tests
  (`test_cast_against_a_monster_applies_pleasure_through_the_generic_channel`,
  `test_mating_cast_emits_the_nonhuman_event`) become RNG-dependent: a monster has no affinity
  record, so its resist is a pure stat contest that can never auto-comply (resolution design §4.2),
  and a successful resist excludes the target from the act's pleasure/event effects. →
  **Mitigation:** this proposal is explicitly sequenced before that follow-up (overview §4.3 batch 9
  is unscheduled), and the wiring change already owns the migration of resistible cast tests under
  its own task 4.1-4.2 (`patch("world.rules.action.roll_d100", return_value=...)`) and re-runs the
  full `world.skills.tests` at its task 5.1; its sweep must extend to this proposal's two tests the
  same way it does to `test_seed_acts.py`. No `world.rules.action.roll_d100` seam exists to patch
  today, so no pre-patch is possible from this proposal.
## Migration Plan

Pure content addition; no data migration. `INTERSPECIES_ACTS` grows from an empty tuple to 7 rows;
every existing consumer (`SEXUAL_ACT_REGISTRY`, `unlocked_act_keys_for`, the combat panel's category
grouping) reads the tuple structurally and requires no change.

## Open Questions

None.
