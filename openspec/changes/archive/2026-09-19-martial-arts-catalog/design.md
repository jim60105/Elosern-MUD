## Context

The lore doc is the node-data authority and was reconciled against the engine before this change was
written: every rider it prices is expressible with shipped vocabulary, and the three that were not
(partial defense ignore, a forced critical against low-HP targets, a battlefield-wide percentage
defense debuff from a single-target strike) were rewritten in the doc rather than bolted onto the
engine. The reconciliation facts that constrain authoring:

- `DamagePolicy` offers `extra_strikes` in `(1, 2)` predicate-free, `bypass_defense` as an all-or-
  nothing skip, and `max_hp_fraction` as the devastation rider; every shipped devastation rung uses
  `0.10`.
- `evaluate_combat_modifiers` merges flat `defense`, `atk_phys`, `agility_flat` and `accuracy` terms;
  `defense` has no percentage-aware consumer, and `agility_flat` negatives ship at `-3` (`ice_slow`)
  and `-8` (`ice_frost_mire`). Flat `atk_phys` ships at `+5` on two ownership passives; the timed
  ladders that exist are `defense` rows reaching `+12`/`+18`.
- Buff riders are ordinary effect components: they settle with the action and are NOT gated on the
  strike's hit roll. The lore doc records this and avoids 「命中後」 wording.
- `buff_apply` on a SINGLE skill lands on the selected target; audiences filter the validated target
  pool and never add unselected entities, so no rider in this tree can splash.
- `CastCondition` already admits `skill_owned`, evaluated by `world/rules/spell_conditions.py`.
- Tip caps derive as the maximum `min_proficiency` over consuming edges, with the canopy default from
  `progression.yaml`; the doc's cap column was checked against that derivation and matches, so no cap
  is authored anywhere.

## Goals / Non-Goals

**Goals:**

- Land the authored 14-node two-tree lineage as registry data plus three rulebook rider rows.
- Retire the one stale key (`dual_blade_mastery`) without leaving an alias.
- Prove the family behaviorally with synthetic compositions only.

**Non-Goals:**

- Any engine change. If a D1 mechanic turns out to be missing at implementation, that is a defect in
  its owning shipped surface and is fixed there — never bolted onto this catalog.
- Data-contract tests of any shape: no key-set equality, no node-table echo, no cost/cap/tier
  assertions, no lineage-edge catalog test. (D5 records what this costs.)
- Touching `basic_attack`, `light_sword_style`, `dual_wield_style` or `flee`, and touching the 情慾/
  神秘 blocks the in-flight divine wave owns.
- `state_reactions.yaml`: zero martial reaction rows. Every rider is a same-settlement effect
  component.

## Decisions

**D1 — The authored node data.** All nodes are `SkillCategory.MARTIAL_ARTS`, `FactionConstraint.ANY`,
`usable_out_of_combat=True`, ACTIVE, with `cost={"sp": N}` and no `group`.

