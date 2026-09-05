# Design: declarative-service-hosts

Ratified: R3 design §5 + D7/D8/D9. Local implementation choices only.

## Context

`_sync_service_host(service_id, host_name, host_title, room, component_specs)` already takes a
`component_specs` tuple of `(ComponentClass, kwargs)`; `sync_service_content` passes the two
hardcoded tuples and pulls `host_name`/`host_title` from `GUILD_BRANCH_REGISTRY` /
`SHOP_REGISTRY`. `_find_service_host` anchors reuse on the component `service_id`, never the
key. `_cleanup_legacy_service_hosts` is the deletion-precedent shape (identity-shape-anchored,
named warning on ambiguity). The import loader's `_apply_profession` (change 2) is the assembly
mechanism this change extracts and shares.

## Goals / Non-Goals

**Goals:** roster is the single truth for which hosts exist and what they carry; shipped roster
reproduces today's two hosts bit-for-bit (same names, titles, rooms, component kwargs); sync
stays idempotent and fail-closed.

**Non-Goals:** anchor semantics (`anchor_room` stays placement-only here — service-anchoring owns
its meaning), new hosts/shops content, per-host schedules.

## Decisions

- **Roster validated in `guild_config.py`** with the catalog family (frozen `ServiceHostRow`,
  batch `GuildEconomyConfigError`): required fields present, `profession` names a registry row,
  the profession's blueprint component types all receive their identity kwargs from the row's
  authored kwargs map, `anchor_room` is a non-empty tag string (room existence is checked at
  sync time, not config time — config load must not touch the DB).
- **Shared helper extraction:** move `_apply_profession` from `world/imports/loader.py` to
  `world/rules/profession_assembly.py` (pure function over a profession row + authored kwargs
  + an entity: attaches blueprint-minus-explicit components via
  `entity.components.add(cls.create(host, **kwargs))`, mirroring the sync loop). The loader
  keeps its batch-rejection error wrapping around the helper's raises; the sync calls the same
  helper so "assembly" is one code path (AGENTS.md single-convention rule).
- **`_sync_service_host` signature change:** now takes the parsed `ServiceHostRow`; creation
  persists `host_name`/validated `host_title`, sets race/baseline/adult identity exactly as
  today (unchanged), then calls the assembly helper with `{component_type: kwargs}` from the
  row. Reuse path never renames/retitles (preserved). `anchor_slot` derives from the row's
  first blueprint component.
- **Roster convergence replaces the one-time cleanup:** generalize the legacy path — every live
  NPC carrying a component whose `service_id` matches no roster row is deleted with the same
  identity-shape guard (carries the anchor component ⇒ service host; titled + ambiguous ⇒ named
  warning, no guess). The old `_LEGACY_HOST_KEYS` ASCII-key residue stays covered because those
  hosts also fail the roster-membership test.
- **`GUILD_SERVICE_KEY` / `MERCHANT_SERVICE_KEY` constants retire** into roster data (the
  roster rows carry `service_id: altoria_guild_master` / `altoria_merchant` verbatim to keep
  reuse identity stable for existing dev databases).

## Risks / Trade-offs

- [Deletion sweep kills a host a concurrent dev fixture created] → identity-shape guard +
  single-host invariant means only roster-absent service hosts die; fixtures using roster
  `service_id`s are untouched; the sweep logs one info event per deletion.
- [Config-time validation cannot see rooms] → sync fails closed with the existing
  `guild_service_interiors_missing` warning path extended to name the roster row.
