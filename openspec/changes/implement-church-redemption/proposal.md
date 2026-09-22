## Why

The owner capped this sub-project at eight hours (one engineer-day) per
OpenSpec change; the superseded `implement-church-core` is re-cut into four,
and this is its **redemption layer**: the ordination ladder itself — the
price-band finals for the 16 Series A/B/D keys, their `SKILL_REGISTRY` rows,
the grown `REDEEM_CATALOG`, and the `church redeem` / `church merit` rail that
makes the 「聖職敘階授予」 channel real. The ledger, rulebook gates, and
catalogue shells landed with `implement-church-foundation`; enrollment with
`implement-church-enrollment`; the earning behaviours (pray/offer/climax
accrual) with `implement-church-accrual`. Authoritative design:
`docs/superpowers/specs/2026-09-22-church-system-design.md` §5.5/§5.6/§7.

## What Changes

- Price-band finals task (moved from the superseded core's tuning section):
  assign each of the 16 Series A/B/D keys a final `merit_price` inside the
  design's bands (entry 300–600, mid 1200–2500, high 4000–8000; Series A
  qualifiers entry-tier except the three legacy passives at mid;
  `rite_lamb_mark`/`rite_martyrdom_vow` high; the Series D high rows carry the
  only catalogue-internal prereq chain), recorded in the `REDEEM_CATALOG`
  module docstring.
- Register the 16 `SKILL_REGISTRY` rows: Series A clergy qualifier passives
  (`pain_to_pleasure`, `priestly_grace`, `rapture_renewal` first-time
  catalogue entry + new `vow_of_service` ledger multipliers), Series B rite
  actives (eight, incl. `rite_lamb_mark`/`rite_martyrdom_vow` — their COMBAT
  rails land with `implement-church-combat-ministry`), Series D sexual-ministry
  actives (four, doubling as advanced `OFFERING_CATALOG` rows by shared key).
  No lineage tree membership; the pipeline is the only acquisition path.
- Grow `REDEEM_CATALOG` with the 16 priced rows behind the foundation's
  validator; the offering menu picks up the advanced Series D rows through the
  accrual change's projection with zero code change there.
- `church redeem [list|<key>]` and `church merit` (read-only ledger print):
  validate (exists ∧ unredeemed ∧ merit ∧ catalogue-internal prereqs), one
  transaction — subtract merit → sanctioned granted-skill write
  (`db.skills.passive`/`db.skills.active` per kind) → append `redeemed` →
  `church_skill_redeemed`; every failure a stable rejection leaving everything
  byte-identical; no repeat redemption; mid-redemption forced-fail rollback
  test.
- Negative-set + guard-green tests: `saintess_vessel` ∉ catalogue ever and
  `church redeem saintess_vessel` is the unknown-key rejection; the
  practice/unlock/conferral PASSIVE guards stay untouched with their tests
  green (the pipeline is the channel, not a bypass).
- Docs trio for the `church redeem` / `church merit` surface,
  `tests/test_command_docs.py` green.

## Capabilities

### New Capabilities
None — the `church-ordination` capability is opened by
`implement-church-foundation`; this change's delta purely ADDS its redemption
requirements onto it.

### Modified Capabilities
None. The `OFFERING_CATALOG` grows by data only (advanced rows append behind
the foundation's validator and the accrual change's projection).

## Dependencies

depends-on: implement-church-foundation
depends-on: implement-church-enrollment
depends-on: implement-church-accrual

Needs the ledger + `redeemed` list and the shell validator (foundation), the
enrolled initiate whose merit is spent (enrollment), and the earning rails
that produce spendable merit plus the docs-trio split point (accrual).
Consumes verbatim: the sanctioned granted-passive/granted-skill write path
(`lineage_ownership_closure` shape), integer copper, `world.observability`.
`implement-church-combat-ministry` queues behind this change (the two combat
rite rows exist here; their rails land there). `implement-church-order-catalogue`
queues behind this change (it appends Series C/E to the redemption-grown
`REDEEM_CATALOG`, clergy registry block, and `church.yaml`).

Size: ≤ 8 tasks / one engineer-day.

## Impact

- New: `church redeem` / `church merit` subcommands on `commands/church.py`;
  the redemption section of `world/rules/church.py`.
- Edited: `world/skills/registry/` (16 new `SKILL_REGISTRY` rows appended as a
  clergy block; the three legacy passives stay where they are — catalogue
  entry is a `REDEEM_CATALOG` fact, not a row move),
  `world/lore/church/` `REDEEM_CATALOG` (+16 priced rows) and
  `OFFERING_CATALOG` (+ advanced rows),
  `world/rules/rulebook/church.yaml` (+ Series A/B/D rule rows where a rite's
  effect is rulebook data), `.github/evennia-shards.json`, the docs trio.
- No lineage membership, no bypass of the PASSIVE guards, no LLM
  participation, no compat shims (unreleased project).

## Batch:

depends-on: implement-church-foundation
depends-on: implement-church-enrollment
depends-on: implement-church-accrual

Code-conflict notes: owns the price finals, `REDEEM_CATALOG` content, the
clergy skill-registry block, and `church.yaml` price/rule additions —
`implement-church-order-catalogue` appends after this change archives, and
`implement-church-combat-ministry` registers no new rows (its two rite rows
exist here) but owns their rail files (`monster_behaviour.py`,
`defeat_aftermath/violation.py`, the buff declaration). No other active change
exists at proposal time.