劍術 route — `element=None`, `effects=["damage:none:physical"]` (the predecessor's token):

| key | label | target | SP | prerequisites | policy |
| --- | --- | --- | --- | --- | --- |
| `basic_swordplay` | 見習劍術 | SINGLE | 8 | — | coefficient 1.0 |
| `flowing_strikes` | 順勢連斬 | SINGLE | 16 | `basic_swordplay` ≥ 3 | 1.4, `DamagePolicy(extra_strikes=1)` |
| `tendon_sever` | 斷筋斬 | SINGLE | 24 | `flowing_strikes` ≥ 3 | 2.0, `+ buff_apply:martial_hamstring` |
| `whirlwind_slash` | 迴旋斬 | AREA | 22 | `flowing_strikes` ≥ 3 | 1.4 |
| `thousand_blade_art` | 千刃連斬 | SINGLE | 30 | `tendon_sever` ≥ 5 | 2.8, `DamagePolicy(extra_strikes=2)` |
| `blade_storm` | 劍刃風暴 | AREA | 28 | `whirlwind_slash` ≥ 5 | 2.0 |
| `blade_saint_arts` | 劍聖斬 | SINGLE | 38 | `thousand_blade_art` ≥ 8 | 4.0, `DamagePolicy(bypass_defense=True, predicate=())` |
| `thousand_army_slash` | 破軍斬 | AREA | 36 | `blade_storm` ≥ 8 | 2.8, `DamagePolicy(max_hp_fraction=0.10)` |
| `true_sword_saint` | 大劍豪 | SINGLE | 48 | `blade_saint_arts` ≥ 10 **and** `thousand_army_slash` ≥ 10 | 5.5, `DamagePolicy(bypass_defense=True, predicate=())`, `+ self_buff_apply:sword_saint_domain` |

影流刀術 route — `element="dark"`, `effects=["damage:dark:physical"]`:

| key | label | target | SP | prerequisites | policy | stance gate |
| --- | --- | --- | --- | --- | --- | --- |
| `shadow_slash` | 影斬 | SINGLE | 18 | — | 1.4 | no |
| `phantom_dance` | 幻影連斬 | SINGLE | 24 | `shadow_slash` ≥ 3 | 2.0, `DamagePolicy(extra_strikes=1)` | yes |
| `dual_blade_waltz` | 雙刃旋舞 | SINGLE | 30 | `phantom_dance` ≥ 5 | 2.8 | yes |
| `shadow_veil_execution` | 暗影獵殺 | SINGLE | 28 | `phantom_dance` ≥ 5 | 2.8, `+ buff_apply:shadow_wound` | yes |
| `shadow_dance_finale` | 暗影終劍 | SINGLE | 44 | `dual_blade_waltz` ≥ 10 **and** `shadow_veil_execution` ≥ 10 | 4.5, `DamagePolicy(bypass_defense=True, predicate=())` | yes |

The multi-effect nodes declare one `EffectPolicy` per effect in order: the damage policy first, a
default `EffectPolicy()` for the mount.

**D2 — The three rider rows and their two modifier rules.** All three are 60 s with
`stacking: refresh`, matching the shipped 60 s band the ice/wind/fire rows use for combat-scoped
riders.

- `martial_hamstring` — `polarity: debuff`, empty modifiers; rule `martial_hamstring_agility_penalty`
  (`when: {buff_active: martial_hamstring}` → `{agility_flat: -5}`). The value sits inside the shipped
  negative band (`-3` … `-8`) and is authored as a rule rather than on the row because that is how
  every shipped agility ladder settles.
- `shadow_wound` — `polarity: debuff`, `tick_interval: 10`, `modifiers: rate: {target: hp, delta: -8}`.
  Matches `fire_ignite`'s shipped 60 s / 10 s / `-8` shape exactly; kill credit rides the shipped
  damaging-gauge attribution, which derives the source from the acting entity.
- `sword_saint_domain` — beneficial, empty modifiers; rule `sword_saint_domain_atk_phys_bonus`
  (`when: {buff_active: sword_saint_domain}` → `{atk_phys: 12}`). No timed `atk_phys` row exists yet,
  but `atk_phys` is an already-merged flat bundle key read by `_adjusted_attack`, and the shipped
  timed `defense` ladder reaches `+12`, so this is a new row in an existing vocabulary, not a new
  consumer.

`status_display.yaml` must cover buff keys **and** modifier rule IDs (it fails closed on drift over
both), so this change adds five rows: the three buff keys (斷筋／暗影創傷 harmful, 劍豪之境
beneficial) and the two rule IDs.

**D3 — The stance gate starts above the root.** The lore requires 雙持劍術 for the shadow line but
also says outsiders 「從影斬一節起步」. `shadow_slash` is shipped and owned by a preset character, so
gating it would silently disarm an existing skill; the gate is therefore authored on `phantom_dance`
and everything above it. `dual_wield_style` stays out of the prerequisite graph entirely — PASSIVE
skills never accrue proficiency, so an edge to it could never be satisfied; the gate is a cast
condition, which is the vocabulary built for exactly this.

**D4 — `dual_blade_mastery` re-keys to `dual_blade_waltz` with no alias.** Same label, same target,
same SP, same effect; only the key changes, because `_mastery` is this project's element-mastery-
passive convention and the lore doc's own stale 「雙刀流・宗師級」 naming was the source of the
confusion. A cast of the retired key rejects as an unknown skill like any never-existing key. The one
preset row that names it moves in this change.

One observable content side effect to record: 悠花's preset declares the move directly, and
`dual_blade_waltz` sits behind `phantom_dance` ≥ 5, so the shipped activation closure
(`world/rules/character_creation.py:593`, `lineage_ownership_closure` + `seed_lineage_proficiency`)
will seed her `phantom_dance` ownership and the matching `shadow_slash` proficiency at activation.
Her ability to cast the move is preserved — that is what the closure is for — but her activated skill
list grows by one entry, which whoever reviews her character card next should expect.

**D5 — Evidence is behavioral only, and what that costs.** This is a deliberate departure from the
only precedent that exists. Both landed tree catalogs (fire and wind) added a `skill-lineage` content
requirement — 「the <element> lineage ships as the authored … tree with a two-parent canopy」 — backed
by a registered data-contract test pinning their real edges and thresholds. This change proposes no
`skill-lineage` delta at all, so the martial family is the first tree family to land with **no
lineage-shape contract of any kind**, not merely with less testing. Stated plainly so the decision is
made here rather than discovered later.

The ratified scope adds no data-contract
test, so the authored tree's shape is guarded by three things and not by a spec requirement: the lore
doc as node-data authority, the registry's own fail-closed load validation (DAG acyclicity, dangling
prerequisites, threshold bounds, effect parsing, audience legality), and the behavioral requirement's
canopy/branch scenarios exercised on synthetic trees. **Accepted trade-off:** a future edit that
changes an authored SP cost, coefficient or edge threshold in the shipped rows will not fail any
test — including a mis-resolved merge against `divine-mystery-catalog`, which edits the same file. The
cheapest way to close this without reopening the no-data-test decision, if it is ever reconsidered, is
a `skill-lineage` ADDED requirement pinning only the structure (two roots, the two branch points, the
two two-parent canopies and their thresholds) and no costs or coefficients. The existing category census key set in `test_skill_registry.py` is updated rather than deleted
— it is an existing data-contract test that would otherwise fail, and this change adds no new one.

