## Context

See `proposal.md` — Why, and
`docs/superpowers/specs/2026-09-20-settlement-shops-design.md` §3.2, §3.3
and §7.

Three existing contracts constrain the shape. `validate_service_hosts`
(`world/rules/guild_config.py:337`) already projects a row's authored kwargs
onto its profession blueprint, enforces blueprint coverage, rejects dead
kwargs, and refuses a person-bound component on an anchored row — all
without touching the database. `_sync_service_host`
(`world/rules/guild_economy.py:73`) already reuses a host by component
`service_id` rather than by display key, and never renames or retitles.
`sync_service_interiors` (`world/maps/bootstrap.py:85`) already creates
interiors idempotently by tag and warns-and-skips a missing exterior. None
of that logic changes; only its input does.

## Goals / Non-Goals

**Goals:**

- One authored record per location.
- Preserve every validation, reuse and idempotence guarantee the roster path
  already makes.
- Make a non-human settlement expressible.

**Non-Goals:**

- Content. This change moves the capital's existing guild hall and general
  store into the new shape and adds nothing. `altoria-trading-places` and
  `ciaran-village-commerce` add locations.
- Price variation. `place-price-scaling` owns scaling and overrides; the
  place row's `extra_item_keys` / `excluded_item_keys` arrive with it.
- The applicability matrix from the lore document. Archetypes are declared
  here as a vocabulary; nothing validates "this archetype may not have this
  place kind" yet.

## Decisions

**Generic `authored_kwargs`, not a `shop_key` field.** The obvious shape for
a place is a nullable `shop_key`. It does not work: the guild hall's host is
`guild_staff`, whose blueprint needs `branch_key` and `dialogue_key`, and a
derived roster row missing those fails blueprint coverage at load. A frozen
mapping projected onto the blueprint is exactly what `validate_service_hosts`
already consumes, so the derivation is a rename rather than new logic, and
any future profession works without another field.

**Derive, do not duplicate.** `SHOP_REGISTRY` and the roster are both views
over `PLACE_REGISTRY` computed at import/load time. The alternative — keep
them authored and add a consistency check — was rejected because a check
tells you the two disagree after you have already written both, whereas
derivation makes disagreement unrepresentable.

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

**Race, subrace and sex are creation-time, not converged.**
`_sync_service_host` converges component bindings on every run but treats
name and title as write-once. Race is currently written only when unset —
effectively write-once by accident, since `race` starts `None`. Sex cannot
use that idiom because it defaults to `"other"`, not `None`. Rather than
invent a third policy, all three are written inside the `host is None`
branch beside `npc_title`. An authored edit then takes effect through the
existing convergence path (the roster deletes a host whose `service_id`
disappears), which is the mechanism the never-retitle contract already
relies on. The alternative — converge them every sync — would make race a
runtime-writable identity field and break the symmetry with title for no
gain, since content edits land with a database rebuild anyway at this stage.

**Places live in per-settlement modules.** `world/lore/items/` already
concatenates `data_*.py` slices into one registry in a fixed order; places
follow that precedent with one module per settlement. This is not
cosmetic — it is what lets `altoria-trading-places` and
`ciaran-village-commerce` be authored in parallel without editing the same
file.

**The place's room name reaches the stock listing through `ShopConfig`.**
`commands/economy.py::CmdShopStock` resolves a `Merchant` component, reads
its `shop_key`, and looks the config up via `get_catalog().shop_configs`. It
has no path to a place. Rather than give the command a second registry
lookup, `ShopConfig` gains a `display_name_zh` populated during shop
resolution from the owning place's `room_name_zh`. The command then prints a
field it already holds, and the place registry stays out of the command
layer.

## Risks / Trade-offs

- **This change is the largest of the seven and may overrun a day.** It
  carries two new registries and an assembly pattern, two derivations
  (shop identities, host roster) with every existing rejection preserved,
  three new identity fields with their validation, a rewrite of
  `sync_service_interiors`, a module deletion, a command-output change, and
  a bit-for-bit neutrality proof for the two shipped hosts. → If it has to
  be cut, §3 (host race/subrace/sex) is the clean seam: it is self-contained,
  has its own task group, and only `ciaran-village-commerce` depends on it.
  The two things not to rush are the blueprint-kwarg projection for the
  `guild_staff` host and the neutrality proof.
- **The two pre-existing capital hosts gain a subrace they never had.**
  `LivingEntity.subrace` defaults to `None`, and both shipped hosts run with
  it unset; authoring `human_plains` on them is behaviourally neutral only
  because that subrace's `StatModifiers()` are all zero
  (`world/lore/races.py`). → Verified, but it is a coincidence rather than a
  guarantee. The neutrality proof must compare stats, not just identity
  fields; authoring `None` instead is the alternative if it ever stops
  holding.
- **This change and `ciaran-village-map` both rewrite
  `world/maps/bootstrap.py`.** → Land the map change first: it adds a second
  entry to `XYMAP_DATA_LIST` and touches `sync_grid`, while this change
  replaces the interior path. Taken in that order each edits a different
  function. Taken together they collide.
- **Deriving `SHOP_REGISTRY` at import time creates a new import edge** from
  the shop view to the place registry, which imports the settlement
  registry. A cycle back into `world/rules/*` would break startup.
  → The lore package must not import from `world/rules/*` at module scope;
  `shops.py` already uses function-local imports for exactly this reason and
  the derived module keeps that discipline.
- **The two shipped hosts must come out bit-for-bit identical**, or existing
  saves and the `sample-city-altoria` guarantees break. → The
  behaviour-neutrality scenario in the `guild-registration` delta is the
  gate; it compares a recreated host against the pre-change expectation
  rather than against a literal.
- **`host_sex` is authored but nothing reads it yet.** Sex participates in
  sexual-state and appearance surfaces elsewhere, not in trade. → Accepted:
  it is authored identity that was previously unwritable, and the village
  content change is the first consumer that cares.
