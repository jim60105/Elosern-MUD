## Context

The authoritative design is
`docs/superpowers/specs/2026-09-22-church-system-design.md` §5.5/§5.6/§7. The
substrate (ledger with `redeemed`, `REDEEM_CATALOG` shell + validator,
`church.yaml` gates) landed with `implement-church-foundation`; enrollment with
`implement-church-enrollment`; the earning rails (pray/offer/climax accrual,
`church_pray`/`church_offering_*` events) with `implement-church-accrual` — so
by now an initiate actually has spendable merit. This change turns the shell
into the ladder. See `proposal.md` for motivation and the delta spec for
requirements.

## Goals / Non-Goals

**Goals:**
- Decide the 16-key price finals inside the design's bands and ship the rows +
  the redeem/merit rail in ≤ 8 tasks.
- Keep the channel sanctioned, not a bypass: writes go through the canonical
  granted-skill path; the practice/unlock/conferral PASSIVE guards stay
  untouched and their tests green; `saintess_vessel` is pinned absent forever.

**Non-Goals:**
- No `charges` buff primitive, no lamb-seal narrowing, no martyr-vow pool
  filter (`implement-church-combat-ministry` — it registers no new rows; the
  two rite rows exist here with their declarations).
- No Series C/E rows, no title ladder (order-catalogue change), no new ledger
  primitives, no changes to the offering projection (advanced rows join the
  menu by data only).

## Decisions

**D1 — Price finals are this change's task, not foundation's.** The rows being
priced land here; keeping the decide-and-record task beside the data keeps the
band-membership test, the catalogue docstring table, and the registry rows in
one commit. Foundation keeps the accrual/pray/acceptance finals because every
change prices against those.

**D2 — Catalogue entry ≠ registry row move.** `pain_to_pleasure`,
`priestly_grace`, `rapture_renewal` already exist in
`data_utility_passives.py`; first-time catalogue entry is a `REDEEM_CATALOG`
fact plus the new clergy block's `vow_of_service` and the new actives — the
legacy rows stay where they are.

**D3 — The redeem write is the sanctioned granted-skill channel, split per
kind.** PASSIVE rows write `db.skills.passive`, ACTIVE rows
`db.skills.active` — same shape as preset activation's
`lineage_ownership_closure` write. The guards' green tests are part of the
requirement's acceptance, not a courtesy.

**D4 — The two combat rite rows register here, rails land next door.** This
change's tasks register all 16 rows and their data tests; combat-ministry owns
`monster_behaviour.py`, `defeat_aftermath/violation.py`, and the buff
declaration, so no seam crosses mid-file. The rows are redeemable inert actives
in between (their cast effects beyond declaration are the combat change's
requirement).

**D5 — Prereq chains only on the Series D high rows.** Catalogue-internal
prereqs are a plain key list; every other row is prereq-free, keeping the
grind legible (design §5.5).

## Risks / Trade-offs

- [Series D advanced offering rows change the offering menu's shape under the
  accrual change's tests] → the projection is data-driven; the accrual tests
  own "menu == owned act keys", which grows with the catalogue by construction.
- [A price final straddling a band boundary quietly breaks the band test] →
  the task asserts every price lands strictly inside its assigned band, table
  recorded in the module docstring.
- [Registered-but-railless combat rite rows tempt an early half-rail] →
  forbidden: declarations only here; the rails are combat-ministry's
  requirements and tests.

## Migration Plan

Unreleased project: no data migrations. Rollback = revert; rows and rail
vanish together.

## Open Questions

None. The price finals are this change's decide-and-record task per design
§5.5's placeholder bands.
