## Why

`sexual-act-seeds` ships one unconditionally-available 戰鬥線 seed in `world/skills/sexual_acts/
combat.py`'s `COMBAT_ACTS` tuple — `combat_tease` (挑逗, 腰腹/腰腹, `actor_pleasure_ratio=0.4`,
`resistible=True`, crediting `hostile_act_count` on the actor only). Past that seed, the line has
nothing: a character who has used a hostile sexual act five or more times has no further 戰鬥線
content to unlock, even though `hostile_act_count`, `climax_count`, and `climax_extension_count` —
the three counters this line trains against or reads — are already fully wired by `sexual-counters`
(B2), `sexual-act-effects` (B5), and the climax-settlement clock.

This proposal fills four of the five remaining tiers: two acts at `hostile_act_count >= 5`, three at
`hostile_act_count >= 20`, two at `hostile_act_count >= 40` (compound-gated on `climax_count` too),
and one AREA act at `hostile_act_count >= 80` (compound-gated on `climax_extension_count`) — eight
acts total. It does **not** ship 搾取 (Tier 4, `unlock={"hostile_act_count": 60,
"climax_extension_count": 10}`), the source catalog's SP-drain act; see "What Changes" and design.md
D-2 for the structural reason.

## What Changes

- Add eight acts to `world/skills/sexual_acts/combat.py`'s `COMBAT_ACTS` tuple, every one
  `TargetSpec.SINGLE` or `TargetSpec.AREA`, `resistible=True`, `actor_counters=("hostile_act_count",)`,
  `participant_counters=()` — matching the shipped seed's asymmetric crediting (only the aggressor's
  own ledger grows; a hostile target is never credited for having been targeted):
  - **Tier 1** (`unlock={"hostile_act_count": 5}`): 挑逗·耳語 (耳朵), 挑逗·觸碰 (腰腹).
  - **Tier 2** (`unlock={"hostile_act_count": 20}`): 魅惑 (頸項) and 束縛愛撫 (大腿) — both rely on
    the already-shipped `high_arousal_agility_accuracy_penalty` combat-modifier row
    (`{field: arousal, gte: 高度} → {agility: "-20%", accuracy: -15}`) firing as a natural side
    effect once repeated casts push a target's pleasure into the `高度` band, delivering the source
    catalog's "accuracy debuff" and "agility debuff" flavour from one already-shipped mechanism
    rather than two new dedicated ones (the same reuse `sexual-catalog-shame`'s 挑釁凝視 established
    for this exact combat-modifier row) — and 強制快感 (私處), this tier's highest raw
    `base_pleasure`.
  - **Tier 3** (`unlock={"hostile_act_count": 40, "climax_count": 30}`): 強制絕頂 (私處) and
    連續責め (臀部), both tuned so their target-side pleasure gain clears
    `climax_extension_threshold` (`20`) even at the worst-case sensitivity/shame combination, making
    them reliable climax-extension tools; 連續責め declares a higher `actor_pleasure_ratio` for its
    "stronger self-gauge cost" flavour.
  - **Tier 5** (`unlock={"hostile_act_count": 80, "climax_extension_count": 30}`,
    `TargetSpec.AREA`): 絕頂支配 — an AREA-target restatement of 強制絕頂's exact tuning, letting one
    cast extend every hostile target present.
- **Explicitly defers 搾取** (Tier 4, `unlock={"hostile_act_count": 60, "climax_extension_count":
  10}`): the source catalog describes it as transferring "a share of the target's climax SP loss" to
  the actor, but no field in `SexualActDef` or effect handler in `world/rules/action.py` moves a
  resource between two entities — the schema expresses pleasure gain, counter increments, and
  rulebook events only, never a cross-entity resource transfer. See design.md D-2.

## Capabilities

### New Capabilities
- `sexual-catalog-combat`: the eight Tier 1-3/5 戰鬥線 acts and their counter-based unlock
  thresholds.

### Modified Capabilities
- none — `sexual-act-registry`, `sexual-act-effects`, and `sexual-act-seeds`'s existing requirements
  (including the shipped `COMBAT_ACTS` seed row) are exercised, not changed.

## Impact

- Code: `world/skills/sexual_acts/combat.py` only, plus a new test module,
  `world/skills/sexual_acts/tests/test_combat_catalog.py`.
- No change to `_builder.py`, `__init__.py`, any other line module, `world/rules/action.py`, or
  `world/rules/rulebook/{sexual,combat_modifiers}.yaml` — this proposal declares no `sexual_events`
  and adds no new rulebook row; 魅惑/束縛愛撫 reuse an already-shipped combat-modifier row unchanged.
- Deferred, not delivered: 搾取 (an SP-transfer act), pending a future proposal that gives the
  effect-handling schema a cross-entity resource-transfer primitive (design.md D-2).
