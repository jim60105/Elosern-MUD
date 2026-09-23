> Sequencing (design D8): tasks 2.3 and every panel/kind test re-pin run only after
> `add-holy-rite-category` is applied AND archived with its specs synced into `openspec/specs/`.

## 1. Grammar + surfaces

- [x] 1.1 Add `RiteBlessingEffect(buff_key)` (single-argument parse helper) and the bare
      `RiteShelterEffect` marker to the parser package `world/skills/effects/` (`parser.py`'s
      dispatch chain, dataclasses where its siblings live), admit both prefixes in
      `parse_effect`'s closed set, and cover the grammar scenarios (payload on the bare prefix and
      bare/empty/multi-segment on the buff prefix fail closed).
- [x] 1.2 Add `"church"` to `SNAPSHOTTED_SURFACES` in `world/rules/action/contracts.py`, declare the
      four `RITE_*` `RejectReason` values, and add their fixed zh-TW lines to
      `world/rules/player_messages.py`.
- [x] 1.2b Add the `"church"` branch to `_snapshot_touched`/`_restore_touched` in
      `world/rules/action/transaction.py` in the wallet/inventory shape
      (`_attribute_snapshot(obj, "church")` / `_restore_attribute`) — membership in the surface set
      alone does NOT snapshot or restore anything (duck B1). Do NOT touch `transaction.py`'s
      `_ENTITY_SURFACES` frozenset (a different, same-named seam: the entity-aggregate gate).
- [x] 1.3 Add `("church", None)` to `_ENTITY_SURFACES` in `world/rules/cast_settlement.py`; verify
      the offering rail's explicit `church` snapshot stays idempotent under key-merge.

## 2. Handlers + registry

- [x] 2.1 Implement `_handle_rite_blessing` and `_handle_rite_shelter` in
      `world/rules/action/effects/church.py` (gates raise `RejectedAction` before staging;
      blessing stages ledger stamp + buff mount, shelter stages traits gain + day marker).
- [x] 2.2 Add the shared day-block normalise helper in `world/rules/church.py` and route
      `pray_step` through it (no third copy of the normalise logic).
- [x] 2.3 Declare `effects=("rite_blessing:martial_blessing",)` / `effects=("rite_shelter",)` on the
      two rows and swap `rite_morning_devotion` to `SkillKind.PASSIVE` in
      `world/skills/registry/data_church.py`; confirm the `REDEEM_CATALOG` row's kind drives
      `grant_owned_skill` into `db.skills.passive`.

## 3. Clean cutover

- [x] 3.1 Delete `cast_martial_blessing`, `apply_shelter_rest`, `MartialBlessingReason`/`Error`,
      `ShelterReason`/`Error` from `world/rules/church.py`; remove the
      `martial_blessing_last_tick` attribute and root `shelter_rest_flag` key everywhere (LSP
      references first, no shims).
- [x] 3.2 Emit the `rite_cast` info event at each successful settlement boundary through the
      observability facade with `char`/`rite`/`tick` context — commit-bound via
      `transaction.on_commit` inside the `church.py` mutator (the `church_pray` precedent), never
      inside a handler's staged `apply` and never before the settlement returns success.

## 4. Tests follow

- [x] 4.1 Re-anchor `test_church_rulebook.py`'s Series E block to the resolver face: success casts
      mount the stamp/buff and the rest bonus; cooldown recast is `RITE_COOLDOWN_ACTIVE`; shelter
      outside a venue is `RITE_OUTSIDE_VENUE`; same-day recast is `RITE_ALREADY_SHELTERED`; a day
      boundary re-arms shelter; `rite_morning_devotion` lands passive and refuses its cast while the
      cap bonus stays live.
- [x] 4.2 Add one rollback proof per handler driving a genuine INNER commit failure (a second
      staged pending effect whose `apply()` raises after the church-surface write, not just an
      outer settlement failure): assert `COMMIT_FAILED` and that ledger, buffs, traits, and tick
      are byte-identical with no `rite_cast` event — this is the test that proves 1.2b's
      dispatcher branch, not just the outer snapshot.
- [x] 4.3 Move the `covers_requirement` anchors for the amended `church-ordination` requirements to
      the new resolver-face tests (literal IDs); run
      `uv run --locked python -m tools.spec_traceability check` plus the observability lint
      (`tools.observability_lint check`) in the same batch as the touched files' focused labels.

## 5. Docs sweep

- [x] 5.1 No command-surface change: confirm `docs/game/commands.md`, `docs/game/command-reference.md`,
      and `tests/test_command_docs.py` stay untouched; update `docs/lore/skill-trees/light.md` (or
      the church doc) where it names the Series E rows' cast behaviour.
- [x] 5.2 `git diff --check` clean.
