# Design: implement-saintess-vessel

## Context

See proposal.md for motivation. The design source is `docs/lore/skill-trees/light.md` §「與相鄰系統的接縫」§聖女（容器） and §聖職者系統. The footnote's contract: the Saintess' `blessed_climax` IS the public 傾湧 miracle, her oath IS the engine `virgin` flag (already landed: `rulebook/sexual.yaml::virginity_once`, event `first_vaginal_penetration`, irreversible), and 「聖女機制不需要任何新增判定，全部讀既有狀態」. The only 〔提案〕 residue is the passive `saintess_vessel`: (a) 聖光涓流 — arousal idles in a 微興奮～中等 band fluctuation — and (b) public blessings cast as `sanctified_ward`/`goddess_blessing` ceremonial abbreviations additionally reading the holder's arousal tier.

Relevant landed machinery (verified against source):

- **Qualifier-passive shape**: `pain_to_pleasure`, `rapture_renewal`, `priestly_grace` are PASSIVE, `element="light"`, `ENHANCEMENT`, empty effects, no prerequisites — pure rule-gating rows read by `skill_qualified` (state_reactions) and `skill_owned` (combat_modifiers). Grant is via `db.skills.passive`, seeded by `PlayerPreset.passive_skills` (`data_pack_cards.py`) — this IS the 劇情/聖職敘階授予 surface. Practice-earning is structurally impossible: `world/rules/progression` rejects `SkillKind.PASSIVE` at both use- and booked-study award entries, and `cross_lineage_unlock` refuses passive nodes. These passives are also NOT conferrable (`validate_conferrable_skill` accepts only `StatMultiplyEffect`/`RuleTableEffect` rows) — the vessel deliberately stays in that non-conferrable class.
- **Pleasure writes**: only `world/rules/pleasure.apply_pleasure_gain` / `zero_pleasure`, the rulebook engine, and `sexual_state.decay_tick`. Bands (`sexual_pleasure.yaml`): 微興奮 15–34, 中等 35–59, 高度 60–84, 極限 85+.
- **Clock settlement** (`world/rules/clock.py::advance` → `_settle_buffs_and_decay`): per-quantum loop guarded by `_has_settlement_work(entity)` (early-exits when every decay field sits at its configured floor — a pleasure-0 holder has NO pending work), skipped entirely for `AdvanceSource.COMBAT`; the advance transaction snapshots/restores the `sexual` surface; there is no RNG-state snapshot, so dice inside the loop are NOT replay-stable.
- **Ceremonial read surfaces**: `sanctified_ward` mounts a `RecoveryRatePolicy` buff; its per-tick HP amount multiplies a cast-time `snapshot_grace_multiplier` computed in `world/rules/action/effects/buffs.py::recovery_snapshot_kwargs` from the caster's merged `recovery_arousal_scale` (0.1/ordinal, `priestly_grace`). `goddess_blessing` casts `heal:area` (authored fixed 2.8) + `buff_apply:light_blessing` (empty-modifier mount; the flat +18/60 s defense is its own `buff_active` row). The repo's established 恩典 pattern (`sister_vestment_grace`, `saintess_vestment_grace`, `holy_emblem_grace`) adds arousal-tier-gated rows ON TOP of authored values as independent status-sourced bonuses.
- **`_merge_adjustments` ADDs same-key numerics** — two rows on one scale key would silently double it.
- **Observability**: boundary events use `transaction.on_commit()` (the `clock_advance` precedent) so a rolled-back transaction leaves no log line.

## Goals / Non-Goals

**Goals:**
- Register `saintess_vessel` as the fourth clergy qualifier passive, 劇情-granted, practice-unearnable, non-conferrable.
- Make the holder's pleasure gauge idle visibly inside 微興奮～中等: never below 15, deterministic ±1 oscillation, no-op at/above 60 — all writes through `world/rules/`.
- Give each named public ceremony exactly one observable arousal-tier read that preserves the authored 2.8/+18 numbers.
- Record oath/grant boundary transitions through the `world.observability` facade, commit-bound.

