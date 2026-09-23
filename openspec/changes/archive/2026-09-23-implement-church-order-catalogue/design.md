## Context

`implement-church-core` lands the substrate this change consumes: `db.church` (incl. `redeemed`), the `REDEEM_CATALOG` module, the `church redeem` rail, and `church.yaml` with its monotonicity + PASSIVE-polarity loader gates. The title machinery is fully landed (`world/lore/titles.py` frozen registry + loader validation, `world/rules/titles/planner.py::predicate_satisfied`, `world/rules/title_view.py` codex view, presentation mirror, `web/static/.../protocol/constants.js` client enum + its protocol test). See `proposal.md` for motivation; the design doc §5.9 enumerates the title touch surfaces.

## Goals / Non-Goals

**Goals:**
- Ship Series C/E (8 rows) + the 5-rung clergy ladder in ≤ one engineer-day (design §8 sizing contract; core is the other day).
- Both validator faces (Python + `titles.js`/`constants.js` mirror) move in the same change — a half-moved enum is exactly the class of bug the "four mirrors" requirement exists to prevent.
- Keep the iron rule mechanical: the loader gate and a catalogue-driven data contract test, never intent.

**Non-Goals:**
- No new commands (`church redeem list` grows automatically), no docs trio change, no combat rails (those are core's Series B), no merit-earning changes, no sub-project 2/3 surface.
- No uniqueness, office state, or 聖女-adjacent title of any kind.

## Decisions

**D1 — New category 聖職 (`clergy`) rather than reusing 公會/`guild`.** Guild titles are rank-pairings with the guild registry; the clergy ladder pairs with church redemption, and the codex tab is player-facing taxonomy. The category enum is closed and mirrored across four faces (Python `TitleCategory`, `web/webclient/presentation/title_codex.py` mirror, `protocol/constants.js`, `tests/protocol_title_codex.test.js`); all four move together. Tab order: 戰鬥／法術／探索／公會／聖職／風流韻事 (design lists the ladder alongside the existing tabs; placing 聖職 before the romance tab keeps mechanical tabs grouped — recorded in tasks so the mirror diff is mechanical).

**D2 — Predicate parameter reuses the existing `threshold: int` face.** `counter_threshold` already carries an int threshold; `church_skills_redeemed` needs exactly that one parameter — no new parameter kind, minimal loader-validation growth (the family simply references no registry face, like a pure counter).

**D3 — Evaluation is a pure read of `db.church.redeemed` length via a no-create helper.** Modeled on how `guild_rank_reached` reads current rank; the planner's event-log staging is bypassed for correctness (count is durable state), and re-grant dedupe is the registry's existing fixed-key rule. Unenrolled ⇒ 0 ⇒ false, no ledger materialization.

**D4 — 聖女 ban stays a GLOBAL loader validation.** The saintess-vessel spec's office-as-prose decision bans any fixed-title row naming the 聖女 office and design §9 reaffirms it unchanged — so the registry loader rejects any row whose display contains 聖女, not only clergy-category rows; scoping it to the ladder would silently weaken a reaffirmed invariant. Stays a data-contract test plus loader rejection.

**D5 — Series C effects are ledger/rulebook multipliers, not code hooks.** `poverty_vow`/`chastity_discipline`/`public_devotion`/`obedience` are accrual-row conditions + scale rows in `church.yaml` gated on `skill_owned` (the established `combat_modifiers.yaml` gating shape) — no new writer paths in `church.py` beyond reading existing status/venue state; `temple_endurance` is a scale row on the existing high-arousal defense-penalty computation.

**D6 — `rite_morning_devotion` raises the cap through the rulebook, not a hardcoded +1.** The cap row reads a skill-owned scale so a future Series E cap row composes; the test asserts exactly +1 for the shipped row.

## Risks / Trade-offs

- [Enum mirror drift between Python and `constants.js`] → the protocol test enumerates the closed set literally; both sides updated in one task with a same-commit test-green gate.
- [`obedience` depends on domination/submission status identity] → the evaluator reads the existing status-membership check used elsewhere in the rulebook; if the status vocabulary moves, the row's condition moves with it (no Python branch), covered by the boundary test.
- [Ladder grants fire during the redeem transaction] → desirable: titles ride the triggering action's atomic transaction per the existing fixed-title-grants requirement; a rolled-back redeem rolls the title back too (test asserts).
- [24-row total depends on core's archive landing first] → the batch `depends-on` plus the catalogue-completes-at-24 test make an out-of-order start fail loudly instead of silently duplicating rows.

## Migration Plan

Unreleased project: enum widening and appended rows need no migration. Rollback = revert; the ladder rows and Series C/E rows vanish together.

## Open Questions

None blocking: the ladder thresholds (design's tuning placeholders, 3/6/10/15/20 baseline) and Series C/E price finals are decide-and-record tasks in §1.
