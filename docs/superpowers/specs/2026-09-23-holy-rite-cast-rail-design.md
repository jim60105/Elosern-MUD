# Holy-Rite Cast Rail — Design

Date: 2026-09-23
Status: approved by the requester in the brainstorming session
Related: `docs/superpowers/specs/2026-09-22-church-system-design.md` (§5.7 Series E),
archived change `2026-09-23-implement-church-order-catalogue` (proposal note:
"No player-command surface change … left for a future church rituals/commands
change" — the N3 deferral this design closes).

## 1. Problem

The church redemption catalogue grants ACTIVE skills whose cast surface never
landed:

- `rite_martial_blessing` and `rite_shelter` have engine APIs
  (`world/rules/church.py::cast_martial_blessing` / `apply_shelter_rest`) that
  only tests call. No command reaches them (the N3 deferral).
- Both engine APIs are **undisciplined writers**: no transaction, no
  snapshot/restore, no clock participation — below the standard `pray_step`
  already keeps for its own settlement.
- `shelter_rest_flag` has no reset path anywhere in the repo: one use and the
  sister is permanently `ALREADY_SHELTERED`.
- The church block is the only skill source outside the unified cast rail:
  15 registry ACTIVE rows (Series B 8, D 4, E 3) sit in `enhancement` /
  `sexual_act`; only `rite_lamb_mark` (`self_buff_apply:lamb_seal`) and
  `rite_martyrdom_vow` (`session_stamp:martyr_key`) are actually on the rail.
  The other 10 declare no effects (authored future content).
- `rite_morning_devotion` is declared ACTIVE but its mechanic is purely
  ownership-triggered (pray daily cap +1, consumed via `daily_cap_bonus`);
  casting it would burn time for nothing.

## 2. Decision summary (requester-approved)

1. **Cast rail (option B), reusing the existing settlement safety system.**
   The Series E rites become normal `cast` actions through the resolver's
   step-5 effect-handler registry, the commit-point snapshot/restore, and the
   outer `settle_out_of_combat_cast` transaction. No new transaction machinery.
2. **A fourth skill family: `SkillCategory.HOLY_RITE = "holy_rite"` (神聖聖儀).**
   All 15 church-block ACTIVE rows re-classify to it. This is the data
   contract for the future fourth menu in the web UI (out of scope here — the
   browser frontend is a non-goal for this change; only the JS protocol mirror
   constant grows).
3. **`rite_morning_devotion` re-judges to PASSIVE** (decision (a)): honest to
   its mechanic, zero prayer-side change. This amends the main spec's "(ACTIVE:
   …)" wording through this change's delta spec.
4. **Shelter's daily reset rides the existing prayer day-block.** The flag
   moves from the ledger root into `db.church["daily"]`, so the prayer
   day-rollover `daily.clear()` clears it with no new reset code.

Passives (Series C, 5 rows) stay in `enhancement`. No player-command surface
changes: `cast` is already documented, so the docs trio (`docs/game/commands.md`,
`docs/game/command-reference.md`, `tests/test_command_docs.py`) is untouched —
consistent with the original proposal's "no player-command surface change".

## 3. Registry: the `holy_rite` category

`world/skills/registry/vocab.py::SkillCategory` gains the member
`HOLY_RITE = "holy_rite"` **at the end of the enum** (declaration order is the
frozen display order; appending is the only legal edit). zh-TW label:
神聖聖儀.

`world/skills/registry/data_church.py`: the 15 ACTIVE rows
(`rite_heal_light`, `rite_cleanse`, `rite_calm`, `rite_bless_water`,
`rite_sanctify_ground`, `rite_absolution`, `rite_lamb_mark`,
`rite_martyrdom_vow`, `rite_anointing_touch`, `rite_milk_blessing`,
`rite_holy_kiss`, `rite_confession_bed`, `rite_martial_blessing`,
`rite_shelter`, `rite_morning_devotion`) change `category=ENHANCEMENT →
CHURCH_RITE`; the four Series D rows change `SEXUAL_ACT → CHURCH_RITE`.
The 5 Series C PASSIVE rows and every pre-existing non-church row keep their
category.

Consequences:

- `rite_morning_devotion` additionally changes `SkillKind.ACTIVE → PASSIVE`
  (the redemption `grant_owned_skill` writes by kind: PASSIVE lands in
  `db.skills.passive`; `_owns_skill` reads both lists, so the cap bonus is
  unaffected).
