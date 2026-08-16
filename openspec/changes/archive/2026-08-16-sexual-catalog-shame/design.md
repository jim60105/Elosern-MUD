## Context

`sexual-act-seeds` ships 撩起衣襬 (the sole 羞恥線 seed) and `exposure_up_on_self_exposure` — the one
`sexual.yaml` row needed to move `exposure` from an act at all, since no previously-shipped event
expressed it. Its design.md frames this proposal as the reuse point for that row across the rest of
the line.

This document inherits `sexual-catalog-solo` (C2)'s central finding unchanged: `SexualActDef`/
`_act_family()` can express exactly three things per act — a positive pleasure gain, counter
increments, and `sexual.yaml` event emissions — and nothing else. Three of this line's nine acts
carry a secondary buff/debuff in the source catalog document that this schema cannot express. This
proposal resolves one of the three through reuse of an existing mechanism (D-2) and discloses the
other two as dropped flavour (D-3), following C2's precedent exactly rather than inventing a new
disclosure style.

## Goals / Non-Goals

**Goals:**
- Register the nine remaining 羞恥線 acts, reusing `sexual-act-seeds`'s `self_exposure` event with no
  further rulebook change.
- Resolve 挑釁凝視's "accuracy debuff on enemies" through an already-shipped combat modifier rather
  than dropping it, since a reuse is available and C2 already established the discipline of looking
  for one before disclosing a drop.
- Disclose the two remaining unbuildable secondary effects precisely, matching C2's format.

**Non-Goals:**
- Extending `SexualActDef`/`_builder.py` with a secondary-effect field. Still out of scope for a
  content proposal, per C2's D-2/D-4.
- Any `sexual.yaml` change. Every event this proposal's acts need (`self_exposure`,
  `masturbation_climax`) is already reachable before this proposal lands.
- A "who is actually present in the room" check for `watched_count` crediting. See D-4.

## Decisions

### D-1: The nine rows

| Key | Label | Tier | Target | Unlock | `actor_part`/`target_part` | `base_pleasure` | Ratio | Counters (actor / participant) | Events |
|---|---|---|---|---|---|---|---|---|---|
| `shame_half_expose_chest` | 半露出·胸口 | 1 | SELF | `exposure_act_count: 5` | None / None | 9 | 1.0 | `exposure_act_count` / — | `self_exposure` |
| `shame_half_expose_lower` | 半露出·下身 | 1 | SELF | `exposure_act_count: 5` | None / None | 9 | 1.0 | `exposure_act_count` / — | `self_exposure` |
| `shame_loosen_collar` | 解開衣襟 | 1 | SELF | `exposure_act_count: 5` | None / None | 8 | 1.0 | `exposure_act_count` / — | `self_exposure` |
| `shame_full_expose` | 全露出 | 2 | SELF | `exposure_act_count: 20` | None / None | 16 | 1.0 | `exposure_act_count` / — | `self_exposure` |
| `shame_public_masturbation` | 公開自慰 | 2 | SELF | `exposure_act_count: 20`, `masturbation_count: 25` | None / None | 18 | 1.0 | `exposure_act_count`, `masturbation_count`, `watched_count` / — | `self_exposure`, `masturbation_climax` |
| `shame_provocative_gaze` | 挑釁凝視 | 3 | AREA | `watched_count: 10` | None / 腰腹 | 14 | 0.4 | `hostile_act_count` / — | — |
| `shame_public_performance` | 公開表演 | 3 | AREA | `watched_count: 10`, `exposure_act_count: 20` | None / 腰腹 | 15 | 0.6 | `watched_count`, `exposure_act_count` / — | `self_exposure` |
| `shame_devoted_pose` | 獻身姿態 | 4 | AREA | `exposure_act_count: 50` | None / 腰腹 | 22 | 0.5 | `exposure_act_count` / — | `self_exposure` |
| `shame_shameless_declaration` | 無恥宣言 | 4 | SELF | `exposure_act_count: 50`, `watched_count: 30` | None / None | 20 | 1.0 | `exposure_act_count` / — | `self_exposure` |

