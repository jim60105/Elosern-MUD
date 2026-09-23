# Design: implement-holy-rite-cast-rail

## Context

Parent design: `docs/superpowers/specs/2026-09-23-holy-rite-cast-rail-design.md` (§4–§6 approved by
the requester). Depends on `add-holy-rite-category` for the `holy_rite` category. The cast rail is
the unified pipeline (`cast` → `settle_out_of_combat_cast` → `ActionResolver.resolve` step-1..8 →
one commit point with per-surface snapshot/restore → `clock.advance(COMMAND)` in the outer
transaction). The `session_stamp` handler in `world/rules/action/effects/church.py` is the shipped
precedent for a church-flavoured handler staging against a snapshotted surface. The two Series E
engine APIs in `world/rules/church.py` are bare writers today — no transaction, no snapshot, no
clock — and `shelter_rest_flag` has no reset path.

## Goals / Non-Goals

**Goals:**
- `cast rite_martial_blessing` / `cast rite_shelter` work end-to-end through the rail with the
  existing safety system: stable rejections, snapshot/restore, one COMMAND time charge.
- Rite state (cooldown stamp, shelter day marker) lives in the `db.church` ledger, which becomes a
  snapshotted surface; single-writer audit survives (mutators stay in `church.py`).
- Delete the engine APIs in a clean cutover; re-anchor their tests and the traceability pin.
- `rite_morning_devotion` becomes PASSIVE, honest to its ownership-triggered mechanic.

**Non-Goals:**
- No rails for the 10 effect-less future-content rows (Series B heal/cleanse/… and the Series D
  acts) — documented future content stays as-is under `holy_rite`.
- No player commands (`church bless`/`church shelter` explicitly rejected in favour of the rail).
- No new transaction machinery, no UI, no compat layers or data migrations.

## Decisions

**D1 — Reuse the safety system wholesale (requester's option B).** `"church"` joins
`SNAPSHOTTED_SURFACES` in `world/rules/action/contracts.py` and `("church", None)` joins
`_ENTITY_SURFACES` in `world/rules/cast_settlement.py`. The `contracts.py` set is only the
registration gateway: the actual snapshot/restore engine is the per-surface dispatcher
`_snapshot_touched`/`_restore_touched` in `world/rules/action/transaction.py`, where every
non-entity surface (`quest_log`, `wallet`, `inventory`, …) earned its own explicit
`_attribute_snapshot` branch — `"church"` gets the same branch, in the wallet/inventory shape
(an attribute-keyed snapshot restored via `_restore_attribute`), not an entity-aggregate key.
Membership alone is not the rollback guarantee; the branch is. Alternative (a bespoke pray-style
settlement inside the handlers) rejected: it duplicates machinery the requester explicitly asked
to reuse. Naming hazard: `_ENTITY_SURFACES` exists twice with different shapes — the
`frozenset` of surface names in `transaction.py` (the entity-aggregate gate; do NOT extend it)
versus the `(attribute-key, category)` tuple in `cast_settlement.py` (the settlement snapshot
list; this change's addition target).

**D2 — Grammar on the closed set.** `rite_blessing:<buff-key>` (typed payload, `self_buff_apply`
grammar twin) and bare `rite_shelter` join `parse_effect` in `world/skills/effects.py`; the registry
fails at import on any payload outside their grammar. Handlers register in
`world/rules/action/effects/church.py` with surfaces `{"church","buffs"}` / `{"church","traits"}`.

**D3 — Handler gates stay in step 5, not the shared preview.** The four `RITE_*` rejections fire at
staging like every other handler-raised gate; `action_preview.py` keeps mirroring only pre-staging
steps. Consequence: the combat panel may show a cooled-down blessing enabled until step 5 says
otherwise — consistent with every buff-already-active-style gate today.

**D4 — Ledger shape re-pin (no compat).** Cooldown stamp: `db.church["blessing_last_tick"]`
(replaces `db.martial_blessing_last_tick`). Shelter marker: `db.church["daily"]["shelter"]`
(replaces root `shelter_rest_flag`). Both writers normalise the day block exactly as `pray_step`
already does (`daily.day != today → daily.clear()`), so readers compare `daily.day` to today and
the prayer day-rollover resets shelter with zero new code. Unreleased project: stale attributes just
disappear.

**D5 — Morning devotion → PASSIVE.** Registry `SkillKind.PASSIVE`; `REDEEM_CATALOG` row keeps the
same key/price, `grant_owned_skill` writes by kind into `db.skills.passive`; `daily_cap_bonus`
already reads both stores, so the cap bonus is unaffected. The `(ACTIVE: …)` wording in the
church-ordination main spec is amended by this change's delta.

**D6 — Values stay rulebook-owned.** Cooldown seconds, buff stat/magnitude, and the `rest_bonus`
hp/sp amounts keep reading `church.yaml` accrual/rest rows through existing accessors; handlers add
zero Python constants. The `martial_blessing` buff definition and `combat_modifiers.yaml` row are
untouched.

**D7 — Clean cutover deletions.** `cast_martial_blessing`, `apply_shelter_rest`,
`MartialBlessingReason`/`Error`, `ShelterReason`/`Error` deleted with their tests' old anchors;
`Series E utility rows feed the core loop`'s `covers_requirement` anchor moves to the new
resolver-face test (literal IDs per `docs/development/spec-test-traceability.md`). No requirement
headers rename in this change, so existing slugs stay parseable mid-flight.

**D8 — Hard sequencing on change 1's ARCHIVE, not its proposal.** Task 2.3 (and the panel/kind
test re-pins) may only run once `add-holy-rite-category` is applied AND archived with its specs
synced into `openspec/specs/`: `tools.spec_traceability` parses main specs only, and the
classification tests re-pin against the seven-category main spec. While change 1 is still an
active delta, change 2's registry/test edits would contradict the still-current six-category
contract and neither change's gates can both be green.

## Risks / Trade-offs

- **Ledger-on-rail is new surface coverage**: a handler bug could corrupt `db.church` mid-commit;
  mitigated by the rollback-proof tests (ledger byte-identical after injected commit failure) and by
  the mutator indirection (handlers never touch the dict directly).
- **Ledger normalisation duplication**: blessing/shelter writers must replicate `pray_step`'s
  day-block normalise — one shared helper in `church.py`, not three copies.
- **Preview honesty**: cooldown state is invisible to the combat panel (D3); acceptable, matches
  existing handler-gate behaviour, and the `cast` path still rejects with a stable zh-TW line.
- **Test anchor churn**: the Series E block in `test_church_rulebook.py` re-targets the resolver
  face; the classification anchor for morning devotion's kind swap is a one-row delta.