**Non-Goals:**
- No re-implementation of `blessed_climax`, `bliss_apotheosis`, `pain_to_pleasure`, `rapture_renewal`, `priestly_grace`'s own scale, 露出計價, `virginity_once`, or `saintess_vestments`.
- No new arousal/exposure/virginity storage fields; no new `SexualState` trait.
- No title-system change of any kind (predicate families, bank path, removal path, fixed-title rows all frozen — decision D5).
- No new player commands: the ceremonies ARE `cast sanctified_ward` / `cast goddess_blessing`, so `docs/game/commands.md` / `command-reference.md` / `tests/test_command_docs.py` are untouched.
- No conferral story for the vessel (it joins the non-conferrable qualifier class).

## Decisions

### D1 — Registry row: qualifier passive, appended inside the clergy block

Row copies the `priestly_grace` builder shape exactly: `_skill("saintess_vessel", "聖女容器", <zh desc>, SkillKind.PASSIVE, TargetSpec.NONE, usable_out_of_combat=True, element="light", category=SkillCategory.ENHANCEMENT)` — effects omitted (the builder defaults it to the shared empty frozen list; the spec asserts *emptiness*, never the container type), no prerequisites, no lineage entry (§聖職者系統: 「被動不進系譜樹」). Registry order is observable → append immediately after `priestly_grace` in `data_utility_passives.py`. Alternative considered: a new `SkillCategory` — rejected (`rapture_renewal` precedent keeps clergy in `ENHANCEMENT`).

Grant: `"saintess_vessel"` added to the shipped Saintess preset's `passive_skills`. Preset activation is the validated creation path; import records may carry the key verbatim like any passive. This mirrors `reincarnation_boon_*` posture.

### D2 — 聖光涓流: ownership-aware decay floor + one deterministic post-settlement step

Two cooperating pieces, explicitly ordered:

**D2a — decay floor inside `decay_tick`**: the pleasure decay branch becomes holder-aware (no-create stored-skill ownership read): a holder's decay target is `max(15, band_floor − 1)`, and a holder at ≤ 15 with decay due is a no-op. Decay can therefore never take a holder below 微興奮.

**D2b — the trickle step, once per advance, after the quantum loop**: `saintess_trickle_step(entity)` in `world/rules/pleasure.py`, called from `advance`'s settlement staging as its own step AFTER `_settle_buffs_and_decay`, for non-COMBAT sources only (matching the loop's own combat posture — combat already floods arousal through stimulus/reactions), exactly once per `advance()` call (NOT per quantum — the quantum loop is a decay/buff cadence; the idle flavor is a per-advance step). Per call:
1. pleasure < 15 → `apply_pleasure_gain(entity, 15 − pleasure)` (pin-up; covers grant-time seeding and any sub-floor reduction).
2. 15 ≤ pleasure ≤ 59 → deterministic ±1: direction = `(entity_key_hash + resulting_world_tick) % 2` — a stateless parity of the committed-world-tick and the entity, so a rolled-back and retried advance recomputes the identical draw (no RNG consumed; no dice involved). Result clamped to [15, 59]. At 15 with a + draw the holder moves to 16; at 59 with a + draw clamps to 59; downward steps clamp at 15.
3. pleasure ≥ 60 → no-op; ordinary decay owns the descent, the step re-arms on band re-entry.

The holder at the floor therefore oscillates 15↔16 (level never leaves 微興奮), which satisfies 「常駐微興奮～中等浮動」 without a replay-unsafe RNG. Why the step is NOT inside `_has_settlement_work`'s quantum loop: (a) an idle holder at pleasure 0 has no other pending work and the loop early-exits before reaching any post-decay hook — the pin-up must run regardless, so the step lives outside that guard; (b) per-quantum firing would draw up to 180 steps in one sleep-length advance. The observable guarantee is 「never below 15 after any settlement, oscillation bounded to the band」 — not a frozen 15.

Why not a buff/mount: `RulebookBuff` rates are absolute per-tick gauge deltas with no band-floor or bidirectional concept; passive + declarative settlement (the `pain_to_pleasure` precedent) is cheaper and matches how the other clergy passives are consumed. Single-writer boundary intact: everything lives in `world/rules/`.

Balance: ±1 per advance against the 70-point climax journey is flavor; the clamp ceiling 59 can never open the 85 climax gate, and 60+ always requires stimulus.

### D3 — Two ceremonial reads, one per named ceremony

