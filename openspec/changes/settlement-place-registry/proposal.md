## Why

A location that offers a service is described in four places that nothing
keeps in agreement:

| Source | What it holds |
| --- | --- |
| `world/lore/shops.py` | the shop's identity and host name/title |
| `world/rules/rulebook/guild_economy.yaml` `service_hosts:` | the same host's name, title, profession, room tag |
| `world/rules/rulebook/commerce.yaml` | the shop's hours |
| `world/maps/bootstrap.py` | the interior room, hard-coded as module constants |

`sync_service_interiors()` is not a loop over data — it is two constant
blocks (`GUILD_HALL_KEY`, `GENERAL_STORE_KEY`, their exteriors, tags,
descriptions) and two bespoke call sites. Adding a third location means
editing Python. `docs/lore/settlement-locations.md` describes eighteen
location types across six settlement archetypes.

Two further gaps block any settlement that is not the capital:

- **Hosts are hard-coded human.** `world/rules/guild_economy.py:103` sets
  `host.race = "human"` when race is unset. An elven village's hosts would
  be built as humans. `LivingEntity.sex` (`typeclasses/entities.py:28`)
  defaults to `"other"` and is never written for a service host at all.
- **A shop has no name.** `commands/economy.py:127` prints a hard-coded
  `商店（營業中）：`, so a player standing in a forge and a player standing in
  a bakery read the same line.

## What Changes

- Introduce **places**: one authored row per location, carrying its interior
  room, its exterior grid coordinate, its host's full identity, its
  profession and the component identity kwargs that profession needs, and
  the assortments it sells. One row is the whole location.
- Introduce **settlements**: a key, an archetype drawn from the six the lore
  document defines (capital, town, port, beast city, elven village,
  frontier), and the map coordinate space the settlement's places sit in.
- **BREAKING**: the `service_hosts:` roster in `guild_economy.yaml` is
  removed. The roster is derived from the place registry, so a host is
  declared exactly once.
- **BREAKING**: `world/lore/shops.py` is deleted. `SHOP_REGISTRY` is derived
  from the places that declare a `shop_key`; its authored-identity and
  cross-registry uniqueness validators move into the new package and run
  over the derived rows unchanged.
- Interiors are created by iterating the place registry rather than from
  module constants. The existing "exterior missing → warn and skip"
  behaviour is kept.
- A place authors its host's race, subrace and sex. These are creation-time
  identity, written once beside the authored title and never rewritten on a
  later sync, matching the existing never-rename/never-retitle contract.
  `SUBRACE_REGISTRY` already ships `ciaran` bound to `village_ciaran`, so a
  village host can carry a real subrace rather than a bare race.
- Stock listing names the place: `聖潔王都鍛造鋪（營業中）：` rather than
  `商店（營業中）：`.

## Capabilities

### New Capabilities

- `settlement-place-registry`: the place and settlement records, the
  derivation of shop identities and the service-host roster from places,
  registry-driven interior creation, and authored host race/subrace/sex.

### Modified Capabilities

- `guild-registration`: the "Service hosts are created and converged from a
  declarative YAML roster" requirement changes its source — the roster is
  derived from the place registry rather than hand-written in
  `guild_economy.yaml`. Every validation, reuse, convergence and idempotence
  guarantee it makes is retained.
- `shop-economy`: the "Player-facing shop commands use only a local
  unambiguous merchant" requirement gains the shop's authored name in the
  stock listing.

## Impact

- `world/lore/settlements/` — gains `settlements.py` (`SettlementArchetype`,
  `SettlementDefinition`, `SETTLEMENT_REGISTRY`), `places.py` (`PlaceKind`,
  `PlaceDefinition`, `PLACE_REGISTRY`), and `shops.py` (derived
  `SHOP_REGISTRY` plus the two relocated validators).
- `world/lore/shops.py` — deleted. Its only non-test consumer is
  `world/rules/guild_config.py`.
- `world/rules/guild_config.py` — `validate_service_hosts` reads derived
  rows; shop resolution reads derived shop identities.
- `world/rules/guild_economy.py` — `_sync_service_host` writes authored
  race, subrace and sex at creation instead of hard-coding human.
- `world/maps/bootstrap.py` — the two interior constant blocks and their
  bespoke call sites are replaced by a loop over the place registry.
- `world/rules/rulebook/guild_economy.yaml` — `service_hosts:` removed.
- `commands/economy.py` — stock listing header, fed by a new
  `display_name_zh` on `ShopConfig` so the command needs no place lookup.
- `world/lore/sync.py` — the new registries join `_ALL_REGISTRIES`.
- **Depends on `commerce-assortment-registry`**: places reference
  assortments, and this change moves the shop identity that change reshaped.
- **Conflicts with `ciaran-village-map`** on `world/maps/bootstrap.py`. Land
  the map change first; this change then rewrites the interior path once.
