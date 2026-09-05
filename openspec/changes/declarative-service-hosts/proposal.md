# Proposal: declarative-service-hosts

## Why

`world/rules/guild_economy.py::sync_service_content` hardcodes every service host — names come
from branch/store registries, but the room, the profession-shaped component combination
(`GuildStaff+GuildExaminer+ScriptedDialogue`, `Merchant`), and the very list of hosts live in
Python. Opening a second shop or re-theming a clerk is a code change, which contradicts the
authored-content pipeline (YAML + JSON) the profession registry exists to serve. With the
registry landed (`profession-rulebook-registry`) and import assembly available
(`profession-import-assembly`), the sync can become a pure interpreter of a roster.
Source design: `docs/superpowers/specs/2026-09-05-profession-registries-design.md` (§5, D7–D9).

## What Changes

- `world/rules/rulebook/guild_economy.yaml` gains a `service_hosts:` roster section: one row per
  host with `name`, `title`, `profession`, `anchor_room` (room tag), `service_id`, and the
  authored component identity kwargs (`shop_key` / `branch_key` / `dialogue_key`). The shipped
  roster replicates today's two hosts exactly (guild master with branch kwargs + merchant with
  `altoria_general_store`), so the conversion is behavior-neutral.
- `sync_service_content` becomes a roster interpreter: for each row, resolve the room by tag,
  find-or-create the host on the `service_id` anchor (single-host invariant and
  `ServiceAnchorIntegrityError` preserved verbatim), ensure adult identity, and assemble
  components through the shared profession assembly helper. A roster row with an unknown
  profession, unknown room tag, or missing identity kwargs fails sync closed with a named
  integrity error.
- The component-assembly helper is extracted from `world/imports/loader.py` to
  `world/rules/profession_assembly.py` (owned here; loader re-imports it) so import and sync
  share ONE assembly mechanism without `world/rules/` importing `world/imports/`.
- **BREAKING (internal, pre-release):** surplus live hosts whose `service_id` is absent from the
  roster are removed through the existing `_cleanup_legacy_service_hosts` precedent; the roster
  is authoritative (D9, no back-compat).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `guild-registration`: new requirement — service hosts are created and converged from the
  declarative roster, with its validation matrix and idempotent re-sync.

## Impact

- `world/rules/rulebook/guild_economy.yaml`, `world/rules/guild_config.py` (roster parsed +
  validated with the catalog's fail-fast family), `world/rules/guild_economy.py` (sync becomes
  interpreter; `_cleanup_legacy_service_hosts` generalized to roster convergence),
  `world/rules/profession_assembly.py` (new shared helper) and `world/imports/loader.py`
  (imports it).
- Depends on: `profession-rulebook-registry` (rows), `profession-import-assembly` (helper to
  extract). Code conflicts: touches the same `sync_service_content` body the anchoring change
  will later read `default_binding` from — this change lands first, no overlap otherwise.
- No player-facing commands, no webclient surface.
