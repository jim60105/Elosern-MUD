## Why

`sexual-act-seeds` ships one unconditionally-available 羞恥線 seed, 撩起衣襬, and the one new
`sexual.yaml` rule row (`exposure_up_on_self_exposure`) it needs to raise the actor's own `exposure`
field — a mechanism no previously-shipped rule expressed. That proposal's design.md explicitly names
this proposal as the reuse point: "`sexual-catalog-shame`'s nine remaining acts reuse this same event
with no further rulebook change." Past the seed, `world/skills/sexual_acts/shame.py`'s `SHAME_ACTS`
tuple has nothing: a player who has exposed themselves five or more times has no further 羞恥線
content to unlock.

This proposal fills the remaining four tiers: three acts at `exposure_act_count >= 5`, two at
`exposure_act_count >= 20` (one compound-gated on `masturbation_count` too), two at
`watched_count >= 10`, and two at `exposure_act_count >= 50` (one compound-gated on `watched_count`
too) — nine acts total, all reusing `sexual-act-seeds`'s one rulebook row with zero further
`sexual.yaml` change.

## What Changes

- Add nine acts to `world/skills/sexual_acts/shame.py`'s `SHAME_ACTS` tuple:
  - **Tier 1** (`unlock={"exposure_act_count": 5}`, `TargetSpec.SELF`): 半露出·胸口, 半露出·下身,
    解開衣襟.
  - **Tier 2** (`TargetSpec.SELF`): 全露出 (`unlock={"exposure_act_count": 20}`) and 公開自慰
    (`unlock={"exposure_act_count": 20, "masturbation_count": 25}` — credits `masturbation_count`
    and `watched_count` alongside `exposure_act_count`, and reuses `masturbation_climax` alongside
    `self_exposure`).
  - **Tier 3** (`unlock={"watched_count": 10}`, `TargetSpec.AREA`): 挑釁凝視 (credits
    `hostile_act_count`, no exposure event — a battlefield taunt, not a further exposure act) and
    公開表演 (`unlock={"watched_count": 10, "exposure_act_count": 20}`, credits both counters plus
    `self_exposure`).
  - **Tier 4** (`TargetSpec.AREA`/`SELF`): 獻身姿態 (`unlock={"exposure_act_count": 50}`, AREA) and
    無恥宣言 (`unlock={"exposure_act_count": 50, "watched_count": 30}`, SELF).
- **Reuses `sexual-act-seeds`'s `self_exposure` event on eight of the nine acts** (every one except
  挑釁凝視, which targets enemies rather than raising the actor's own exposure, and — see design.md —
  no other new `sexual.yaml` row is added by this proposal. One disclosed engine-boundary
  consequence: the event fires on the cast's targets, so on the two AREA acts (公開表演, 獻身姿態) it
  raises each *target's* exposure rather than the performer's — see design.md D-6, and the delta
  spec pins this destination as a scenario).
- **Explicitly drops three flavour-only secondary effects** the source catalog document describes for
  three of these acts — 挑釁凝視's `accuracy` debuff, 獻身姿態's self-`defense` penalty, and
  無恥宣言's temporary "`shame` reads as `成癮`" buff — because `SexualActDef` has no field for a
  secondary buff/debuff effect (the same schema boundary `sexual-catalog-solo` (C2) identified and
  worked around for 拘束自慰). 挑釁凝視's case is **not** a pure drop: this proposal instead relies on
  the already-shipped `high_arousal_agility_accuracy_penalty` combat-modifier row firing as a natural
  side effect once a target's pleasure crosses the `高度` band — see design.md D-2 for why this is a
  faithful reuse, not a workaround.
- **Ships all three AREA acts (挑釁凝視, 公開表演, 獻身姿態) with `target_part="腰腹"`**, reusing the
  same neutral-part compromise `sexual-act-seeds` established for `partner_hand_hold` (its D-4):
  `SexualActDef`'s existing structural invariant requires a non-null `target_part` for any
  non-`SELF`/`NONE`, non-異種/神之秘法 act, and 羞恥線 has no natural erogenous-zone mapping for
  "an audience seeing someone expose themselves."

## Capabilities

### New Capabilities
- `sexual-catalog-shame`: the nine Tier 1–4 羞恥線 acts and their counter-based unlock thresholds.

### Modified Capabilities
- none — `sexual-act-registry`, `sexual-act-effects`, and `sexual-act-seeds`'s existing requirements
  (including the `exposure_up_on_self_exposure` rule `sexual-act-seeds` adds) are exercised, not
  changed.

## Impact

- Code: `world/skills/sexual_acts/shame.py` only, plus a new test module,
  `world/skills/sexual_acts/tests/test_shame_catalog.py`.
- Collateral test updates (shared with `sexual-catalog-solo`, its parallel batch-6 sibling): the
  same eight pre-existing test files pin the fresh-entity unlocked set or the SEXUAL_ACT category's
  key set and are updated to the unconditionally-unlocked (empty-`unlock`) subset:
  `test_registry_structure.py`, `test_handler.py`, `test_inventory.py`, `test_registry.py`,
  `test_status_query.py`, `test_combat_view.py`, `test_combat_session.py`, and
  `web/webclient/presentation/tests/test_character_panel.py`. The two proposals share these files by
  construction (batch 6's disjoint-ownership rule governs line modules and test modules, not the
  pre-existing pinned-registry expectations); whichever of the two lands first updates them.
- No change to `_builder.py`, `__init__.py`, any other line module, or `world/rules/rulebook/
  sexual.yaml` — this proposal is the first catalog line to add zero new rulebook content, reusing
  `sexual-act-seeds`'s single row across the entire remaining line.
- Deferred, not delivered: 挑釁凝視's dedicated `accuracy` debuff (superseded by a documented reuse of
  an existing combat modifier, not a gap); 獻身姿態's self-`defense` penalty; 無恥宣言's temporary
  shame-multiplier buff (both flavour-only, see design.md).