Every row declares `participant_counters=()`. For the three `SELF`-target rows in Tiers 1/2/4 this is
structurally required (`sexual-act-registry`'s existing invariant); for the three `AREA` rows it is a
content choice (D-4) — none of the eleven named lifetime counters fits "was in the audience of
someone else's exposure act," so targets of these three acts receive pleasure only, no counter
credit.

`actor_part=None` on every row, inherited from `sexual-act-seeds`'s D-3: exposure is a state of
dress, not a stimulation of one erogenous zone, and this line has held that position from its first
act.

### D-2: 挑釁凝視's "accuracy debuff" is delivered by an already-shipped combat modifier, not dropped

`world/rules/rulebook/combat_modifiers.yaml` already declares:

```yaml
- id: high_arousal_agility_accuracy_penalty
  when: {field: arousal, gte: 高度}
  then: {agility: "-20%", accuracy: -15}
```

`挑釁凝視` is an `AREA`-target act, so `_handle_pleasure_effect`'s existing, unmodified participant
loop (`participants(actor, targets)`, which for an `AREA` cast is the actor plus every resolved
target) applies a pleasure gain to every enemy the cast resolves against, exactly as it does for any
other act. If that gain pushes a target's derived `arousal` level to `高度` or above (the pleasure-
gauge design's own band table: pleasure `>= 60`), the modifier above already fires on that target's
next `accuracy` read — with no new code, no new buff, and no secondary-effect field, because
combat-modifier evaluation is a live, continuous read of `entity.sexual.arousal`, not something an
act "applies" once.

This is not guaranteed on every cast (a target already near `高度` crosses it; a target at `平靜`
with one cast of `挑釁凝視` likely does not), which is a real, disclosed difference from the source
document's framing of "an `accuracy` debuff" as a certain, dedicated effect. It is accepted as the
correct trade-off: the act is themed exactly as "distraction through pleasure," and using the
already-shipped pleasure-to-combat-penalty pipeline is more consistent with this whole design set's
established discipline (reuse over new mechanism, `sexual-act-seeds`'s own governing principle) than
adding a bespoke, unconditional debuff would be. `combat_tease` (`sexual-act-seeds`'s combat-line
seed) already relies on the identical pipeline for the same reason, unstated there because its own
design.md did not need to justify a source-document debuff claim.

### D-3: 獻身姿態 and 無恥宣言 drop their secondary buff/debuff, following C2's precedent exactly

The source document frames 獻身姿態 as trading a self-`defense` penalty for pleasure delivered to
every enemy present, and 無恥宣言 as granting a temporary buff causing `shame` to read as `成癮`
(`×1.6`) for several rounds. Both require a secondary effect `SexualActDef` cannot express
(`sexual-catalog-solo`'s D-4, unchanged: `_act_family()`'s auto-generated `effects` list is exactly
`pleasure:`/`sexual_counter:`/`sexual_event:` entries, nothing else). Unlike 挑釁凝視 (D-2), no
already-shipped mechanism produces an equivalent side effect for either of these — `獻身姿態`'s
self-cost and `無恥宣言`'s temporary multiplier override are both effects nothing in the combat-
modifier table or the pleasure formula happens to already compute. Both acts ship as plain pleasure
acts; the flavour lives in `label`/`description` text only, exactly as C2 shipped `拘束自慰`.

Neither dropped detail creates the strict-dominance problem C2's rubber-duck review found for
`拘束自慰`: 獻身姿態 and 無恥宣言 sit in different tiers from every other act in this proposal (Tier 4
alone, and 無恥宣言 additionally compound-gated on `watched_count`), so there is no same-tier sibling
either one could strictly dominate.

### D-4: watched_count crediting is unconditional, not room-occupancy-checked

The pleasure-model design document defines `watched_count` as incrementing "when any act resolves
with a third party present." Nothing in the landed `_handle_sexual_counter_effect` (or anywhere else
in the effect pipeline) reads room occupancy — `actor_counters`/`participant_counters` credit
unconditionally on a successful cast, regardless of who else is in the location. `公開自慰`,
`公開表演`, and `無恥宣言`'s compound gate all therefore credit/require `watched_count` as "this act
was performed in a manner framed as public," not "a third party was verifiably present at cast time."
Building the latter would need a new room-occupancy read inside the counter-effect handler —
`sexual-act-effects`'s territory, out of scope here, and not attempted as a partial workaround.

### D-6: An AREA act's `self_exposure` event fires on its targets, not on the actor

`sexual-act-effects`'s landed `_handle_sexual_event` iterates the cast's **targets** — for a
`SELF`-target act that is the actor itself, which is why every SELF shame act raises the actor's own
`exposure` exactly as the seed established; for an `AREA` act the targets are the resolved audience,
and the actor is not among them (`participants()` includes the actor only in the pleasure handler).
`公開表演` and `獻身姿態` therefore deliver their declared `self_exposure` event to each resolved
target — the audience's `exposure` rises by one (and cascades their `shame`), while the performer's
own `exposure` stays put.

This is a disclosed engine-boundary consequence, not the source document's framing (whose shame-line
prose casts every exposure raise as the actor's own self-cost): the performer never accumulates the
`high_exposure_defense_penalty` cost from these two acts, and a target repeatedly performed at (three
casts of a Tier 3/4 AREA act) crosses `exposure >= 高` and starts taking the shipped
`high_exposure_defense_penalty` (defense `-15`) — a mechanical side effect the source design never
claimed. It is accepted rather than engineered around: routing an act's events to the actor as well
would be a change to `world/rules/action.py`'s event handler (`sexual-act-effects`'s territory, out
of scope for a content proposal), and dropping the declaration would contradict the delta spec's
SHALL list. The actual destination is pinned by a test and a delta-spec scenario so it is a
verifiable contract, not an accident; a future engine proposal giving acts an actor-side event
channel should revisit this note.

