## Why

`settlement-place-registry` makes a place the single authored record of a
service location, but nothing at runtime reads it yet. Three gaps remain,
and each one blocks a settlement that is not the capital.

**Interiors are code.** `sync_service_interiors()`
(`world/maps/bootstrap.py:85`) is not a loop over data — it is two constant
blocks (`GUILD_HALL_KEY`, `GENERAL_STORE_KEY`, their exteriors, tags and
descriptions) and two bespoke call sites. Adding a location means editing
Python, and the function has no notion of which settlement a room belongs
to, so it cannot resolve an exterior in a second coordinate space at all.

**Hosts are hard-coded human.** `world/rules/guild_economy.py:103` sets
`host.race = "human"` whenever race is unset. An elven village's hosts would
be built as humans. `LivingEntity.sex` (`typeclasses/entities.py:28`)
defaults to `"other"` and is never written for a service host at all, so
every shopkeeper in the game is currently unsexed. The place record already
authors race, subrace and sex; nothing applies them.

**A shop has no name.** `commands/economy.py:127` prints a hard-coded
`商店（營業中）：`, so a player standing in a forge and a player standing in a
bakery read the same line. With one shop that was invisible; the capital is
about to have four.

## What Changes

- Interiors are created by iterating the place registry, grouped by
  settlement so each exterior resolves in its own settlement's coordinate
  space. The two hard-coded constant blocks and their bespoke call sites are
  removed. The existing behaviour on an unresolvable exterior — warn naming
  the row, skip it, continue with the rest — is kept.
- Synchronization applies each place's authored host race, subrace and sex
  instead of assuming human. These are creation-time identity: written once
  beside the authored title and never rewritten on a later sync, matching
  the existing never-rename and never-retitle contract. Changing an authored
  value therefore takes effect through roster convergence.
- `ShopConfig` gains a `display_name_zh`, populated during shop resolution
  from the owning place's room name, and the stock listing prints it:
  `聖潔王都鍛造鋪（營業中）：` rather than `商店（營業中）：`. The command already
  holds the `ShopConfig`, so it needs no registry lookup of its own.

## Capabilities

### New Capabilities

- `place-driven-service-sync`: registry-driven interior creation, authored
  host race/subrace/sex, and the end-to-end guarantee that one place record
  yields a complete working location.

### Modified Capabilities

- `shop-economy`: the "Player-facing shop commands use only a local
  unambiguous merchant" requirement gains the shop's authored name in the
  stock listing.

## Impact

- `world/maps/bootstrap.py` — the two interior constant blocks and their
  call sites are replaced by a loop over `PLACE_REGISTRY` grouped by
  settlement.
- `world/rules/guild_economy.py` — `_sync_service_host` writes authored
  race, subrace and sex at creation instead of hard-coding human.
- `world/rules/guild_config.py` — `ShopConfig` gains `display_name_zh`,
  populated during shop resolution.
- `commands/economy.py` — stock listing header.
- **Depends on `settlement-place-registry`** for the records it reads.
- **Conflicts with `ciaran-village-map`** on `world/maps/bootstrap.py`. Land
  the map change first: it edits the map assembly at the top of the file
  while this change rewrites `sync_service_interiors`, so in that order the
  two touch different regions.
