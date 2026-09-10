## Why

Today it is impossible to cast a damaging skill outside combat, but only by
accident: not one skill carrying a `DamageEffect` declares
`usable_out_of_combat=True`, so `world/rules/action.py`'s existing gate refuses
every such request before the question of what damage outside a battlefield
would even mean can arise.

That accident is about to end. `skill-field-availability` audits and widens the
`usable_out_of_combat` flag, and `field-combat-initiation` adds an exploration
entry that opens combat with the chosen skill. The moment a damage skill is
flagged usable outside combat, `settle_out_of_combat_cast` would happily
resolve it against a `RoomActionContext` — a context that reports every
co-located non-self entity as an **ally**
(`world/rules/targeting.py`) — letting a player kill an NPC in the open world
with no combat, no session, no defeat handling, and no aftermath. Nothing in
the codebase would stop it.

This change installs the invariant that makes the later widening safe, and
installs it while it is still provably inert: **a damaging action never
resolves without a battlefield.** Landing it first means no intermediate commit
in the sequence ever exposes the hole.

## What Changes

- New `RejectReason.DAMAGE_REQUIRES_MONSTER_TARGET` in `world/rules/action.py`,
  with its Traditional Chinese player-facing line in
  `world/rules/player_messages.py`.
- `ActionResolver`'s capability step gains a second, explicitly marked
  combat-state gate immediately after the existing `usable_out_of_combat` one:
  a skill whose parsed `effects` carry a `DamageEffect` and whose
  `request.context.battlefield is None` rejects with the new reason, before any
  resource spend, any roll, any effect staging, and any world-clock access.
- `world/rules/action_preview.py` mirrors the same condition, so the shared
  preview and the combat-session submission revalidation report the skill as
  disabled with the same stable reason rather than letting it reach resolve.
  This follows the existing pairing of `action.py:310` and
  `action_preview.py:141`.
- Gate order is fixed and specified: the `usable_out_of_combat` flag is
  checked first, so a damage skill that is not flagged still reports
  `SKILL_NOT_USABLE_OUT_OF_COMBAT`; the new gate speaks only for skills the
  registry does permit outside combat.
- **BREAKING** for one archived requirement's wording: `action-resolution-
  pipeline` currently asserts `action.py` and `targeting.py` contain exactly
  *one* explicitly marked combat-state conditional. It becomes exactly two,
  both enumerated by name.

The reason name states the player-facing rule ("a damaging skill must be aimed
at a monster"), because from exploration the only way to obtain a battlefield
is to open combat on a co-located monster — the routing
`field-combat-initiation` adds. The mechanism is the battlefield's absence; the
message is the reason it is absent.

No backward compatibility and no migration: the project has no released users,
and the gate is inert against every skill that exists today.

## Capabilities

### New Capabilities

None. This change adds and modifies requirements in one existing capability.

### Modified Capabilities

- `action-resolution-pipeline`: adds the damage-outside-battlefield gate as a
  named requirement covering both `ActionResolver` and the shared preview,
  including its ordering relative to the `usable_out_of_combat` gate; and
  modifies the existing "Neither ActionResolver nor targeting branches on
  combat state" requirement so the sanctioned count of explicitly marked
  combat-state conditionals is two rather than one.

## Impact

- `world/rules/action.py` — the new `RejectReason` member and the capability-step gate.
- `world/rules/action_preview.py` — the mirrored preview condition.
- `world/rules/player_messages.py` — the rejection line.
- `world/rules/tests/` — gate coverage, gate-order coverage, and preview/resolve
  agreement.
- `world/rules/tests/test_no_combat_branching.py` — the existing structural
  tripwire encodes the one-gate contract today and fails on this change until
  it is updated to the two named gates. Both this module and every other test
  module this change touches are already registered in
  `.github/evennia-shards.json`, so the manifest needs no edit.
- Unaffected today: every existing skill (no `usable_out_of_combat=True` skill
  carries a `DamageEffect`, verified across `world/skills/registry.py` and the
  sexual-act catalog), `settle_out_of_combat_cast`'s own logic, the combat
  session, the command surface, and the webclient.
- Explicitly out of scope: item use (`world/rules/items.py` /
  `resolve_item_use`) keeps its own `in_combat` contract; this gate is about
  skill effects.