- The four Series D placeholder rows are not in `SEXUAL_ACT_REGISTRY` and
  currently sit in the named-exclusion list of the registry-agreement
  structural check (`world/skills/tests/test_registry_structure/_support.py`).
  After the re-classification they leave the `SEXUAL_ACT` comparison set
  entirely, so the exclusion list shrinks by those four keys.
- Presentation surfaces that group by category (combat-actions listing, the
  webclient panels) pick the group up automatically once the JS protocol
  mirror constant `SKILL_CATEGORY_KEYS`
  (`web/static/webclient/js/elosern/protocol/constants.js`) gains
  `"holy_rite"`; the panel validators reject unknown categories, so the mirror
  update ships in the same change. This is a data mirror, not frontend work.

## 4. Cast rail for the two Series E mechanics

### 4.1 Church ledger becomes a snapshotted surface

`"church"` joins `SNAPSHOTTED_SURFACES`
(`world/rules/action/contracts.py`) — precedent: `"battlefield"` joined the
same list by combat-disengage D-5; adding a surface extends the snapshot
inventory, it does not alter the commit mechanism.

`world/rules/cast_settlement.py::_ENTITY_SURFACES` gains `("church", None)` so
the outer settlement transaction snapshots the ledger too (the inner resolver
commit alone would not cover the clock-advance failure path). The offering
rail's own `_snapshot_offering_state` already snapshots `church` explicitly on
top of `_ENTITY_SURFACES`; dict-merge by key makes the addition idempotent
there, not double-restoring.

### 4.2 `rite_martial_blessing` — effect prefix `rite_blessing`

Registry row gains `effects=("rite_blessing:martial_blessing",)` — payload is
the `buffs.yaml` buff key, matching the `self_buff_apply:<key>` grammar.

New handler in `world/rules/action/effects/church.py` (same home as
`_handle_session_stamp`), registered with surfaces
`frozenset({"church", "buffs"})`:

- Gates (all before staging): ledger exists (`REJECTED: RITE_NOT_ENROLLED`);
  the cooldown stamp read from `db.church["blessing_last_tick"]` against
  `get_world_clock().tick` and the `church.yaml` accrual row's
  `cooldown_seconds` (`REJECTED: RITE_COOLDOWN_ACTIVE`). Skill ownership is
  already resolver step 1 (`_owns_skill` sees the redeemed grant in
  `db.skills.active`); no duplicate ownership gate.
- Stages two `PendingEffect`s: (1) ledger write of `blessing_last_tick =
  clock.tick` on the `church` surface, (2) the buff mount on the `buffs`
  surface reusing the `self_buff_apply` staging helper path with the named
  buff key.
- Values (`stat`, `magnitude`, `cooldown_seconds`) keep reading the
  `church.yaml` accrual row — zero Python constants, unchanged rulebook
  discipline. The `martial_blessing` buff definition and
  `combat_modifiers.yaml` defense row stay exactly as shipped.
- Cooldown stamp location moves from the standalone attribute
  `db.martial_blessing_last_tick` into the ledger key `blessing_last_tick`
  (unreleased project: no compat read, old attribute deleted).

### 4.3 `rite_shelter` — effect prefix `rite_shelter` (bare)

Registry row gains `effects=("rite_shelter",)` (bare prefix like
`set_disguise`; payload fails at parse).

New handler registered with surfaces `frozenset({"church", "traits"})`:

- Gates: ledger exists (`RITE_NOT_ENROLLED`); `_in_church_venue(entity)`
  (`RITE_OUTSIDE_VENUE`); day-block freshness — `daily.day == today and
  daily.get("shelter")` → `RITE_ALREADY_SHELTERED`.
- Stages two `PendingEffect`s: (1) hp/sp gain capped at base by the
  `church.yaml` `rest_bonus` row, on the `traits` surface (same clamp the
  engine API performs today); (2) the day-block write on the `church`
  surface: normalize the block exactly like `pray_step`'s `_mutate` (if
  `daily.day != today`: `daily.clear()` then `{"day": today, "pray": 0}`),
  then `daily["shelter"] = 1`.
- The day-rollover clear is inherited: every writer (pray or shelter)
  normalizes on write, and readers compare `daily.day`, so a new day is
  automatically unsheltered with no reset code. The root
  `shelter_rest_flag` key disappears (no compat read).

### 4.4 RejectReason additions

