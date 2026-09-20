## Why

A location that offers a service is described in four places that nothing
keeps in agreement:

| Source | What it holds |
| --- | --- |
| `world/lore/shops.py` | the shop's identity and host name/title |
| `world/rules/rulebook/guild_economy.yaml` `service_hosts:` | the same host's name, title, profession, room tag |
| `world/rules/rulebook/commerce.yaml` | the shop's hours |
| `world/maps/bootstrap.py` | the interior room, hard-coded as module constants |

Nothing detects a disagreement. A host renamed in one file and not the other
loads cleanly and produces a host whose roster row and shop identity name
different people. `docs/lore/settlement-locations.md` describes eighteen
location types across six settlement archetypes; this shape does not survive
the second settlement, let alone the sixth.

There is also no such thing as a settlement in the code. A map's `zcoord` is
a string that appears in several registries, and the six archetypes the lore
document organises itself around have no representation at all.

This change builds the records and makes the duplicated declarations derive
from them. It deliberately stops at the load boundary: startup
synchronization keeps reading exactly what it reads today, so the change is
provably behaviour-neutral. `place-driven-service-sync` moves the runtime
onto the registry afterwards.

## What Changes

- Introduce **places**: one authored row per location, carrying its interior
  room's identity and description, its exterior grid coordinate, its host's
  identity, its profession and the component identity kwargs that profession
  needs, and the assortments it sells. One row is the whole location.
- Introduce **settlements**: a key matching the geographic anchor, an
  archetype drawn from the six the lore document defines (capital, town,
  port, beast city, elven village, frontier), and the map coordinate space
  the settlement's places sit in.
- **BREAKING**: the `service_hosts:` roster in `guild_economy.yaml` is
  removed. The roster is derived from the place registry, so a host is
  declared exactly once. Every validation the hand-authored roster carried —
  missing field, unknown profession, blueprint coverage, dead kwarg,
  person-bound component on an anchored row — is retained and now runs over
  derived rows.
- **BREAKING**: `world/lore/shops.py` is deleted. `SHOP_REGISTRY` is derived
  from the places that declare a `shop_key`; its authored-identity and
  cross-registry uniqueness validators move into the new package and run
  over the derived rows unchanged.
- Places live in per-settlement modules concatenated into one registry, the
  way `world/lore/items/` already assembles its `data_*.py` slices. This is
  what lets later content changes author different settlements without
  editing the same file.

The capital's two existing locations are transcribed into place rows using
the same room tags, host names, titles, `service_id`s and component kwargs
they carry today, so the derived roster reproduces the shipped hosts exactly.

## Capabilities

### New Capabilities

- `settlement-place-registry`: the place and settlement records, their
  validation, and the derivation of shop identities and the service-host
  roster from places.

### Modified Capabilities

- `guild-registration`: the "Service hosts are created and converged from a
  declarative YAML roster" requirement changes its source — the roster is
  derived from the place registry rather than hand-written in
  `guild_economy.yaml`. Every validation, reuse, convergence and idempotence
  guarantee it makes is retained.

## Impact

- `world/lore/settlements/` — gains `settlements.py` (`SettlementArchetype`,
  `SettlementDefinition`, `SETTLEMENT_REGISTRY`), `places.py` (`PlaceKind`,
  `PlaceDefinition`, `PLACE_REGISTRY` assembled from per-settlement slices),
  `places_altoria.py`, and `shops.py` (derived `SHOP_REGISTRY` plus the two
  relocated validators).
- `world/lore/shops.py` — deleted. Its only non-test consumer is
  `world/rules/guild_config.py`.
- `world/rules/guild_config.py` — `validate_service_hosts` reads derived
  rows; shop resolution reads derived shop identities.
- `world/rules/rulebook/guild_economy.yaml` — `service_hosts:` removed.
- `world/lore/sync.py` — the new registries join `_ALL_REGISTRIES`.
- `world/rules/guild_economy.py`, `world/maps/bootstrap.py`,
  `commands/economy.py` — **untouched.** Startup synchronization still
  creates the two interiors from module constants and still interprets a
  roster; only where the roster comes from has changed. That is what makes
  this change behaviour-neutral and is why the runtime work is a separate
  change.
- **Depends on `commerce-assortment-registry`**: places reference
  assortments, and this change moves the shop identity that change reshaped.
- **No conflict with `ciaran-village-map`.** That change edits
  `world/maps/bootstrap.py` and `world/lore/wilderness_entry.py`, neither of
  which this change touches. The `bootstrap.py` collision belongs to
  `place-driven-service-sync`.
