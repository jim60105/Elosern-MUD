# Tasks: implement-saintess-vessel

Traceability convention (verified against `tools/spec_traceability.py::_normalize_identifier`): annotation IDs are the requirement name after NFKC + casefold with every non-ASCII alphanumeric run STRIPPED (the regex is `[^0-9a-z]+` → hyphen — CJK does not survive it). The exact IDs for this delta are:

1. `saintess-vessel-is-a-granted-only-clergy-qualifier-passive`
2. `saintess-trickle-pins-the-holder-s-idle-arousal-inside-the-idle-band`
3. `each-named-public-blessing-ceremony-reads-the-holder-s-excitement-tier-exactly-once`
4. `the-vessel-adds-no-combat-numbers-beyond-the-two-ceremonial-reads`
5. `the-oath-flip-and-vessel-grant-are-observable-through-the-facade-without-title-state`

Any NEW test module MUST be registered in `.github/evennia-shards.json` under its owning shard (unregistered modules silently never run).

## 1. Registry and grant surface

- [ ] 1.1 Append the `saintess_vessel` PASSIVE row (聖女容器, `element="light"`, ENHANCEMENT, `TargetSpec.NONE`, omitted/defaulted empty effects, no prerequisites) immediately after `priestly_grace` in `world/skills/registry/data_utility_passives.py`; verify registry import succeeds and update roster-enumerating tests ONLY where they list shipped clergy qualifier keys (the new key is PASSIVE/light/ENHANCEMENT with `usable_out_of_combat=True`, so the frozen `usable_out_of_combat=False` inventory stays untouched).
- [ ] 1.2 Add `"saintess_vessel"` to the shipped Saintess preset `passive_skills` in `world/lore/player_presets/data_pack_cards.py`; verify preset validation passes and activation writes the key into `db.skills` passive list.
- [ ] 1.3 New test module `world/lore/tests/test_saintess_vessel_grant.py` (annotated `covers_requirement` ID 1): row-shape assertions including empty effects collection (assert emptiness, not container type); a practice-award and cross-lineage-unlock probe proving the PASSIVE guards reject the key like the other three clergy passives; `validate_conferrable_skill("saintess_vessel")` raises like `pain_to_pleasure`; preset activation banks the passive and emits exactly one `saintess_vessel_granted` event via the commit seam. REGISTER in `.github/evennia-shards.json`.

## 2. 聖光涓流 (idle-band trickle)

