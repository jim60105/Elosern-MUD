## Context

`world/skills/sexual_acts/partner.py` ships two seed rows in `PARTNER_ACTS` (`sexual-act-seeds`,
already merged): `partner_caress` (愛撫, 腰腹/腰腹, `actor_pleasure_ratio=0.5`) and
`partner_hand_hold` (牽手交纏, same shape, lower `base_pleasure=3`). Both are `TargetSpec.SINGLE`,
`resistible=True`, and credit `duo_act_count` on `actor_counters` and `participant_counters` alike —
the pattern this proposal's Tier 1-3 acts all reuse unchanged.

`sexual-act-catalog-design.md` §4 specifies eighteen 關係線 acts total (the two seeds plus sixteen
more). This proposal builds fourteen of the sixteen; §4.1's two intercourse acts (交合, 深度交合) are
deferred — D-2 below is the reason, in the same "name the exact code, don't route around it" style
`sexual-catalog-solo` (C2) used for its three deferred pleasure-reduction acts and
`sexual-catalog-shame` (C3) used for its two dropped secondary effects.

This document is written directly against the landed contract in `_builder.py`,
`sexual_act_effects.py`, and `action.py` — not against the source catalog document's prose, which
predates several implementation-time corrections C2/C3 already found and recorded.

## Goals / Non-Goals

**Goals:**
- Ship the fourteen buildable 關係線 acts across Tiers 1-4, each a plain
  `SexualActDef`/`SkillDef` pair through `_act_family("關係", ...)`.
- Keep every act's `unlock` gate readable directly off `duo_act_count`/`group_act_count`/
  `climax_count`, the three counters `sexual-counters` (B2) already ships mutators for.
- Preserve the two shipped seeds' symmetric counter-crediting convention (both `actor_counters` and
  `participant_counters` declare the same tuple) for every new Tier 1-3 act, and extend it to
  `group_act_count` for Tier 4.
- Leave `world/rules/action.py`, `_builder.py`, `__init__.py`, and every other line module
  byte-for-byte unchanged — this proposal's only code file is `partner.py` plus its new test module.

**Non-Goals:**
- Building 交合/深度交合 (D-2) or fixing the `_handle_sexual_event` target-only-application gap
  乳交 inherits (D-3) — both are named, disclosed, and left for a future proposal.
- Wiring `resistible=True` to an actual resist-contest call site. `sexual-resist-contest` (B6a) and
  `sexual-resist-turn-cost` (B6b) are both merged, but nothing in `action.py` yet calls
  `resist_verdict()` from an act's cast path — `resistible` remains declarative metadata a future
  wiring proposal consumes, exactly as it already was for every `resistible=True` act B8/C2/C3
  shipped.
- Reworking `base_pleasure` tuning system-wide; every value here is a `sexual_acts` module constant
  per §1.2 of the source catalog, trivially retunable and non-load-bearing for correctness.

## Decisions

### D-1: The fourteen acts, exactly as registered

| Key | Label | Tier | Unlock | Part (actor=target) | Base | Ratio | Counters | Events |
|---|---|---|---|---|---|---|---|---|
| `partner_kiss` | 親吻 | 1 | `duo_act_count: 5` | 口唇 | 12 | 0.5 | duo (both) | — |
| `partner_neck_caress` | 撫摸頸項 | 1 | `duo_act_count: 5` | 頸項 | 12 | 0.5 | duo (both) | — |
| `partner_breast_play` | 揉捏胸部 | 1 | `duo_act_count: 5` | 乳房 | 13 | 0.5 | duo (both) | — |
| `partner_ear_whisper` | 耳邊細語 | 1 | `duo_act_count: 5` | 耳朵 | 11 | 0.5 | duo (both) | — |
| `partner_deep_caress` | 深度愛撫 | 2 | `duo_act_count: 15` | 私處 | 20 | 0.5 | duo (both) | — |
| `partner_oral_service` | 口舌服務 | 2 | `duo_act_count: 15` | 口唇 | 19 | 0.5 | duo (both) | — |
| `partner_breast_sex` | 乳交 | 2 | `duo_act_count: 15` | 乳房 | 19 | 0.5 | duo (both) | `breast_sex_performed` |
| `partner_thigh_rub` | 腿間摩擦 | 2 | `duo_act_count: 15` | 大腿 | 18 | 0.5 | duo (both) | — |
| `partner_foot_service` | 足部服務 | 2 | `duo_act_count: 15` | 足部 | 17 | 0.5 | duo (both) | — |
| `partner_anal_sex` | 後庭交合 | 3 | `duo:30, climax:10` | 後庭 | 26 | 0.6 | duo (both) | — |
| `partner_mutual_masturbation` | 相互自慰 | 3 | `duo:30, climax:10` | 私處 | 18 | 1.0 | duo (both) | — |
| `partner_group_caress` | 多人愛撫 | 4 | `duo_act_count: 30` | 腰腹 (AREA) | 18 | 0.5 | group (both) | — |
| `partner_group_orgy` | 多人交歡 | 4 | `group_act_count: 15` | 腰腹 (AREA) | 20 | 0.5 | group (both) | — |
| `partner_group_service` | 群體服務 | 4 | `group_act_count: 30` | 腰腹 (AREA) | 22 | 0.5 | group (both) | — |

