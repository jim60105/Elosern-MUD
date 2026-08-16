## 1. Confirm the dependency surface this change reads and extends

- [x] 1.1 Confirm `world/rules/combat_session.py::_scan_friendly_fire`,
  `_snapshot_party_surfaces`, and `_restore_round_touched` still have their documented shape
  (nested `transaction.atomic()`, `AffinitySource`/`apply_affinity_change` import, the
  `companion_pks`-scoped snapshot). If the shared outer transaction's structure around the
  `_scan_friendly_fire` call site in `submit_player_action` has moved or changed, re-read that
  function in full before writing task 4.
- [x] 1.2 Confirm `world/rules/affinity.py::AffinitySource`, `apply_affinity_change`, and
  `NATURAL_CAP` still have their documented shape; confirm `world/rules/affinity_config.py`'s
  `_TOP_LEVEL_FIELDS`/`AffinityConfig` still validate `friendly_fire_penalty_per_hit` the way
  design.md Decision 4 describes.
- [x] 1.3 Confirm `world/rules/event_log.py::EventEntry` still has fields `kind`, `actor`, `target`,
  `data`, `text_template` — the contract in design.md Decision 1 depends on this exact shape.
- [x] 1.4 Confirm `sexual-resist-contest` (`B6a`)'s `ResistVerdict` field names
  (`resisted`, `auto_comply`, `roll`) are unchanged from what this proposal's spec assumes. Do not
  import from `world/rules/sexual_resist.py` — this proposal only needs the field *names* to match
  its own documented `EventEntry.data` contract, not the module itself (design.md Non-Goals).

## 2. `world/rules/rulebook/affinity.yaml` and `world/rules/affinity_config.py`