- [ ] 2.1 Holder-aware decay floor in `world/rules/sexual_state/lifecycle.py::decay_tick` pleasure branch: holder decay target `max(15, band_floor - 1)`; holder at or below 15 with decay due is a no-op; ownership read is the no-create stored-skill check (never materializes a handler). Verify existing decay/cycle tests pass byte-identically for non-holders.
- [ ] 2.2 Add `saintess_trickle_step(entity, resulting_tick)` to `world/rules/pleasure.py`: sub-15 raised to exactly 15 via `apply_pleasure_gain`; inside [15,59] exactly one deterministic plus/minus 1 whose direction is a stateless parity of the resulting world tick and entity identity (NO dice, NO RNG), clamped to [15,59]; at or above 60 no-op. Call it from `world/rules/clock.py::advance` exactly once per advance, after the `_settle_buffs_and_decay` quantum loop, OUTSIDE the `_has_settlement_work` guard (an idle holder at pleasure 0 has no pending work and must still be pinned), for non-COMBAT sources only (matching the loop's combat posture).
- [ ] 2.3 New test module `world/rules/tests/test_saintess_vessel_trickle.py` (annotated `covers_requirement` ID 2): pinned-up from a fully idle holder (pleasure 0, no buffs) lands exactly on 15 in one advance; mid-band repeated advances stay in [15,59], move at most 1/advance, and visibly move; floor oscillation 15↔16 with level never reading 平靜; holder at 70 decays ordinarily and re-arms on band re-entry; a forced-fail-then-retry advance yields the identical direction and a single-apply value; non-holder settlement trace byte-identical. REGISTER in `.github/evennia-shards.json`.

## 3. Ceremonial blessing reads

- [ ] 3.1 Add TWO vessel rows to `world/rules/rulebook/combat_modifiers.yaml` after `priestly_grace_recovery_scale`: `saintess_vessel_blessing_scale` (`when: skill_owned saintess_vessel`, `then: blessing_arousal_scale 0.1`) and `saintess_blessing_grace` (`when: skill_owned saintess_vessel AND buff_active light_blessing AND field arousal gte 中等`, `then: defense 6`, mirroring the `saintess_vestment_grace` magnitude/shape); plus `status_display.yaml` code entries for both. Verify with one matching test per row in `world/rules/tests/test_combat_modifiers.py` (one-row-one-test convention) — including the negative case that the grace row does not match at 微興奮 and requires the holder's own live `light_blessing`.
- [ ] 3.2 In `world/rules/action/effects/buffs.py::recovery_snapshot_kwargs`, fold grace as one plus max of (`recovery_arousal_scale`, `blessing_arousal_scale`) times the cast-time arousal ordinal, with a comment recording the equal-0.1-by-design posture and the ADD-merge double-count hazard behind the distinct key. Do NOT give `light_blessing` a recovery profile; do NOT touch its authored +18/60 s row.
- [ ] 3.3 Extend `world/rules/tests/test_recovery_profiles.py` with the grace matrix: vessel-only ordinal 2 mounts 1.2; vessel+priestly ordinal 2 still 1.2 and never 1.4; priestly-only ordinal 3 still 1.3; neither mounts 1.0. In `world/rules/tests/test_light_buffs.py` (or sibling) assert a holder at 中等 with live `light_blessing` merges +18 authored plus independent +6 listed as two status-sourced conditions, and the authored +18 yaml row is byte-identical. Annotate ID 3 on the double-read-refutation, vessel-only ward, and goddess-grace-stack cases; annotate ID 4 on the bare-holder merged-bundle test (bundle contains exactly `blessing_arousal_scale`).

## 4. Oath observability (no title state)

- [ ] 4.1 Emit `saintess_oath_broken` in `world/rules/sexual_transitions.py::_apply_then` at the point the `virgin` down-change is reported (the first flip only — irreversibility already suppresses repeats), gated on `skill_owned saintess_vessel`, registered through `transaction.on_commit()` (the `clock_advance` precedent) with context `{"entity": str(entity), "event": "first_vaginal_penetration"}` — plain data, facade-only, zero title reads or writes. A non-holder flip emits nothing.
- [ ] 4.2 New test module `world/rules/tests/test_saintess_oath_observability.py` (annotated `covers_requirement` ID 5): holder flip emits exactly one event at commit and `title_collection`/`title_equipped` are byte-identical; a rolled-back transaction emits nothing; a non-holder flip emits nothing; a repeat `first_vaginal_penetration` after the flip re-emits nothing; `TitlePredicateFamily` members and fixed-title rows enumerated unchanged. REGISTER in `.github/evennia-shards.json`.

## 5. Integration and gates

- [ ] 5.1 Run the observability lint gate over the touched modules and confirm zero findings (facade-only logging, contained failures, comment-tagged intentional suppressions).
- [ ] 5.2 After the delta syncs to main specs, run `uv run --locked python -m tools.spec_traceability check` and confirm all five IDs above resolve with zero uncovered requirements and zero unknown-annotation errors.
- [ ] 5.3 End-to-end smoke as one registered integration test (in the trickle module): activate the Saintess preset, advance the clock several quanta, cast `sanctified_ward` at 中等 arousal — observe pleasure pinned inside [15,59] with visible movement, mounted HOT grace multiplier 1.2, and exactly one `saintess_vessel_granted` log event at commit.