**Ward (`sanctified_ward`)**: new `combat_modifiers.yaml` row `saintess_vessel_blessing_scale: when {skill_owned: saintess_vessel} then {blessing_arousal_scale: 0.1}`, a key distinct from `recovery_arousal_scale` (the ADD-merge would double a shared key). `recovery_snapshot_kwargs` folds the grace as `1 + max(recovery_arousal_scale, blessing_arousal_scale) × cast-time arousal_ordinal`: a holder of vessel-only, priestly-only, or both gets exactly `1 + 0.1 × ordinal` — the tier is read once. Lore basis: §聖職者系統「不再額外乘一次此倍率，以免重複加成」.

**Goddess blessing (`goddess_blessing`)**: its authored 2.8 heal and +18 defense are fixed lore numbers and stay untouched; `light_blessing` deliberately gains NO recovery profile (the 节点資料表 authors no HOT for it). The tier read lands as one new 恩典 row on the established grace pattern (mirroring `saintess_vestment_grace`'s magnitude and the arousal-tier-gated `when` shape): `saintess_blessing_grace: when {skill_owned: saintess_vessel, buff_active: light_blessing, field: arousal, gte: 中等} then {defense: 6}` — while the holder's own降福 is live and she is at 中等 or above, the blessing's defense bundle is 18 + 6, displayed as its own status-sourced condition. This is an observable, testable, independent grace bonus that does not rewrite the authored +18 exception (same posture by which 修女聖袍恩典 +4 stacks independently of armor numbers).

Rejected: extending `recovery_snapshot_kwargs` to goddess_blessing (no recovery policy → unreachable), a vessel heal_gain row (vessel must not add general combat numbers; and rule-table conditions cannot gate on source skill anyway), a ground/HOT invention (un-authored).

### D4 — Observability is commit-bound and vessel-scoped

- `saintess_oath_broken`: emitted via `transaction.on_commit()` (the `clock_advance` precedent — fires immediately when no transaction is active) at the ONE place the `virgin` flag's irreversible flip commits (`sexual_transitions._apply_then` reports the `virgin` down-change only on the first flip), gated on `saintess_vessel` ownership so a generic character's first penetration does not claim a Saintess oath was broken. Context: `{"entity": str(entity), "event": "first_vaginal_penetration"}` — plain data only.
- `saintess_vessel_granted`: one `log_info` via `transaction.on_commit()` on successful preset activation that seeded the key, context `{"entity", "source": "preset", "passive": "saintess_vessel"}`.
- No logging inside the per-advance trickle step (steady-state chatter); the band is observable through status reads.

### D5 — Saintess title: narrative-only; no engine title state (decision recorded per assignment)

The 聖女 title stays prose/persona (`PresetIdentity.public`). The title-system's predicate families are closed and none expresses 王室獻任/聖座祝聖; its only bank path is a satisfied predicate and its only delete path is the player-voted epithet removal — a deterministic removal on the `virgin` flip would need a new family plus a new rules-layer writer, i.e. engine surface the footnote declares unnecessary (「不需要任何新增判定，全部讀既有狀態」). The oath itself is already engine state (`virgin`, seeded, irreversibly flipped by `virginity_once`); anything displaying the title reads the flag through existing stored reads. This change owns zero title state, therefore zero title rollback surface.

## Risks / Trade-offs

- [Trickle interacts with climax bookkeeping] → clamp ceiling 59, no-op ≥60, every write through `apply_pleasure_gain` so the two-step climax gate and wetness cascade behave as for any stimulus.
- [`max()` fold could mask a future third arousal-scale carrier] → naming discipline: `blessing_arousal_scale` IS the ceremonial-read key, `recovery_arousal_scale` stays the HOT-carrier key; consumer comment records the equal-0.1-by-design posture.
- [Parity draw is deterministic, not random] → intentional: replay-safety inside the advance transaction is worth more than true randomness for a ±1 cosmetic; the draw still varies across ticks and entities.
- [Grace stack 18+6 could look like re-balancing 女神降福] → it is an independent 恩典 row (status-display-sourced), precedented three times over in the same table; the authored +18 row is byte-identical.
- [Preset seeding is the only grant path until 劇情 tooling exists] → accepted, same posture as `reincarnation_boon_*`.

## Migration Plan

Unreleased project — no compat layer: registry row + preset field + rulebook rows + rules-layer branches land together. Rollback = revert commit; every touchpoint is append-only except the two small ownership branches in `decay_tick` and `recovery_snapshot_kwargs`.

## Open Questions

- None blocking. Whether a future 聖座祝聖 quest should mechanically bank the 聖女 title is deferred to that story's change; D5 already bounds what this change must not build.