"duo (both)" / "group (both)" means the named counter appears in both `actor_counters` and
`participant_counters`, matching the two shipped seeds — every participant, actor included, is
credited once per cast, never only one side.

Tier 4's three acts credit `group_act_count`, not `duo_act_count`, on cast — even though 多人愛撫's
own unlock gate reads `duo_act_count`. A player unlocks their first group act through two-person
experience, but *casting* it is itself a group encounter, so its own credit feeds the next two acts'
`group_act_count` gates. This mirrors how Tier 2's toy acts in `sexual-catalog-solo` credit both the
gating counter and the counter the next tier reads.

### D-2: 交合 and 深度交合 are deferred — no mechanism selects a `sexual_events` entry from runtime participant state

`sexual-act-catalog-design.md` §4.1 requires each act to emit exactly one of three different events
depending on the two participants' `sex` field (`world/lore/sex.py`, `entity-sex-field`/S1, merged)
at the moment of casting:

| Partner sexes | Event | Breaks `virgin` |
|---|---|---|
| opposite | `first_vaginal_penetration` | yes |
| both female | `penetrative_sex_with_female` | no |
| both male | `penetrative_sex_with_male` | no |
| either `other`/unknown | (same shape as the female branch) | no |

`SexualActDef.sexual_events` (`_builder.py:68`) is a single `tuple[str, ...]` fixed at
`_act_family()` call time — a module-load-time constant, identical for every cast regardless of who
the target turns out to be. Nothing in `_handle_sexual_event` (`action.py:547-581`) or
`SexualActDef` reads participant state to choose *which* declared event applies; every name in the
tuple fires on every cast, unconditionally (`action.py:569-581`).

Two acts declaring three mutually-exclusive events and picking one per cast is a genuinely new
capability — a conditional-dispatch mechanism neither `_builder.py` nor `action.py` has today. Adding
it means extending shared, already-merged infrastructure (most likely `_handle_sexual_event` itself,
or a new `sexual_events`-adjacent field letting an act declare `{condition: event}` pairs), which is
out of a catalog proposal's file ownership (`partner.py` and its own tests only) by the same
discipline that kept `sexual-catalog-solo`'s three pleasure-reduction acts and `sexual-catalog-shame`'s
two dropped secondary effects out of those proposals' scope.

**What a follow-up needs:** a way for an act's cast to compute
`actor.sex`/`target.sex` and select the emitted event accordingly, landing in `sexual-act-effects` or
a dedicated successor capability — not in this proposal, and not by giving `partner.py` special-case
logic no other line module has.

**Rejected alternative — ship 交合 emitting a fixed event unconditionally.** Hardcoding
`first_vaginal_penetration` would incorrectly break `virgin` for a same-sex pair, directly
contradicting the explicit, user-approved requirement that `virgin` breaks only on opposite-sex
vaginal intercourse. Hardcoding one of the non-breaking events instead would silently under-deliver
the act's entire narrative point for opposite-sex pairs. Neither is an acceptable partial delivery;
deferring outright is more honest than shipping either wrong branch.

**Rejected alternative — ship three separately-keyed acts (`partner_vaginal_sex_hetero`,
`_lesbian`, `_gay`) and let the player pick the "right" one.** This asks the player to manually
declare their own and their partner's sex through act *choice* rather than the game deriving it from
`LivingEntity.sex`, which is both bad UX and a duplicate, error-prone source of truth for a fact the
schema already tracks structurally. Rejected.

### D-3: 乳交 ships despite `_handle_sexual_event`'s target-only event application