Four stable reasons on `world/rules/action/contracts.py::RejectReason`:
`RITE_NOT_ENROLLED`, `RITE_COOLDOWN_ACTIVE`, `RITE_OUTSIDE_VENUE`,
`RITE_ALREADY_SHELTERED`, each mapping through the existing
`world/rules/player_messages.py` rejection-message surface to fixed zh-TW
lines (same pattern as every existing `RejectReason`).

### 4.5 Deleted with the cutover

`cast_martial_blessing`, `apply_shelter_rest`, `MartialBlessingReason`,
`MartialBlessingError`, `ShelterReason`, `ShelterError`, the
`martial_blessing_last_tick` attribute, and the root `shelter_rest_flag`
ledger key. No shims, no re-exports. `daily_cap_bonus` and the passive-effect
readers are untouched.

## 5. Flow and error handling

```
cast rite_martial_blessing
  → settle_out_of_combat_cast            # outer transaction
      snapshot: _ENTITY_SURFACES (+ church) per actor/target, clock tick,
                advance registry, practice dedupe
      ActionResolver.resolve
        step1 owns ✓ (grant in db.skills.active)
        step4 gates, step5 rite_blessing handler → 2 PendingEffects
        step8 time cost (existing COMMAND billing)
      commit: inner snapshot/restore per touched surface (incl. church)
      _scan_out_of_combat_sexual_coercion  (no-op for these rows)
      clock.advance(time_cost, COMMAND)
  any failure → inner rollback and/or outer restore; ledger, buffs, traits,
  wallet-adjacent state byte-identical; nothing notified.
```

`rite_shelter` outside a venue never reaches the clock: step 5 raises
`RejectedAction`, `resolve()` returns the stable rejection, the settlement
advances nothing (existing promise, newly exercised for a church ledger
write). Rollback proof tests cover both handlers (injected commit failure →
ledger/buffs/traits byte-identical).

## 6. Testing, traceability, docs

- `world/rules/tests/test_church_rulebook.py`: the Series E block re-targets
  the resolver face — success cast mounts buff + stamp; cooldown recast is
  `RITE_COOLDOWN_ACTIVE`; shelter outside venue is `RITE_OUTSIDE_VENUE`;
  shelter twice same-day is `RITE_ALREADY_SHELTERED`; **after a day rollover
  (clock advanced past day boundary, or `daily.day` backdated) shelter succeeds
  again**; rollback proof per handler.
- `world/skills/tests/test_skill_registry/test_category_classification.py` and
  the registry-agreement `_support.py` exclusion list follow the 15-row move
  and the ACTIVE→PASSIVE re-judgement.
- Panel/codex tests naming the old categories (combat panel, `skills.js` /
  protocol constants tests) gain `holy_rite`; the Node protocol test fixtures
  validate the extended `SKILL_CATEGORY_KEYS`.
- Spec traceability: the `church-ordination::Series E utility rows feed the
  core loop` requirement anchor moves from the deleted engine-API test to the
  new cast-behaviour test via `covers_requirement` (literal IDs, per
  `docs/development/spec-test-traceability.md`).
- Observability: every new write path is inside existing boundary events
  (`action_commit` covers the resolver commit); the handler emits
  `log_info("rite_cast", context={char, rite, tick})` on success per the
  catalog discipline. Freeze list untouched (facade already adopted in
  `church.py`).
- Docs trio: unchanged (no command keys/aliases/syntax change).
  `docs/game/commands.md` needs no edit because `cast` already covers the
  surface.

## 7. OpenSpec plan

Implementation ships as one change, proposed name
`implement-holy-rite-cast-rail`, via the normal propose → apply → verify →
archive flow:

- Delta spec `church-ordination`: amends the Series E requirement wording
  (morning devotion PASSIVE, the rite cast rail as the acquisition-use pair),
  adds requirements for the cooldown/day-block rails and the stable rejections.
- Delta spec (skills registry capability): the `holy_rite` category fact.
- Tasks: surfaces + RejectReason + handlers → registry re-classification →
  engine-API deletion + test re-anchors → JS mirror + panel tests → docs/
  traceability sweep.

## 8. Explicit non-goals

- No browser/UI implementation (the fourth menu consumes the `holy_rite`
  category in a later change; only the JS protocol constant mirror moves now).
- No rails for the 10 effect-less future-content rows (Series B heal/cleanse/
  calm/bless-water/sanctify/absolution, Series D acts): they keep their
  documented future-content status, now honestly filed under `holy_rite`.
- No player commands (`church bless`/`church shelter` explicitly rejected in
  favour of the rail), no new rulebook sections, no compat layers.