- [x] 2.1 Add `sexual_forced_penalty` to `affinity.yaml`'s top level, a plain non-negative integer,
  distinct in value from `friendly_fire_penalty_per_hit` (design.md Decision 4 — pick any
  distinguishable placeholder value; exact balance tuning is not this proposal's concern).
- [x] 2.2 Add `sexual_forced_penalty` to `affinity_config.py`'s `_TOP_LEVEL_FIELDS` and to
  `AffinityConfig`'s dataclass fields, with the same non-negative-integer validation
  `friendly_fire_penalty_per_hit` already has (reuse the existing validation helper if one exists
  rather than duplicating the check).
- [x] 2.3 Confirm `get_config().sexual_forced_penalty` is readable exactly like
  `get_config().friendly_fire_penalty_per_hit` already is.

## 3. `world/rules/affinity.py`: the new source

- [x] 3.1 Add `SEXUAL_FORCED = "sexual_forced"` to `AffinitySource`.
- [x] 3.2 Confirm no other logic in `apply_affinity_change` needs to change — `SEXUAL_FORCED` is a
  negative-delta-only source in practice (this proposal never applies it as a positive delta), so it
  falls through the existing `delta < 0` branch (floor at 0, no budget interaction, auto-leave
  recheck) with no new code path required.

## 4. `world/rules/combat_session.py`: the coercion scan

- [x] 4.1 Implement `_scan_sexual_coercion(actor, battlefield, logs) -> tuple[str, ...]`, structured
  as a close mirror of `_scan_friendly_fire`:
  - Collect every `EventEntry` across `logs` where `entry.kind == "sexual_resist"`.
  - For each: resolve `target = battlefield.roster.get(entry.target)`; skip (no penalty, no write)
    if `target is None` or not `isinstance(target, NPC)`.
  - Skip (no penalty) unless `entry.data.get("resisted") is False and entry.data.get("auto_comply")
    is False` — use `is False`, not falsy-truthiness, so a missing key (`None`) is correctly treated
    as "do not penalize" rather than accidentally matching (design.md Risk 2).
  - For each qualifying entry, call `apply_affinity_change(target, actor,
    AffinitySource.SEXUAL_FORCED, -get_config().sexual_forced_penalty)` inside the same
    `transaction.atomic()` + snapshot/restore-on-exception pattern `_scan_friendly_fire` uses,
    collecting `outcome.auto_leave_notification` the same way.
  - Return the collected notification tuple.
- [x] 4.2 Widen `_snapshot_party_surfaces` (or a merged sibling snapshot) per design.md Decision 3's
  exact code shape. Two independent changes are both required — a rubber-duck review caught that
  widening only the inner condition leaves the bug in place:
  - Remove the outer `if companion_pks:` early-return's gating effect on `relations_before`: the
    roster loop must always run, not only when the actor has declared companions.
  - Decouple the two dicts' population conditions: `relations_before[pk]` is populated for **every**
    `isinstance(entity, NPC)` roster member unconditionally; `members_before[pk]` stays gated on
    `pk in companion_pks` (party membership is only meaningful for companions).
  - Confirm this does not change `_scan_friendly_fire`'s own snapshot semantics observably — a
    superset snapshot restores everything the original scope restored, plus more.
- [x] 4.3 Update `_restore_round_touched`'s guard (`if party_before or members_before:`) so it also
  restores relations for a round with no companions but a non-companion NPC coercion target — for
  example, change the guard to `if party_before or members_before or relations_before:`.

## 5. Wiring

- [x] 5.1 In `submit_player_action`, immediately after the existing
  `notifications = _scan_friendly_fire(actor, battlefield, logs)` line, add
  `notifications += _scan_sexual_coercion(actor, battlefield, logs)` (or equivalent tuple
  concatenation preserving both scans' notifications) — inside the same shared outer transaction,
  per the code comment already documenting that block's scope.
- [x] 5.2 Confirm the combined `notifications` tuple still reaches the caller exactly where the
  existing single-scan `notifications` variable already does — no new return-shape change.

## 6. Tests

- [x] 6.1 `world/rules/tests/test_combat_session_sexual_coercion.py` (or an appropriately named
  addition to the existing combat-session test module — check whether `test_combat_session.py` or a
  friendly-fire-specific test file is the better home by inspecting how `_scan_friendly_fire`'s own
  tests are organized, and follow that placement).
- [x] 6.2 One test per spec scenario across both delta specs
  (`specs/sexual-resist-turn-cost/spec.md` and `specs/affinity-system/spec.md`'s MODIFIED
  requirement) — enumerate them explicitly. Apply `covers_requirement` per `AGENTS.md`'s OpenSpec
  test traceability section once requirement IDs are resolvable after archive (same caveat as
  `sexual-resist-contest`'s task 5.2 — do not guess an ID before then).
- [x] 6.3 Construct synthetic `EventLog`/`EventEntry` fixtures carrying `kind="sexual_resist"` with
  each of the three `data` shapes (forced, auto-comply, resisted) — this proposal's tests are the
  only exerciser of `_scan_sexual_coercion` until `sexual-act-effects` lands (design.md Risk 1); make
  these fixtures thorough enough to stand alone as the mechanism's full behavioral proof.
- [x] 6.4 A rollback test: force an exception after `_scan_sexual_coercion` applies a penalty but
  before the outer transaction commits, and assert the target NPC's `relations_data` is unchanged
  both via a fresh database read and via the in-process idmapper-cached object (mirroring however
  `_scan_friendly_fire`'s own existing rollback test verifies both surfaces — read that test first
  and match its verification technique).
- [x] 6.5 Two non-companion-NPC tests, both required to actually exercise the bug the rubber-duck
  review found (a test with any companion present on the battlefield would sidestep it, since that
  makes `companion_pks` non-empty and masks the outer-guard defect):
  - A battlefield with **one or more other companions present**, plus a non-companion `NPC` roster
    member who is the coercion target — commits correctly on success and restores correctly on
    rollback.
  - A battlefield with **zero declared party companions at all** (`companion_pks` empty) and one
    non-companion `NPC` roster member as the coercion target — commits correctly on success and, on
    rollback, the target's `relations_data` is restored both via a fresh database read and via the
    in-process idmapper-cached object. This second case is the actual regression test for design.md
    Decision 3's outer-guard fix; the first case alone does not prove it.
- [x] 6.6 A combined-scan test: one round producing both a qualifying friendly-fire hit and a forced
  coercion entry, asserting both penalties apply within the same commit.
- [x] 6.7 A non-NPC-target test: a `kind="sexual_resist"` entry whose target resolves to a `Monster`
  or `PlayerCharacter` applies no penalty and does not raise.

## 7. Validation

- [x] 7.1 Run `uv run --locked python -m compileall -q world` to catch syntax errors early.
- [x] 7.2 Run the new/extended test module(s) directly via `evennia test` (this touches
  `combat_session.py`, which requires `EvenniaTest` fixtures — confirm the exact invocation by
  checking how existing `combat_session` tests are run in `AGENTS.md`'s test-runtime section).
- [x] 7.3 Run the full existing `world.rules.tests.test_combat_session` (or equivalent) module to
  confirm the friendly-fire mechanic and general round-settlement behavior are unaffected by the
  snapshot-scope widening (design.md Decision 3's "companion snapshot coverage is unchanged"
  scenario).
- [x] 7.4 Run `uv run --locked python -m tools.spec_traceability check` and address any reported gap.
- [x] 7.5 Run `openspec validate sexual-resist-turn-cost --strict` and resolve every finding.
- [x] 7.6 Keep the hub documents in sync with what this proposal actually ships, per this document
  set's own established practice of correcting shared docs when implementation reveals a gap in the
  original sequencing. Already applied during this proposal's own design (verify unchanged at
  implementation time):
  - `docs/superpowers/specs/2026-08-15-sexual-act-system-overview-design.md` §4.2's file-ownership
    table for `B6b` includes `world/rules/affinity_config.py` and `world/rules/rulebook/affinity.yaml`
    (design.md Decision 4); the deferred `sexual-resist-out-of-combat` follow-up proposal is added to
    §4.2's table (design.md Decision 5); `B5`'s own row cross-references the resist-outcome contract.
  - `docs/superpowers/specs/2026-08-15-sexual-act-resolution-design.md` gained §3.4 ("Resist outcome
    contract (for `B6b`)"), the authoritative statement of the `EventEntry(kind="sexual_resist", ...)`
    contract `B5`'s implementer must honor — added because a rubber-duck review found the contract
    undiscoverable from `B5`'s own source-design section when only recorded in this proposal's
    design.md (design.md Decision 1's amendment note).
- [x] 7.7 Run `uv run --locked -m unittest discover -s tests -t .` to confirm no repository-wide
  contract regressed.
