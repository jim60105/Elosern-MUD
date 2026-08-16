## Why

`sexual-act-seeds` ships two unconditionally-available 關係線 seeds in `world/skills/sexual_acts/
partner.py`'s `PARTNER_ACTS` tuple — `partner_caress` (愛撫) and `partner_hand_hold` (牽手交纏), both
`TargetSpec.SINGLE`, both crediting `duo_act_count` on actor and target alike. Past those two seeds,
the line has nothing: a pair who has interacted five or more times has no further 關係線 content to
unlock, even though `duo_act_count` and `group_act_count` — the two counters this line trains — are
already fully wired by `sexual-counters` (B2) and consumed by `sexual-act-effects` (B5).

This proposal fills four of the five remaining tiers: four acts at `duo_act_count >= 5`, five at
`duo_act_count >= 15`, two at `duo_act_count >= 30` (compound-gated on `climax_count` too), and three
AREA acts spanning `duo_act_count >= 30` through `group_act_count >= 30` — fourteen acts total. It
does **not** ship 交合/深度交合 (vaginal intercourse), the two acts the source catalog names as the
sole triggers of `virginity_once`; see "What Changes" and design.md D-2 for the structural reason and
what a follow-up proposal needs to deliver them correctly.

## What Changes

- Add fourteen acts to `world/skills/sexual_acts/partner.py`'s `PARTNER_ACTS` tuple, every one
  `TargetSpec.SINGLE` or `TargetSpec.AREA`, `resistible=True`, crediting `duo_act_count` and/or
  `group_act_count` on every participant (never `actor_counters`-only, matching the two shipped
  seeds' symmetric crediting):
  - **Tier 1** (`unlock={"duo_act_count": 5}`): 親吻 (口唇), 撫摸頸項 (頸項), 揉捏胸部 (乳房—
    a deliberate near-duplicate of the `solo_*` seed of the same label on a different line, per
    `sexual-act-catalog-design.md` §1.1), 耳邊細語 (耳朵).
  - **Tier 2** (`unlock={"duo_act_count": 15}`): 深度愛撫 (私處), 口舌服務 (口唇), 乳交 (乳房 —
    the sole emitter of `breast_sex_performed`, a rule that has existed unemitted since the
    transition rulebook landed), 腿間摩擦 (大腿), 足部服務 (足部).
  - **Tier 3** (`unlock={"duo_act_count": 30, "climax_count": 10}`): 後庭交合 (後庭, no
    `sexual_events` — the source table marks it "never breaks `virgin`", which this proposal
    satisfies for free by declaring no penetration event at all) and 相互自慰 (私處,
    `actor_pleasure_ratio=1.0` — the source catalog's "bidirectional gain doubled" note, delivered
    by giving the actor the same full ratio every recipient already gets. The two acts trade off at
    baseline — 後庭交合 gives the partner more, 相互自慰 gives the actor more — but that trade-off is
    not, and cannot be, a structural non-dominance guarantee once per-body-part sensitivity training
    diverges; see design.md D-4 for why that's the same situation every other same-tier,
    different-part pair in this catalog is already in, by design).
  - **Tier 4** (`TargetSpec.AREA`, `target_part="腰腹"`): 多人愛撫 (`unlock={"duo_act_count": 30}`),
    多人交歡 (`unlock={"group_act_count": 15}`), 群體服務 (`unlock={"group_act_count": 30}`) — all
    three credit `group_act_count` (not `duo_act_count`) on every participant, so a duo-trained
    player's first group act is what starts building toward the next two.
- **Explicitly defers 交合 and 深度交合** (vaginal intercourse, `unlock={"duo_act_count": 30,
  "climax_count": 10}` in the source catalog): the source design's §4.1 requires each cast to emit
  one of three different `sexual.yaml` events (`first_vaginal_penetration`,
  `penetrative_sex_with_female`, or `penetrative_sex_with_male`) depending on the two participants'
  `sex` field at cast time — but `SexualActDef.sexual_events` is a single tuple fixed at registry-load
  time, with no mechanism to select among alternatives based on runtime participant state. Building
  that selection is out of a pure-data catalog proposal's reach; see design.md D-2.
- **Discloses an engine-level self-cast gap on the Tier 4 AREA acts**: `resolve_targets`'s AREA
  branch accepts the actor as a candidate, so a solo player can self-cast `partner_group_caress` and
  credit `group_act_count` with no partner present, bypassing the "casting it is itself a group
  encounter" intent. This proposal does not fix it — the exclusion lives in `world/rules/targeting.py`
  (shared engine, out of a content proposal's file boundary) and the gap already shipped with
  `sexual-catalog-shame`'s AREA acts — but names the exact site for a shared-engine follow-up; see
  design.md D-7.
- **Ships 乳交 with a disclosed, non-blocking event-recipient gap**: `_handle_sexual_event`
  (`world/rules/action.py`, owned by the already-merged `sexual-act-effects`) applies a declared
  `sexual_events` entry to the resolver's raw `targets` list only, never to the actor — unlike
  `_handle_pleasure_effect`/`_handle_sexual_counter_effect`, which both expand to
  `participants(actor, targets)`. This means casting 乳交 credits the `breast_sex_performed` →
  `乳交` experience type to the receiving partner only, not the actor who initiated it. This
  proposal ships 乳交 anyway — its pleasure and counter effects are correct and valuable
  independent of this gap — and names the asymmetry for whichever future proposal extends
  `sexual-act-effects` to close it, rather than reaching into that already-merged file itself; see
  design.md D-3.

## Capabilities

### New Capabilities
- `sexual-catalog-partner`: the fourteen Tier 1–4 關係線 acts and their counter-based unlock
  thresholds.

### Modified Capabilities
- none — `sexual-act-registry`, `sexual-act-effects`, and `sexual-act-seeds`'s existing requirements
  (including the two shipped `PARTNER_ACTS` seed rows) are exercised, not changed.

## Impact

- Code: `world/skills/sexual_acts/partner.py` only, plus a new test module,
  `world/skills/sexual_acts/tests/test_partner_catalog.py`.
- Collateral test update (same class as `sexual-catalog-solo`'s): `world/skills/tests/
  test_registry.py` pins the `SkillCategory.SEXUAL_ACT` key set in
  `test_per_category_key_sets_match_the_d4_classification_table`, and breaks the moment any new act
  registers. Its SEXUAL_ACT entry gains this change's fourteen keys; no other collateral file needs
  an edit (the empty-`unlock`-filter collateral `sexual-catalog-solo`/`sexual-catalog-shame`
  already shipped). See tasks.md section 6.
- No change to `_builder.py`, `__init__.py`, any other line module, `world/rules/action.py`, or
  `world/rules/rulebook/sexual.yaml` — every event this proposal's acts declare (`breast_sex_performed`
  only) is already wired by the shipped transition rulebook.
- Deferred, not delivered: 交合 and 深度交合 (vaginal intercourse and the `virgin`-breaking branch),
  pending a future proposal that gives `sexual-act-effects` a way to select a `sexual_events` entry
  from participant state at cast time (design.md D-2).
