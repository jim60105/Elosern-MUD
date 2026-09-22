## Context

The authoritative design is
`docs/superpowers/specs/2026-09-22-church-system-design.md` (approved, five
owner amendments baked in) §5.1/§7/§9. The substrate — `db.church`, the
`church.yaml` gates, `ChurchHost` on the two clergy roster rows, the derived
`church` venue set, the frozen catalogue shells — landed with
`implement-church-foundation`. This change makes the church joinable and lands
the owner's preset/lore amendments. See `proposal.md` for motivation and the
delta specs for requirements.

## Goals / Non-Goals

**Goals:**
- Ship `church join` end-to-end (three-stage flow, office branch, vestment
  handover) plus the `violet_altoria` surgery, lore realignment, join docs trio
  and the saintess-vessel delta replacement in ≤ 8 tasks.
- Land the enrollment office tests exactly as design §7 enumerates them
  (including the trickle-disarmed-pre-enrollment baseline and the no-uniqueness
  pair).

**Non-Goals:**
- No pray/offer (accrual change), no redeem/merit or Series A/B/D rows
  (redemption change), no charges primitive or combat rails
  (combat-ministry change), no title ladder or predicate family
  (order-catalogue change — this change only sanctions it via the
  saintess-vessel delta and asserts the family stays absent until then).
- No office uniqueness state, no holding check on the vestment, no quest
  channel, no affinity gate, no LLM in any mechanic.

## Decisions

**D1 — The vessel branch reuses the enrollment transaction, not a post-commit
hook.** Grant + event + ledger + vestment are one `transaction.atomic()`;
`saintess_vessel_granted` emits via `transaction.on_commit` exactly as preset
activation did, so the saintess-vessel spec's granted-event requirement
transfers verbatim through the delta's REMOVED+ADDED replacement.

**D2 — Vestment rides the `QuestReward` item-quantity rail, not the LLM
`give_item` intent.** The rail is already deterministic and transactional; the
dialogue intent would violate offline determinism. Presentation is authored
prose around the deterministic grant ("the celebrant places the robe in your
hands"). Unconditional handover is the owner's decision — the implementer must
NOT add a holding check.

**D3 — The saintess-vessel delta travels here and replaces, not modifies.** The
validator forbids a MODIFIED block that replaces scenarios and forbids
same-name ADDED+REMOVED in one delta, so the two preset-grant-era requirements
are REMOVED and the replacements carry new headings; the vessel tests are
re-annotated with the new IDs in this change. The §9.2 predicate-family
extension sanction is recorded here but the family itself ships in
order-catalogue; until then the church-count family is asserted ABSENT.

**D4 — The persona deletion is deletion.** The owner's amendment says successor
reframings count as failures: the temple-blessing and consecration sentences
are removed, the public identity loses the church clause, and the repo-wide
authored-content search for 聖女／聖女繼承人／consecration wording proves the
framing is gone rather than reworded around it.

**D5 — Docs trio splits by subcommand ownership.** This change documents only
`church join` (+ 入教／洗禮); accrual documents pray/offer, redemption
documents redeem/merit. `tests/test_command_docs.py` stays green at every step
because each change documents exactly the subcommands it lands.

## Risks / Trade-offs

- [Preset prose deletion leaves dangling narrative references elsewhere (other
  presets/lore quoting the consecration)] → the tasks include a repo-wide
  search for 聖女繼承人/consecration wording in authored content; only
  deletion, no reframing, per owner.
- [Re-annotating vessel tests against new IDs can silently orphan old
  annotations] → the traceability check runs after the deltas sync; both new
  IDs must resolve with zero unknown-annotation errors.
- [Lore realignment wording drifts from the shipped mechanics] → the landing
  requirement pins the replacement framing ("any female royal may be donated
  … consecrated at enrollment") and a search-proves the retired claim absent.

## Migration Plan

Unreleased project: no data migrations. The preset edit is a data row change
(no existing characters to migrate — pre-release). Rollback = revert the
change commits.

## Open Questions

None. All tuning this change reads (pray/accrual numbers) was decided in
foundation §1.