`_handle_sexual_event` (`action.py:547-581`) loops over its raw `targets` parameter and calls
`apply_event(target, event_name, ...)` for each — it does **not** call `participants(actor, targets)`
first, unlike `_handle_pleasure_effect` (`action.py:619`) and `_handle_sexual_counter_effect`
(`action.py:720`), which both expand to the full participant list before applying their effects. For
a `TargetSpec.SELF` act (every `sexual-catalog-solo` act), `targets` already equals `[actor]`
(`ActionResolver`'s own targeting step resolves it that way), so this gap has never been visible: the
sole existing consumer of `sexual_events` on a non-seed act (`solo_deep_touch`,
`sexual_events=("masturbation_climax",)`) happens to have `targets == [actor]` regardless.

乳交 is the first two-party act to declare a `sexual_events` entry. Cast against a chosen partner,
`targets == [partner]` — `breast_sex_performed` fires only on the partner, and
`experience_titfuck_added`'s `乳交` experience-type credit lands only on them, never on the actor who
initiated it.

This proposal ships 乳交 anyway: its `pleasure:partner_breast_sex` and
`sexual_counter:partner_breast_sex` effects (both correctly participant-expanded, since those two
handlers already call `participants()`) deliver full value independent of this gap, and 乳交 is the
catalog's sole planned emitter of `breast_sex_performed` — deferring it would leave that rule
unemitted indefinitely with no compensating benefit. The event-recipient asymmetry is named here,
not fixed here: fixing `_handle_sexual_event` means changing `action.py`, a file
`sexual-act-effects` (B5) owns and this proposal does not touch. A future proposal that extends
`_handle_sexual_event` to call `participants(actor, targets)` — mirroring its two sibling handlers —
would fix this for 乳交 and for `sexual-catalog-interspecies`'s 異種交合 (which inherits the identical
gap) in one place.

### D-4: 後庭交合 and 相互自慰 trade off by design intent, not by a provable numeric dominance guarantee

Both Tier 3 acts share the same unlock gate (`duo_act_count: 30, climax_count: 10`) but declare
different `target_part`s (後庭 vs 私處). At `participant_count == 2` (the only value either act can
reach — both are `TargetSpec.SINGLE`), the baseline (untrained, `普通`/`無`, all multipliers `1.0`)
comparison is:

- 後庭交合: `base_pleasure=26`, `ratio=0.6` → actor gain = round(26×0.6×1.1) = 17, **target** gain =
  round(26×1.0×1.1) = 29 (target ratio is always `1.0`). The generous act *for your partner*.
- 相互自慰: `base_pleasure=18`, `ratio=1.0` → actor gain = round(18×1.0×1.1) = 20, target gain = 20.
  The balanced, *mutual* act — matching its "bidirectional gain doubled" source-catalog note by
  giving the actor the same full ratio the target already gets, rather than a literal >1.0 multiplier
  this schema has no precedent for outside the divine line.

At baseline this is a real trade-off (相互自慰 gives the actor 3 more; 後庭交合 gives the partner 9
more), and an earlier draft of this document stopped there, framing it as a settled non-dominance
guarantee. A rubber-duck review correctly rejected that framing: `sensitivity_mult` is a **per-body-
part** trait (`sensitivity_up_on_frequent_stimulation` trains 後庭 and 私處 independently), so a
character who has trained one part more than the other has *unequal* multipliers on the two acts'
respective parts, and no fixed `base_pleasure`/`ratio` choice can guarantee either side of the
trade-off survives that divergence — a large enough sensitivity gap (`普通` ×1.0 up to `敏感異常`
×2.5, per `sexual_pleasure.yaml`) swamps a margin this small in either direction.

This proposal does **not** claim numeric non-dominance as a structural guarantee. It cannot claim
that for *any* pair of same-tier acts on different body parts — Tier 1's four acts and Tier 2's five
acts have the identical property, and per §1.1 of the source catalog document, that is the intended
mechanic: body-part variety is what lets sensitivity training diverge in the first place, so which
act is "better" for a given character is supposed to depend on their individual play history, not on
a catalog author's fixed numbers. What this proposal does guarantee is the narrower claim
`sexual-catalog-solo`'s rubber-duck review actually cared about: no two acts here are dominated
**for every character regardless of history** — that failure mode is only possible between two acts on
the *identical* body part (where sensitivity cancels out of the comparison identically for both), and
後庭交合/相互自慰 are not on the identical part. See the note below on same-part pairs across tiers,
where that stricter guarantee does apply and is deliberately not attempted.