### D-5: Tier 3/4 gates need no compound-gate hardening beyond what the source document already specifies

`sexual-catalog-solo`'s rubber-duck review flagged an emergent (not structural) safety margin around
its own Tier 3 gate and recommended making it an explicit compound gate. The same question applies
here: could `watched_count` be reached without first crossing the `exposure_act_count` thresholds
Tiers 1/2 gate on?

Within this proposal's own content, `watched_count` actually has **two** sources, not one:
`shame_public_masturbation` (Tier 2, gated on `exposure_act_count: 20` and `masturbation_count: 25`)
and `shame_public_performance` itself (Tier 3, gated on `watched_count: 10` and
`exposure_act_count: 20`). The correct invariant is not "single source" but that **neither source can
be an unprotected first-crosser of the threshold it feeds**: `shame_public_masturbation` requires
`exposure_act_count: 20` before it can be cast at all, and `shame_public_performance` requires
`watched_count: 10` before it can be cast at all — so the only way to ever reach `watched_count >= 10`
is through `shame_public_masturbation`, which already required crossing `exposure_act_count: 20`
first. `無恥宣言`'s second gate (`watched_count >= 30`) inherits the same guarantee transitively. This
proposal declares no additional `exposure_act_count` floor on 挑釁凝視 beyond what that dependency
chain already guarantees, matching the source document's own table exactly (`挑釁凝視`'s gate is
`watched_count: 10` alone there too), unlike C2's Tier 3 where the source document's
`toy_use_count`-alone gate genuinely needed hardening.

This safety is disclosed as emergent, not structural, exactly as C2 disclosed its own equivalent
finding: a future proposal granting `watched_count` from a source other than `公開自慝` (a partner-
line "performed in front of an audience" act, say) would reopen the same fragility C2 hardened
against. Recorded here so that proposal budgets for it rather than rediscovering it.

## Risks / Trade-offs

- **[Risk]** 挑釁凝視's debuff (D-2) is probabilistic, not guaranteed — a target far from the `高度`
  band feels no accuracy penalty from one cast. A player expecting the source document's literal
  "accuracy debuff" framing could be surprised. → **Mitigation**: disclosed here. Note that the
  actor's own `actor_pleasure_ratio` (0.4) is irrelevant to whether a *target* crosses `高度` — every
  non-actor participant always resolves at `ratio=1.0` (`_handle_pleasure_effect`'s existing,
  unmodified behaviour), so the relevant quantity is `base_pleasure` (14) times the target's own
  sensitivity/shame multipliers, not any actor-side adjustment. Against a `Monster` target (`shame`
  hard-clamped to `無`, sensitivity defaulting to `普通`, both ×1.0), one cast yields roughly
  `round(14 × 1.1) ≈ 15` pleasure (the two-participant crowd multiplier applying) — enough to cross
  from `中等` into `高度` only when the target is already within roughly 15–24 points of the `高度`
  floor (pleasure 60). This confirms the act is plausible as "a follow-up act, not an opener" against
  an already-aroused target, without claiming a specific tuning precision this proposal did not
  actually calibrate against the target-side formula.
- **[Risk]** All three AREA acts share `target_part="腰腹"` (D-1), the same neutral-part compromise
  `sexual-act-seeds` used once for `partner_hand_hold`; this proposal is the second use of that
  compromise and the first to apply it three times in one line. → **Mitigation**: disclosed, not
  silent; the three acts' `base_pleasure` values are all high enough that the sensitivity-multiplier
  mismatch (training `腰腹` instead of a thematically-fitting part) has negligible mechanical
  consequence, and — as with every other sensitivity claim in this document set — training itself is
  currently unreachable regardless (`frequent_stimulation` remains blocked).
- **[Risk]** `watched_count`'s no-unprotected-first-crosser dependency (D-5) is a repeat of C2's exact
  finding in a new line, suggesting this class of fragility may recur in every future catalog
  proposal that reuses a counter another line originated. → **Mitigation**: no proposal so far has
  needed to actually harden against it (both C2's and this proposal's dependency chains already
  self-protect, though this proposal's own chain runs through two sources rather than one — see D-5);
  this is
  recorded as a pattern to watch, not a defect to fix speculatively.

- **[Note]** `count = len(participants(actor, targets))` (`sexual-act-effects`'s existing,
  unmodified pipeline) is shared across every participant in one cast, so hitting more enemies at
  once with an `AREA` act raises *both* the actor's own gain and every target's gain, up to the
  `"3+": 1.2` crowd multiplier. For 挑釁凝視/公開表演/獻身姿態 this strengthens, not weakens, their
  intended effect in a multi-enemy fight — noted for completeness, not treated as a risk.

## Migration Plan

Additive only — nine new registry rows in one already-existing, currently-one-row tuple. No
rulebook, engine, or schema change. Zero released users; no backward-compatibility concern applies.

## Open Questions

None for this proposal's own scope.
