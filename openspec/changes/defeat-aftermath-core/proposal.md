# Proposal: DA1 — defeat-aftermath-core

Change ID: **DA1** (parent design §8 archive order).

## Why

Player defeat today is one line of prose (`"你被擊敗了。"`) and a player
statue at HP 0: heal cannot revive, but movement and `rest` are unguarded,
so the real loop is lose → walk out → rest to full → refight the same
coordinate, whose wilderness monster respawned at full HP. Zero cost. The
owner-approved design
(`docs/superpowers/specs/2026-09-06-defeat-aftermath-design.md`) defines a
consequential-but-continuable defeat; this change lands the deterministic
PG skeleton — independently playable (the player wakes at HP 1; recovery to
5% is the sibling `defeat-aftermath-recovery` change) and the seam every
adult layer attaches to.

## What Changes

- Hostile defeat settles differently (guild exams unaffected):
  - Player HP **floors at 1** and the player is marked knocked out
    (nonlethal-floor precedent extended to the player; no player is ever
    settled as a 0-HP corpse).
  - The **defeat-aftermath writer** (`world/rules/defeat_aftermath.py`,
    new, deterministic core) runs inside the existing `settle_session`
    `transaction.atomic()` — the `settled_tick` marker, session clearing,
    and aftermath commit or roll back together, so no half-applied
    aftermath is observable.
  - **Violators depart**: living winning-foe monsters leave the room —
    wilderness population monsters (`db.population_key`) despawn and drop
    from `itemcoordinates` (next activation respawns them as today);
    **quest-bound monsters (pk in the player's `db.quest_log`
    `objective_target_ids`) are never removed** — quest retention outranks
    the population marker — and narratively ignore the player (removing an
    extermination target would be disguised record loss). Foreign monsters
    stay untouched.
  - The player wakes **on the spot** at HP 1 (5% recovery is
    `defeat-aftermath-recovery`'s scope).
- New **weak debuff** (`rulebook/buffs.yaml` row `defeat_weak`): marker
  buff on the shipped effect surface (`bounds` ceilings on the physical
  axes, like `dark_curse`), duration measured in advanced world seconds.
  It does not scale regen — the buff engine's rate modifier is an absolute
  per-interval delta, and the regen tax belongs to the recovery change's
  settlement math.
- New **defeat rendering**: ordered EventLog entries (new open-vocabulary
  kinds `defeat_settle` / `violator_depart` / `weak_granted` —
  `EventEntry.kind` is an open string; each kind ships its zh-tw offline
  template line here) rendered through the existing `player_messages.py`
  idiom; a `defeat_aftermath` boundary info event per the observability
  catalog.
- **`DEFEAT_ADULT_SCENES` setting** (default true) declared here as a pure
  guard around a violation hook point whose body adult changes register;
  the core has no on-branch.
- **Per-section rulebook loader** for `rulebook/defeat_aftermath.yaml`:
  the loader validates its own sections and ignores unknown sections with
  one `log_warn`; downstream changes register their own section validators
  (forward-compatible single YAML file).
- **Zero-uncaused-write guarantee, pinned as tests**: affinity, wallet
  (integer copper), inventory, quest progress, guild rank/merit, and
  protected-entity bindings are byte-identical after a defeat settlement,
  excluding changes the world clock causally produced (deadline, daily
  decay/reset, restock, buff decay). The declared-write manifest lives in
  test code and downstream changes extend it.
- **BREAKING** (settlement semantics, no released users): the two
  "settlement never revives the defeated player at 0 HP" regression tests
  are rewritten — the player now settles at the HP-1 floor.

## Capabilities

### New Capabilities

- `defeat-aftermath-core`: the deterministic defeat settlement — HP floor,
  violator departure (population despawn vs quest-bound retain with
  precedence), weak debuff mount, defeat EventLog vocabulary + zh-tw
  lines, the content-switch guard, the per-section rulebook loader, and
  the zero-uncaused-write contract.

### Modified Capabilities

- `player-combat-session`: the terminal-outcome settlement requirement
  gains the defeat-aftermath phase; the "knocked-out player settles as
  defeat" scenario keeps its shape but the survivor state changes (HP 1 +
  aftermath, not 0 HP); the atomic-persistence-unit requirement now covers
  the aftermath phase.
  (`wilderness-monster-population` is NOT modified: departure is a
  defeat-writer action pinned in the new capability; every existing
  population requirement, respawn-on-activation and the
  session-participant-preservation invariant, stays verbatim true.)

## Impact

- `world/rules/defeat_aftermath.py` (new), `world/rules/combat_session.py`
  (`settle_session` defeat branch hook-in, same transaction),
  `server/conf/settings.py` (`DEFEAT_ADULT_SCENES`),
  `world/rules/skip_safety.py` (unchanged behavior — verified, not edited),
  `world/rules/rulebook/defeat_aftermath.yaml` (PG sections + loader),
  `world/rules/rulebook/buffs.yaml` (weak buff row),
  `world/rules/player_messages.py` (defeat template lines).
- Rewritten tests: `test_combat_session_recovery.py`'s two never-revive
  cases; new `world/rules/tests/test_defeat_aftermath_core.py`; shard
  manifest updated in the same change.
- Depends on nothing. **Blocks** `defeat-aftermath-recovery`,
  `defeat-aftermath-violation-sequence` (archives first in the family;
  archive order per parent design §8).