**D6 — Two element policies in one family, on purpose.** The 劍術 route is plain steel and declares no
element; the 影流 route is 暗屬性 in the lore and keeps `dark`. The split is visible to players
(`SkillDetailPane` renders `skill.element` as a badge) and is exactly the intended reading: a shadow
art carries an affinity, a steel swordsman does not.

## Risks / Trade-offs

- **The authored balance is unguarded by tests** (D5). The mitigation is that the lore doc and the
  registry are the two authorities, and the doc carries the monotonicity argument for every rung.
- **Riders are not hit-gated.** A missed 斷筋斬 still applies 斷筋. This is shipped effect-component
  semantics, is recorded in the lore doc, and is uniform with every shipped mount; changing it would
  be a settlement change in `world/rules/action.py`, out of scope here.
- **`atk_phys: 12` is the largest flat attack bonus in the table** by a wide margin over the two `+5`
  ownership passives. It is a 傳奇-tier canopy rider on a 60 s timer gated behind two Lv.10 parents, so
  the reach is deliberate; the shipped timed `defense` ladder at `+12` is the calibration point.
- **The one-workday estimate is tight but precedented.** The nearest landed comparison is the wind
  catalog: 13 nodes, 7 buff rows, 6 modifier rules, census rows and one synthetic behavior module in a
  single change. This change is 14 nodes with fewer rulebook rows. The pressure point is task 4.1's
  disposable exploration preceding an eight-scenario behavior module; if the budget slips, the split
  that costs least is data-authoring (groups 1–3) in one session and the behavior module (group 4) in
  the next, kept in one change because the ADDED requirement covers both trees as one family.
- **Re-keying touches a preset.** 悠花's active-skill tuple is the only shipped reference; a missed
  second reference would surface as a preset validation failure at load, not as silent drift.
