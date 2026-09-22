## Why

The church design (`docs/superpowers/specs/2026-09-22-church-system-design.md` §8) splits the 24-row redemption catalogue across two changes because the catalogue alone exceeds the one-workday convention. `implement-church-core` ships the substrate (ledger, rulebook, `church redeem` rail, Series A/B/D); this change completes the ladder with the remaining 8 rows (Series C discipline passives + Series E utility) and the clergy title group (design §5.9) that gives the redeemed count a visible, spend-free reward.

## What Changes

- Series C discipline passives (5, pure-positive only, iron rule): `poverty_vow` (offering copper income and pray merit up — the original "shop prices rise" downside was removed per the iron rule), `obedience` (merit doubled while under a domination/submission status), `chastity_discipline` (pray merit +), `temple_endurance` (mitigates the existing high-arousal defense penalty by 25% — mitigation of an existing penalty is positive relative to baseline), `public_devotion` (merit from acts in public venues +).
- Series E utility (3): `rite_martial_blessing` (pre-fight single-stat buff, clock-cooled), `rite_shelter` (sanctuary rest bonus ledger flag), `rite_morning_devotion` (pray daily cap +1 — feeds the core loop).
- Their `church.yaml` rule rows + `REDEEM_CATALOG` rows (prices inside the design's bands) behind the same one-row-one-test correspondence and polarity gates.
- Clergy title group (design §5.9), modeled on how guild-rank titles ride `guild_rank_reached`:
  - New predicate family `church_skills_redeemed` (integer threshold parameter) evaluating `len(db.church.redeemed)` — the redeemed count only; `saintess_vessel` is never in `redeemed` and never counted. This is exactly the one family extension the core change's §9.2 saintess-vessel delta sanctions.
  - Fixed-title ladder rows: 虔信者 3 ／ 修女 6 ／ 神官 10 ／ 主教 15 ／ 樞機 20 (thresholds tuning; tuning placeholders decided and recorded in tasks) in a new 聖職 codex category. **No church title may display 聖女** — the office stays prose per the saintess-vessel spec.
  - All enumerated touch surfaces, none optional: the family enum + `TitlePredicate` parameter face + `predicate_satisfied` evaluator; the fixed-title registry loader validation; the closed codex `category` set in Python AND its `titles.js` panel-validator mirror (both sides, same change); one-row-one-test registry tests; codex panel tests.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `title-system`: the fixed-title registry requirement gains the `church_skills_redeemed` predicate family and the 聖職 category in its validated vocabulary, and the codex OOB/WebClient requirement's category-tab vocabulary gains 聖職 on both validator faces; two ADDED requirements pin the family's evaluation contract and the ladder (incl. the 聖女 display ban).
- `church-ordination`: ADDED requirements for the Series C/E rows and their rule rows (the A/B/D requirement is untouched — the catalogue reaching 24 rows is additive).

## Dependencies

depends-on: implement-church-core

The ledger (`db.church.redeemed`), the `REDEEM_CATALOG` engine + `church redeem` rail, the `church.yaml` loader with its polarity gate, and the §9.2 predicate-extension sanction all land there; this change queues behind it (its archive syncs `church-ordination`'s main spec first).

Size: ≤ one engineer-day (design §8 second half: 8 rows + the title ladder + both validator faces).

## Impact

- `world/lore/church/` `REDEEM_CATALOG` — 8 appended rows (Series C/E share the core's module).
- `world/skills/registry/` — 8 new `SKILL_REGISTRY` rows; `world/rules/rulebook/church.yaml` — Series C/E rows.
- `world/lore/titles.py` (family enum parameter face, 5 ladder rows, 聖職 category), `predicate_satisfied` evaluator, registry loader validation, `titles.js` panel-validator mirror + codex panel tests, `.github/evennia-shards.json`.
- No player-command surface change (`church redeem list` prints the grown catalogue automatically) → docs trio untouched.
- No compat layers, no migrations (unreleased project).

## Batch:

depends-on: implement-church-core

Code-conflict notes: appends to `REDEEM_CATALOG`, the skill-registry clergy block, and `church.yaml` — all owned by the core change; must not start before core archives. Title-side files (`world/lore/titles.py`, evaluator, `titles.js`) are owned by no other active change at proposal time.
