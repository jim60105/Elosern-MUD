## Why

`world/skills/sexual_acts/interspecies.py` ships pre-declared and empty — `sexual-act-seeds` created
the module with an empty `INTERSPECIES_ACTS` tuple specifically so this proposal would own exactly
this one file, per the original batch-sequencing plan. No 異種線 content exists yet: a character with
any amount of `hostile_act_count` or `interspecies_act_count` has nothing to unlock on this line.

This proposal fills all seven acts the source catalog specifies for 異種線: two at
`hostile_act_count >= 10`, two at `hostile_act_count >= 30`, one at `hostile_act_count >= 30`
(compound-gated on `climax_count` too), and two at `interspecies_act_count >= 20` — the full line, no
deferrals of content. It carries forward one disclosed, non-blocking gap from `sexual-catalog-partner`
(C4): 異種交合's declared event currently lands on the wrong participant, for the same reason 乳交's
does.

## What Changes

- Add seven acts to `world/skills/sexual_acts/interspecies.py`'s `INTERSPECIES_ACTS` tuple, every one
  `TargetSpec.SINGLE`, `resistible=True`, `target_part=None` (異種線 is one of `_builder.py`'s two
  `_PARLESS_LINES` — no act on this line may declare a target part; the target always resolves to
  `GENERIC_BODY_PART` via `resolve_part`'s `Monster` collapse), `actor_counters=
  ("interspecies_act_count",)`, `participant_counters=()` (a `Monster` target is never credited a
  counter, matching the asymmetric crediting `sexual-catalog-combat` established for hostile targets):
  - **Tier 1** (`unlock={"hostile_act_count": 10}`): 觸碰異種 (actor part 腰腹) and 異種愛撫 (actor
    part 私處).
  - **Tier 2** (`unlock={"hostile_act_count": 30}`): 異種纏繞 (actor part 腰腹) and 承受異種 (actor
    part 私處, `actor_pleasure_ratio=0.9` — the highest one-way actor ratio shipped in the catalog so
    far, delivering the source catalog's "highest actor ratio in the game" note for this line; see
    design.md D-3 for how this compares against the highest ratios every other catalog proposal has
    shipped).
  - **Tier 3** (`unlock={"hostile_act_count": 30, "climax_count": 20}`): 異種交合 (actor part 私處,
    `sexual_events=("sexual_activity_with_nonhuman",)` — the sole planned emitter of this event,
    unemitted since the transition rulebook landed).
  - **Tier 4** (`unlock={"interspecies_act_count": 20}`): 異種支配 (actor part 大腿) and 異種共鳴
    (actor part 乳房).
- **Ships 異種交合 with a disclosed, non-blocking event-recipient gap, inherited from and compounding
  `sexual-catalog-partner`'s D-3**: `_handle_sexual_event` applies a declared `sexual_events` entry
  to the resolver's raw `targets` list, not `participants(actor, targets)` — for 異種交合, the
  `targets` list is `[the Monster]`, so `sexual_activity_with_nonhuman` currently fires on the
  Monster, never on the actor. This is a more consequential instance of the same gap 乳交 (C4)
  disclosed: for 乳交 the event at least reaches a meaningful human participant; here it reaches only
  a `Monster`, whose `experience_types` set is never read by anything else in the shipped system.
  This proposal ships the act anyway — its pleasure and counter effects are correctly
  participant-expanded and deliver full value independent of this gap — and does not attempt to fix
  `_handle_sexual_event` itself, matching C4's disclosed-not-fixed precedent; see design.md D-4.
- **Target identity is narrative, not mechanically enforced (design.md D-6)**: `TargetSpec.SINGLE`
  accepts any co-located living non-self entity, so nothing stops a 異種 act from being cast at a
  humanoid (which then resolves to `GENERIC_BODY_PART` like any parless target). No proposal in the
  batch enforces target-kind; the partner line ships under the identical precedent, and the delta
  spec's scenarios make no rejection claim.

## Capabilities

### New Capabilities
- `sexual-catalog-interspecies`: the seven Tier 1-4 異種線 acts and their counter-based unlock
  thresholds.

### Modified Capabilities
- none — `sexual-act-registry` and `sexual-act-effects`'s existing requirements (including
  `resolve_part`'s `Monster`-collapse behavior and `_PARLESS_LINES`' target-part prohibition) are
  exercised, not changed.

## Impact

- Code: `world/skills/sexual_acts/interspecies.py` only, plus a new test module,
  `world/skills/sexual_acts/tests/test_interspecies_catalog.py`.
- No change to `_builder.py`, `__init__.py`, any other line module, `world/rules/action.py`, or
  `world/rules/rulebook/sexual.yaml` — `sexual_activity_with_nonhuman`'s rule row already exists and
  is unchanged by this proposal.
- No content deferrals: all seven acts the source catalog specifies for this line ship in this
  proposal. The only carried-forward gap is 異種交合's event-recipient asymmetry (design.md D-4),
  which is a behavior gap in already-merged shared code, not a missing act.
