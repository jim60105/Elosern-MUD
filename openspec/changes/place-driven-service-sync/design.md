## Context

See `proposal.md` — Why, and
`docs/superpowers/specs/2026-09-20-settlement-shops-design.md` §3.2 and §7.

`settlement-place-registry` has already landed the records and the
derivations, and did so without touching a single runtime file — every byte
`sync_service_content` and `sync_service_interiors` observe today is
identical to what they observed before it. This change is the other half:
moving the runtime onto those records.

Two existing behaviours are preserved rather than re-derived.
`_sync_service_host` (`world/rules/guild_economy.py:73`) reuses a host by
component `service_id` rather than by display key, and never renames or
retitles. `sync_service_interiors` (`world/maps/bootstrap.py:85`) creates
interiors idempotently by tag and warns-and-skips a missing exterior.

## Goals / Non-Goals

**Goals:**

- Adding a location becomes a data edit with no code change.
- A settlement whose inhabitants are not human produces hosts of the right
  people.
- A player can tell which shop they are standing in.

**Non-Goals:**

- Content. The capital's two existing locations move onto the new path and
  nothing is added.
- Changing the reuse, convergence or idempotence contracts. They are
  inherited verbatim.
- Reading `host_sex` anywhere. This change writes it; sexual-state and
  appearance surfaces already read the field wherever they read it for any
  other entity.

## Decisions

**Race, subrace and sex are creation-time, not converged.**
`_sync_service_host` converges component bindings on every run but treats
name and title as write-once. Race is currently written only when unset —
effectively write-once by accident, since `race` starts `None`. Sex cannot
use that idiom because it defaults to `"other"`, not `None`. Rather than
invent a third policy, all three are written inside the `host is None`
branch beside `npc_title`, before `apply_race_baseline()`. An authored edit
then takes effect through the existing convergence path — the roster deletes
a host whose `service_id` disappears — which is the mechanism the
never-retitle contract already relies on. The alternative, converging them
every sync, would make race a runtime-writable identity field and break the
symmetry with title for no gain, since content edits land with a database
rebuild at this stage anyway.

**The place's room name reaches the command through `ShopConfig`.**
`commands/economy.py::CmdShopStock` resolves a `Merchant` component, reads
its `shop_key`, and looks the config up via `get_catalog().shop_configs`. It
has no path to a place. Giving the command a second registry lookup would
put the lore package in the command layer; instead `ShopConfig` gains a
`display_name_zh` filled during shop resolution, and the command prints a
field it already holds.

**Interiors are grouped by settlement before resolution.** The current
function resolves an exterior by `(x, y, zcoord)` with the zcoord written
into a module constant. Iterating places naively would need each row to
carry its own zcoord, duplicating what the settlement record already says.
Grouping by `settlement_key` and resolving the zcoord once per settlement
keeps the coordinate space declared in exactly one place, which is the whole
point of the settlement record.

**The warn-and-skip path is kept, not upgraded to an error.** A missing
exterior is a real state during a partial grid build, and the existing
behaviour lets the remaining locations synchronize. Turning it into a hard
failure would make one bad row take down every service in the world —
precisely the failure mode this design set has been removing elsewhere.

## Risks / Trade-offs

- **This change and `ciaran-village-map` both rewrite
  `world/maps/bootstrap.py`.** → Land the map change first. There the edit
  is the map assembly at the top of the file; here it is
  `sync_service_interiors`. In that order the two touch different regions;
  concurrently they collide.
- **The two shipped hosts must survive the move unchanged.** They are
  reused by `service_id`, so the authored race/subrace/sex written in the
  `host is None` branch will not touch an existing host at all — the
  neutrality risk is on a fresh database. → The proof compares a recreated
  host against the pre-change expectation. If `places_altoria.py` authors
  `human_plains` rather than `None` for those two, the comparison must
  include stats, because neutrality then rests on that subrace's
  `StatModifiers()` being all zero.
- **`host_sex` becomes meaningful for hosts that previously had none.**
  Every existing service host runs at the `"other"` default; after this
  change a recreated host carries its authored value. → Intended, and the
  reason the field was added, but it is a visible change for anything that
  reads sex off an NPC.
