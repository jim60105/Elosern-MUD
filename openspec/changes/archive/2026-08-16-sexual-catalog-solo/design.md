## Context

`sexual-act-seeds` (this proposal's direct dependency, not yet merged but frozen in its own
proposal's artifacts at the time of writing) ships three 獨處線 seeds and one new `sexual.yaml` row
(`exposure_up_on_self_exposure`, unrelated to this proposal's line). It leaves `SOLO_ACTS` at three
entries. The source catalog document
(`docs/superpowers/specs/2026-08-15-sexual-act-catalog-design.md` §2) lists seventeen 獨處線 acts in
total across four tiers plus a 忍耐 sub-line; three are the seeds already shipped, leaving fourteen.

Attempting to build all fourteen surfaced a genuine schema boundary in the already-landed
`SexualActDef`/`_act_family()` contract (`sexual-act-registry`, archived): it can express exactly
three things per act — a positive pleasure gain, a set of counter increments, and a set of
`sexual.yaml` event emissions. It cannot express a negative pleasure effect, a secondary buff/debuff,
or a temporary immunity. Three of the fourteen (快感控制, 寸止, 極限忍耐) need the first; one more
(拘束自慰) wants the second as flavour. This document records that boundary and the scope decision it
forces, rather than working around it with a change to `_builder.py` this proposal was not sized for.

## Goals / Non-Goals

**Goals:**
- Register the eleven 獨處線 acts that the landed pleasure/counter/event contract can express
  without modification.
- Disclose, precisely and in one place, which source-document acts this proposal does not build and
  why — so a future proposal picking up the 忍耐 sub-line does not need to independently rediscover
  the schema boundary.

**Non-Goals:**
- 快感控制, 寸止, 極限忍耐 — pleasure-reduction acts. Building these requires, at minimum, a new
  `SexualState` mutator (e.g. `reduce_pleasure(amount)`) and a way for an act to invoke it — either a
  new effect prefix or a signed `base_pleasure` — both of which touch `world/rules/sexual_state.py`
  and/or `world/skills/sexual_acts/_builder.py`, files this proposal does not own. 極限忍耐
  additionally needs a multi-round `climax_gate` immunity, which is a new mechanism outright (nothing
  in the shipped buff or decay systems expresses "this rule does not fire for N rounds").
- 拘束自慰's self-`defense` penalty. `SexualActDef` has no field for a secondary effect beyond
  pleasure/counter/event; adding one is `_builder.py`'s territory (`sexual-act-registry`, archived).
  The act itself ships; only this one flavour detail is dropped.
- Mechanical "multi-part" acts. `雙手併用`, `高階玩具·全身`, and `拘束自慰` are described in the
  source catalog document as touching more than one body part; `SexualActDef.actor_part` is a single
  optional string. Each such act declares one representative part (私處 in all three cases, since the
  source document's own framing escalates toward it) and expresses the "multiple parts" idea in its
  `label`/`description` text only.
- Any change to `world/rules/rulebook/sexual.yaml`. Unlike `sexual-act-seeds`, no act in this
  proposal needs a rule this repository does not already have — every event this proposal's acts
  declare (`masturbation_climax`, or none) was already reachable before this proposal.

## Decisions

### D-1: The eleven rows

| Key | Label | Tier | Unlock | `actor_part` | `base_pleasure` | Counters (actor) | Events |
|---|---|---|---|---|---|---|---|
| `solo_deep_touch` | 深度自慰 | 1 | `masturbation_count: 10` | 私處 | 16 | `masturbation_count` | `masturbation_climax` |
| `solo_both_hands` | 雙手併用 | 1 | `masturbation_count: 10` | 私處 | 17 | `masturbation_count` | `masturbation_climax` |
| `solo_finger_lick` | 舔舐指尖 | 1 | `masturbation_count: 10` | 口唇 | 10 | `masturbation_count` | — |
| `solo_rear_touch` | 撫弄後庭 | 1 | `masturbation_count: 10` | 後庭 | 13 | `masturbation_count` | — |
| `solo_nipple_play` | 玩弄乳尖 | 1 | `masturbation_count: 10` | 乳房 | 12 | `masturbation_count` | — |
| `solo_toy_vibrator` | 玩具自慰·振動 | 2 | `masturbation_count: 25` | 私處 | 20 | `masturbation_count`, `toy_use_count` | — |
| `solo_toy_clamps` | 玩具自慰·夾具 | 2 | `masturbation_count: 25` | 乳房 | 18 | `masturbation_count`, `toy_use_count` | — |
| `solo_toy_plug` | 玩具自慰·填充 | 2 | `masturbation_count: 25` | 後庭 | 19 | `masturbation_count`, `toy_use_count` | — |
| `solo_toy_advanced_link` | 高階玩具·連結 | 3 | `masturbation_count: 25`, `toy_use_count: 15` | 私處 | 24 | `masturbation_count`, `toy_use_count` | — |
| `solo_toy_advanced_full` | 高階玩具·全身 | 3 | `masturbation_count: 25`, `toy_use_count: 15` | 私處 | 26 | `masturbation_count`, `toy_use_count` | — |
| `solo_bound_masturbation` | 拘束自慰 | 3 | `masturbation_count: 25`, `toy_use_count: 15` | 私處 | 25 | `masturbation_count`, `toy_use_count` | — |

Every row: `target_spec=SELF`, `target_part=None`, `actor_pleasure_ratio=1.0`,
`participant_counters=()` (structurally required for a `SELF` act — `sexual-act-registry`'s existing
invariant), `resistible=False`.

**Tier 3's gate is compound, not `toy_use_count` alone.** An earlier draft gated Tier 3 on
`{"toy_use_count": 15}` only, relying on the fact that every act crediting `toy_use_count` in this
proposal *also* credits `masturbation_count` in the same call — so Tier 3 was, in practice,
unreachable without having already crossed 25 masturbations, but only as an emergent property of
this proposal's own counter-crediting choices, not as a structural guarantee. A future proposal
granting `toy_use_count` from some other source (partner-line toy content, a future toy item system)
could silently open a "Tier 3 without ever passing Tier 1/2" path with no test anywhere to catch it.
Naming `masturbation_count: 25` explicitly in the three Tier 3 rows' `unlock` mapping — redundant
with the emergent behaviour today, load-bearing against future proposals tomorrow — costs nothing
(`unlocked_act_keys_for`'s existing all-conditions-must-hold semantics already support a compound
gate with no code change) and removes the fragility permanently.

Tier 2/3 acts credit **both** `masturbation_count` and `toy_use_count` on every cast. A toy act does
not stop being a masturbation act; the pleasure-model design document's own counter table lists
自慰次數 as incrementing on "執行單人 act" without excluding toy-flavoured ones, and 玩具使用次數 as
an additional, not alternative, credit.

Only the two acts most directly framed as an escalation of the seed act (深度自慰, the seed's direct
"deeper" successor, and 雙手併用, which the source document frames as building toward climax) declare
`masturbation_climax` in `sexual_events`. This follows `sexual-act-seeds`'s own precedent (D-5 there):
the event is idempotent and technically safe to fire from every act, but restricting it to acts
explicitly framed as climax-adjacent avoids overclaiming a completed climax from, e.g., a light
finger-lick.

### D-2: The pleasure-reduction gap is real, not a modelling oversight

`_act_family()`'s existing validation (`sexual-act-registry`, unmodified by this proposal):

```python
if (
    isinstance(base_pleasure, bool)
    or not isinstance(base_pleasure, int)
    or base_pleasure <= 0
):
    raise ValueError(f"act {key!r}: base_pleasure must be a positive integer")
```

and `_apply_pleasure_gain` (`sexual-act-effects`, unmodified): `entity.sexual.pleasure.base += gain`
— strictly additive, no code path subtracts. There is no way to author 快感控制/寸止/極限忍耐 as
`SexualActDef` rows without either (a) a negative-capable `base_pleasure`/gain path, which the
positive-integer validation explicitly forbids, or (b) a distinct new effect prefix
(`pleasure_reduce:`, say) with its own handler — both squarely `sexual-act-effects`'s or
`sexual-act-registry`'s territory, not a line-module content proposal's.

This is the same class of gap `sexual-act-seeds` found for exposure-raising, with one difference:
that gap was a **missing rulebook row** (cheap — one YAML entry plus one test, safely absorbed into
the seed proposal that needed it). This gap is a **missing engine capability** (a new mutator, a new
effect prefix, and the validation change to permit it) — not something to fold into a single-line
catalog proposal without inflating it well past a one-day scope. The three acts are deferred rather
than built with a workaround.

### D-3: 極限忍耐 needs an immunity mechanism that plainly does not exist yet

Independent of the pleasure-reduction gap, the source document's 極限忍耐 additionally promises
"several rounds immune to `climax_gate`." `climax_gate`'s condition (`{field: arousal, equals: 極限}`)
is evaluated unconditionally by `apply_event()`'s fixed-point loop; nothing in the shipped rule
schema, buff system, or `SexualState` supports suppressing one specific rule's evaluation for a
bounded number of rounds. Even if the pleasure-reduction gap (D-2) were resolved, 極限忍耐 would still
need this second, independent mechanism. Recorded here so a future proposal picking up the 忍耐
sub-line budgets for two gaps, not one.

### D-4: 拘束自慰 ships without its self-`defense` penalty, and is deliberately not left as the tier's top pick

The source document frames 拘束自慰 as trading a self-inflicted `defense` penalty for above-tier
pleasure. `SexualActDef` has no field for a secondary buff/debuff effect — `_act_family()`'s
auto-generated `effects` list is exactly `["pleasure:<key>", "sexual_counter:<key>", *sexual_event
entries]`, with no seam for an additional `self_buff_apply:<key>` string. Rather than block the act
entirely on a `_builder.py` change, this proposal ships 拘束自慰 as a plain Tier 3 pleasure act. The
bondage flavour lives in the label/description text only.

An earlier draft additionally gave it the tier's highest `base_pleasure` (28, above
高階玩具·全身's 26), reasoning the number alone should "carry" the missing risk framing. That is
wrong: all three Tier 3 acts share an identical unlock gate, identical counters, identical target
shape, and (after this decision) identical downside (none) — `base_pleasure` was the only
differentiator, so the highest number made 拘束自慰 a strict, zero-drawback upgrade over its two
siblings, turning three intended alternatives into one obvious pick and two dead entries. Every
`SEXUAL_ACT`-category skill is also `usable_out_of_combat=True` with nothing gating it out of an
active battlefield context, so this was not even a narrative-only concern — a mid-combat cast of the
highest-pleasure Tier 3 act would have carried literally the source document's promised benefit with
none of its promised cost. This proposal instead sets 拘束自慰's `base_pleasure` to 25, between
高階玩具·連結's 24 and 高階玩具·全身's 26 — no act in the tier dominates another, matching how Tier 1's
five acts already differ by `base_pleasure` alone with no dominance concern (their spread, 10–17, has
no single act that is both the tier's cheapest to unlock and its strongest, since all five share one
unlock gate already).

### D-5: Single-part acts absorb the source document's "multi-part" framing

雙手併用, 高階玩具·全身, and 拘束自慰 all declare `actor_part="私處"` — the same part — despite the
source document describing each as touching more than one region. `SexualActDef.actor_part` is one
optional string; there is no list field. 私處 is chosen because the source document's own prose
escalates each of these three toward it (雙手併用: "乳房→私處"; the other two are described as
whole-body build-ups culminating there). This means these three acts and 深度自慰/
高階玩具·連結/拘束自慰's own Tier grouping all sensitivity-train the same single part
(`sensitivity["私處"]`) rather than the several distinct parts the source document's flavour text
implies — an intentional, disclosed simplification, not a mechanical claim that these acts are
identical in narrative content.

## Risks / Trade-offs

- **[Risk]** A player reading the original catalog design document
  (`2026-08-15-sexual-act-catalog-design.md`) would expect seventeen 獨處線 acts after
  `sexual-act-seeds` + this proposal (3 + 14); only 3 + 11 = 14 exist. → **Mitigation**: disclosed
  here and in the proposal's Impact section, not silent. The three missing acts are a real, named
  future proposal's scope (D-2/D-3), not lost.
- **[Risk]** Concentrating five of eleven acts' `actor_part` on 私處 (深度自慰, 雙手併用,
  玩具自慰·振動, 高階玩具·連結, 高階玩具·全身, 拘束自慰 — six, in fact) trains that one part's
  sensitivity far faster than any other part reachable from this line, even setting aside that
  sensitivity training is itself currently unreachable (`frequent_stimulation` remains blocked, per
  `sexual-act-seeds`'s design.md, inherited unchanged here). → **Mitigation**: this mirrors the
  source document's own part distribution (獨處線's later tiers are explicitly private-parts-forward
  compared to its earlier, more varied tiers), so it is a faithful transcription, not an introduced
  imbalance; and since sensitivity training is not reachable through any current cast path regardless
  of part, no live gameplay effect exists yet either way.
- **[Risk]** Toy acts (Tier 2/3) credit two counters per cast; a hypothetical future consumer that
  assumes one counter per cast per act (as `sexual-act-seeds`'s seven seeds each do) would
  undercount. → **Mitigation**: `sexual-act-effects`'s `_handle_sexual_counter_effect` already
  supports multiple counters per role (design.md's own docstring: "the schema's way of crediting both
  parties of a symmetric two-person act" generalizes to "crediting more than one axis of one
  party's participation"); no assumption anywhere in the landed contract requires exactly one counter
  per act.

## Migration Plan

Additive only — eleven new registry rows in one already-existing, currently-empty tuple. No rulebook,
engine, or schema change. Zero released users; no backward-compatibility concern applies.

## Open Questions

None for this proposal's own scope. D-2/D-3/D-4 name concrete follow-up work but do not require a
decision before this proposal can land.