**Same-body-part pairs across tiers are intentionally progressive, not balanced.** `partner_kiss`
(口唇, Tier 1, base 12) and `partner_oral_service` (口唇, Tier 2, base 19) share a body part, and once
`duo_act_count >= 15` unlocks the latter, the former is a strict downgrade on every axis (same ratio,
same counters, lower `base_pleasure`, no event). The same is true of `partner_breast_play`
(乳房, Tier 1) versus `partner_breast_sex` (乳房, Tier 2). This is deliberate, ordinary tiered-skill
progression — a higher-tier act on the same part superseding a lower-tier one, the same pattern any
levelled skill line uses — not the zero-downside-sibling problem D-4 exists to avoid. It is called
out explicitly here so the omission reads as a decision, not an oversight: `sexual-catalog-solo`'s
dominance concern applies to acts that share both a body part *and* an unlock tier (true rivals), not
to acts a character simply outgrows.

The three Tier 4 AREA acts are a stricter case of the same progression, and it is deliberate too:
all three sit on 腰腹, so once `partner_group_orgy` (base 20) unlocks at `group_act_count >= 15` it
strictly dominates `partner_group_caress` (base 18) for every character that owns both — and
`partner_group_service` (base 22, `group_act_count >= 30`) dominates both. But the trio is not a
rival choice set, it is a sequential unlock chain: `partner_group_caress` is the duo-gated entry
point (its casts feed `group_act_count` toward `partner_group_orgy`), and `partner_group_orgy`'s own
casts feed the `group_act_count >= 30` gate of `partner_group_service`. Each act is the unlock path
for the next, so the within-tier strict dominance *is* the progression, exactly as D-1's note
describes ("its own credit feeds the next two acts' `group_act_count` gates"). A `group_act_count`
reading can never arise without first owning the weaker act (`group_act_count` is credited only by
these three acts, and `partner_group_caress`'s `duo_act_count >= 30` gate is monotone once met), so
the chain has no skipped links.

### D-7: `resolve_targets`'s AREA branch accepts a self-cast, letting a solo player grind `group_act_count` — disclosed, not fixed here

`world/rules/targeting.py`'s `resolve_targets()` carries a sexual-act self-cast exclusion for
`TargetSpec.SINGLE` only (`targeting.py:187-198`: a SINGLE-target sex act whose sole candidate is the
actor is rejected as `target_spec_mismatch`). The `TargetSpec.AREA` branch (`targeting.py:199-210`)
validates cardinality, uniqueness, and candidate quality but never excludes the actor — and
`RoomActionContext.is_present()` explicitly accepts `target is actor`, so a self-only AREA cast is
valid. Consequence: a player at `duo_act_count >= 30` can cast `partner_group_caress` targeting
only themselves — through the normal `cast` command by naming their own character, or through the
combat `all-allies` shorthand, which includes the `SELF` relation — and the act still credits
`group_act_count` on the actor, because `_handle_sexual_counter_effect` credits `actor_counters`
unconditionally. The same cast also opens the other two Tier 4 acts once their `group_act_count`
gates are solo-fed. That directly undermines D-1's "casting it is itself a group encounter" intent.

This proposal does **not** fix it: the exclusion is shared engine code in `world/rules/targeting.py`,
out of this proposal's file boundary (partner.py plus its own test module, per the Goals section),
and the same gap already shipped with `sexual-catalog-shame`'s three AREA acts — a fix belongs in a
single shared-engine follow-up that extends the SINGLE-branch exclusion to the AREA branch for
`SkillCategory.SEXUAL_ACT` skills, benefiting every line at once. This proposal's tests deliberately
do not pin the self-cast behavior (it is not intended behavior; pinning it in a delta-spec scenario
would codify the exploit as a contract); all cast tests here target explicit non-self partners. The
follow-up proposal owns both the engine change and the rejection tests. Until then the solo grind is
live but self-contained: it is the player's own progression cost only, and the divine line is not
involved.

### D-5: The three Tier 4 AREA acts reuse the `target_part="腰腹"` compromise

`_act_family()` requires a non-null `target_part` for any non-`SELF`/`NONE`, non-異種/神之秘法 act
(`_builder.py:160-171`), and an `AREA` act's targets can be an arbitrary mix of entities with no
single natural erogenous-zone mapping for "everyone present." `sexual-act-seeds` established
`target_part="腰腹"` as the neutral compromise for this exact situation
(`partner_hand_hold`'s D-4), and `sexual-catalog-shame` (C3) reused it for its own three AREA acts.
This proposal reuses the same convention for its three AREA acts rather than inventing a fourth
rationale for the same structural constraint.

### D-6: Dependency-surface assumptions this proposal reads, not writes

- `sexual-counters` (B2, merged): `duo_act_count`, `group_act_count`, `climax_count`, and their sole
  mutators (`record_duo_act`, `record_group_act`, `record_climax_count`) are unchanged.
- `sexual-act-effects` (B5, merged): `compute_pleasure_gain`'s participant-count ladder (`1.0` /
  `1.1` / `1.2` at 1/2/3+ participants) and `resolve_part`'s Monster-collapse behavior are unchanged;
  this proposal's acts never target a `Monster` (that's `sexual-catalog-interspecies`'s exclusive
  domain) so the collapse never triggers here.
