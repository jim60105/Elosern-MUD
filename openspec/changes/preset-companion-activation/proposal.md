## Why

`preset-companion-model` gave the registry a way to declare a starting
companion and a builder that produces the NPC. Nothing calls it yet, and a
built NPC is still a stranger: it has no relationship record and no party
binding. This change wires the builder into activation so choosing 悠奈 actually
starts the game with 悠花 in the party.

`join_party` has never been called by anything but a player-initiated invite,
and this change makes activation its second caller. The affinity primitive the
binding needs — a seed that establishes a relationship no interaction produced —
lands separately in `affinity-seed-writer`.

## What Changes

- The companion's relationship is established through `seed_affinity`, the
  narrowly-scoped second writer `affinity-seed-writer` adds to
  `world/rules/affinity.py`. That writer is a prerequisite change, not part of
  this one, so affinity's contract change was reviewed in isolation.
- `activate_player_character` builds, seeds, and binds each declared companion
  **inside** its existing `transaction.atomic()` block, after the character's
  own identity, traits, inventory, and equipment are written — `join_party`
  requires co-location and the builder places the NPC at the player's location.
- Any failure deletes every companion built so far and re-raises, so the whole
  activation rolls back and no half-formed 悠花 survives. A 悠奈 without 悠花
  would silently contradict the card the player chose, so the companion is not
  best-effort.
- The party binding goes through `join_party`, which stays the sole writer of
  membership; activation adds no second binding path.
- The seeded value (95) is above `invite_threshold`, so the auto-leave recheck
  can never dismiss the companion on arrival.
- The player starts with one of the four companion slots occupied; the bound is
  unchanged and enforced by the same gate.

No backward compatibility or data migration: the project has no released users.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `starting-companions`: new requirements for the activation binding — build
  order, atomicity, failure semantics, and the resulting party and relationship
  state.
- `party-system`: the membership requirement names preset activation as a second
  caller of `join_party`, alongside the player-initiated invite.

Prerequisite changes: `preset-companion-model` (the builder) and
`affinity-seed-writer` (the seed writer). There is no logical dependency on
`preset-persona-activation` — the companion's persona comes from
`PresetPersona.to_record()` (`preset-persona-model`), not from the player-side
record builder — but the two changes both edit `activate_player_character`, so
they cannot land in parallel.

## Impact

- `world/rules/affinity.py` — untouched; `seed_affinity()` is consumed, not
  modified.
- `world/rules/character_creation.py` — a companion step inside the activation
  transaction plus its failure cleanup.
- `world/rules/starting_companions.py` — the orchestration entry point that
  builds, seeds, and binds; the builder from the previous change is unchanged.
- `world/rules/party.py` — read-only; `join_party` is reused, not modified.
- `world/rules/tests/test_starting_companions.py`,
  `world/rules/tests/test_party.py`,
  `world/rules/tests/test_character_creation.py`.
- Player-visible: choosing either twin now starts the game with the other in the
  party at 至愛. Dismissing her leaves her in the room, re-invitable through the
  ordinary `invite` command because she is an `LLMNPC` above the threshold.
