## Context

See `proposal.md` — Why, and
`docs/superpowers/specs/2026-09-20-settlement-shops-design.md` §3.2 and
§3.3.

One existing contract does most of the work. `validate_service_hosts`
(`world/rules/guild_config.py:337`) already projects a row's authored kwargs
onto its profession blueprint, enforces blueprint coverage, rejects dead
kwargs, and refuses a person-bound component on an anchored row — all
without touching the database. This change changes what feeds it, not what
it does.

## Goals / Non-Goals

**Goals:**

- One authored record per location, with the duplicated declarations derived
  from it.
- A settlement vocabulary the remaining archetypes can use.
- Provable behaviour-neutrality: the derived roster must reproduce the
  shipped hosts exactly.

**Non-Goals:**

- Any runtime change. `world/rules/guild_economy.py`,
  `world/maps/bootstrap.py` and `commands/economy.py` are untouched;
  `place-driven-service-sync` owns them. Interiors are still created from
  module constants after this change, and hosts are still built human.
- Content. The capital's two existing locations move into the new shape and
  nothing is added.
- Price variation. `place-price-scaling` adds `extra_item_keys`,
  `excluded_item_keys`, scales and overrides to the place row.
- The lore document's applicability matrix. Archetypes are a vocabulary
  here; nothing yet validates "this archetype may not have this place kind".

## Decisions

**Stop at the load boundary.** This change was originally one change with
the runtime work, and was split because that version bundled two new
registries, two derivations, three identity fields, a `bootstrap.py`
rewrite, a module deletion and a command change into one day. The seam
chosen is load-time versus runtime, because it is the one that yields a
provably neutral first half: after this change every byte
`sync_service_content` and `sync_service_interiors` observe is identical to
today's, so the neutrality proof is a real gate rather than a hopeful
assertion. The alternative seam — splitting off host race/subrace/sex —
would have left a 1.5-hour remainder and a 6.5-hour first half, which is
barely a split.

**Generic `authored_kwargs`, not a `shop_key` field.** The obvious shape for
a place is a nullable `shop_key`. It does not work: the guild hall's host is
`guild_staff`, whose blueprint needs `branch_key` and `dialogue_key`, and a
derived roster row missing those fails blueprint coverage at load. A frozen
mapping projected onto the blueprint is exactly what `validate_service_hosts`
already consumes, so the derivation is a rename rather than new logic, and
any future profession works without another field.

**Derive, do not duplicate.** `SHOP_REGISTRY` and the roster are both views
over `PLACE_REGISTRY`. The alternative — keep them authored and add a
consistency check — was rejected because a check tells you the two disagree
after you have already written both, whereas derivation makes disagreement
unrepresentable.

**`world/lore/shops.py` is deleted rather than kept as a shim.** It has
exactly one non-test consumer, `world/rules/guild_config.py`. Everything
else is tests and synthetic fixtures. A shim would preserve an import path
nobody needs and hide where shop identity actually comes from.

**A separate `SettlementArchetype`, not an extension of `AnchorKind`.**
`AnchorKind` includes `dungeon` and classifies geography; several of its
members are not settlements at all. Widening it would make "every anchor
kind is a settlement archetype" false in the type. The two vocabularies
overlap in wording and not in meaning, so they stay apart, joined by the
settlement key equalling the anchor key.

**Places live in per-settlement modules.** `world/lore/items/` already
concatenates `data_*.py` slices into one registry in a fixed order; places
follow that precedent with one module per settlement. This is not
cosmetic — it is what lets `altoria-trading-places` and
`ciaran-village-commerce` be authored in parallel without editing the same
file.

**The place row carries `host_race`, `host_subrace` and `host_sex` now,
unread.** The fields and their validation land here because they belong to
the record's shape and because `places_altoria.py` would otherwise have to
be edited again immediately. Nothing reads them until
`place-driven-service-sync`, which is stated in the spec rather than left
for a reader to discover.

## Risks / Trade-offs

- **The two shipped hosts must come out bit-for-bit identical**, or the
  `sample-city-altoria` guarantees break. → This is the change's main gate.
  Because no runtime file is touched, the comparison is exact: the derived
  roster rows must equal the removed YAML rows field for field.
- **`places_altoria.py` authors `human_plains` on two hosts that today have
  no subrace.** `LivingEntity.subrace` defaults to `None`, and the field is
  unread until the next change, so nothing changes here — but when it is
  read, neutrality holds only because that subrace's `StatModifiers()` are
  all zero (`world/lore/races.py`). → Verified, but it is a coincidence.
  Authoring `None` for the two pre-existing hosts is the safer option and is
  the recommended default unless the neutrality proof in the next change
  compares stats.
- **Deriving `SHOP_REGISTRY` at import time creates a new import edge** from
  the shop view to the place registry, which imports the settlement
  registry. A cycle back into `world/rules/*` would break startup.
  → The lore package must not import from `world/rules/*` at module scope;
  the current `shops.py` already uses function-local imports for exactly
  this reason and the derived module keeps that discipline.