- `climax_count` is credited exclusively by the climax-settlement clock's own mutator call
  (`sexual_state.py:867`), never by an act's `actor_counters` — Tier 3's compound gate reads it but no
  act in this proposal (or any catalog proposal) writes it directly, matching the same pattern
  `sexual-catalog-solo`'s Tier 3 established for `toy_use_count` alongside `masturbation_count`.
- `world/rules/rulebook/sexual.yaml`'s `experience_titfuck_added` row (`breast_sex_performed` →
  add `乳交` to `experience_types`) is unchanged and already shipped; this proposal adds no new
  rulebook row.
- `sexual-resist-cast-wiring` (merged while this proposal was in flight) wired
  `resist_verdict()` into `ActionResolver.resolve()`: every `resistible=True` act now runs one
  d100 contest per non-actor target, and a resisting target is excluded from the act's
  pleasure/counter/event effects. This proposal's cast tests force a compliant roll
  (`patch("world.rules.action.roll_d100", return_value=1)`) so the target-side credits the delta
  spec pins stay deterministic, and call `register_catalog()` in setUp because the resist gate's
  affinity-config read requires the quest definition registry. The actor-side effects the cast
  tests assert are unconditional on resist outcome by that change's design, so the actor
  assertions need no fixture.

## Risks / Trade-offs

- **[Risk]** A future proposal fixes `_handle_sexual_event`'s target-only gap (D-3) by switching to
  `participants(actor, targets)`, which would also start applying 乳交's event to the actor —
  a behavior change this proposal's own tests do not pin against. → **Mitigation:** this proposal's
  test suite asserts 乳交's *currently correct* behavior (event reaches the target) without asserting
  the actor is *excluded* from it, so a future fix cannot regress against a test this proposal wrote.
- **[Risk]** Shipping fourteen acts without 交合/深度交合 leaves the single most design-emphasized
  mechanic (opposite-sex-only `virgin` breaking) completely undelivered after this proposal lands.
  → **Mitigation:** D-2 states exactly what a follow-up proposal needs; this is a loud, proposal-level
  disclosure rather than a buried caveat, so the gap is visible to whoever sequences the next batch of
  work.
- **[Risk]** `partner_breast_play`'s label (揉捏胸部) exactly matches the already-shipped
  `solo_fondle_breasts` seed's label. → **Mitigation:** this is the intentional near-duplicate pattern
  §1.1 of the source catalog document describes — different `key`s, independent per-part
  `sensitivity` training, no registry collision (`_register_rows` only fails closed on duplicate
  `key`s, never duplicate labels).
- **[Risk]** `resolve_targets`'s AREA branch accepts the actor as a candidate, so a player at
  `duo_act_count >= 30` can self-cast `partner_group_caress` with no partner and still credit
  `group_act_count` on themselves — a solo grind that bypasses D-1's "casting it is itself a group
  encounter" intent, and it is player-reachable through the normal `cast` command (targeting your
  own character by name). → **Mitigation:** disclosed in D-7 with the exact engine site
  (`targeting.py:199-210`); the fix — extending the SINGLE-branch sexual-act self-cast exclusion
  (`targeting.py:187-198`) to the AREA branch — is a shared-engine change out of this proposal's
  file boundary, and the same gap already ships in `sexual-catalog-shame`'s AREA acts, so it belongs
  to one engine follow-up benefiting every line. This proposal's tests intentionally do not pin the
  self-cast behavior.

## Migration Plan

Pure content addition; no data migration. `PARTNER_ACTS` grows from 2 rows to 16; every existing
consumer (`SEXUAL_ACT_REGISTRY`, `unlocked_act_keys_for`, the combat panel's category grouping) reads
the tuple structurally and requires no change.

## Open Questions

None — the two acts this proposal cannot deliver (交合, 深度交合) are a resolved deferral (D-2), not
an open question; what a follow-up needs to build is stated explicitly.
