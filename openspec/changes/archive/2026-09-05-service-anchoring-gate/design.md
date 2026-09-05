# Design: service-anchoring-gate

Ratified: R2 design D1–D4. Local implementation choices only.

## Context

Gate sites today: `world/rules/economy.py::_require_local_merchant` (room equality →
`TradeReason.REMOTE_MERCHANT`), guild registration's "absent or remote staff" rejection
(`guild-registration` spec), exam authority co-location. Component creation happens in exactly
one shared place after change 3: `world/rules/profession_assembly.py`. Anchor identity is
carried by the roster's resolved room object — persisting "the anchor" must be reload-safe, so
the component stores the anchor ROOM's dbid (int), resolved lazily at read time; a deleted
anchor room makes a `place` binding malformed → fails closed (never defaults open — equipment
normalization idiom).

## Goals / Non-Goals

**Goals:** one resolver, stable vocabulary, zero behavior drift for every shipped configuration
(shipped hosts are `place`-bound and always synced to their anchor, so `off_anchor` is
unreachable until a host parties away — which possession-era gameplay enables).

**Non-Goals:** presentation (`disabled_reason` rendering — change 5), schedule silence (change
5), possession mechanics, invite-gate changes (D7).

## Decisions

- **Resolver signature takes the actor and one component:**
  `service_available(actor, host, component) -> ServiceVerdict`; callers that resolve multiple
  components on one host (guild staff + examiner) call it once per component — the rules are
  per-component semantics, and batching would invent cross-component coupling the design
  doesn't have.
- **`remote` first, then `off_anchor`:** the resolver checks co-location exactly as today's
  gates do (same message lineage), then `place`-binding anchor equality. Callers map
  `remote` to their existing reason codes (`REMOTE_MERCHANT`, registration's remote-staff
  line) — that keeps every existing scenario's wording; `off_anchor` gets a NEW fixed zh-TW
  message owned by the gate module's reason table (both `shop-economy` and `guild-registration`
  deltas cite it), so text stays registry-owned.
- **Persistence shape on components:** `service_binding` (str) + `anchor_room_id` (int | None)
  as Evennia contrib-components **`DBField` persistent fields** on each service component class
  (`typeclasses/components.py` already imports `DBField` from
  `evennia.contrib.base_systems.components`; plain instance attributes would not survive reload
  and are forbidden here), written only by `profession_assembly` at creation (single-writer);
  the resolver reads them. A pre-existing component without the fields (dev DB created before
  this change) reads as `person`-unbound? NO — fails closed: shipped hosts are re-synced from
  the roster every startup and the roster now always supplies binding+anchor, and assembly only
  attaches components at creation, so sync MUST backfill the two fields for reused hosts in
  this change (bounded, roster-authoritative — the same never-rename rule permits attribute
  convergence since binding is authored config, not runtime identity). Reload survival is
  verified by a save/re-read test, not assumed from the framework. Decision pinned in the
  spec's scenarios.
- **Malformed binding warn event:** one `log_warn` per resolution with a per-host
  `ndb` debounce flag; never per-frame spam.

## Risks / Trade-offs

- [Backfill on reuse looks like runtime state write] → binding/anchor are authored config
  re-converged from the roster (idempotent), not runtime history; the never-retitle rule
  protects identity fields only. Documented in the sync docstring.
- [Two hosts, two bindings disagreeing on one door] → resolver is per-component; each gate asks
  about the component it serves.
- [Source design D2 promises a per-NPC binding override; no representation ships here] →
  deliberate deferral, amendment recorded in the source design's change-mapping section: the
  documented exception (traveling antique dealer) is expressible today as its own profession row
  with `default_binding: person`, and the project has no shipped content needing a per-host
  disagreement. Adding a one-line roster/import override before a second exception exists is
  weightless abstraction; when it lands it travels with the roster row and import schema
  (change 3's surface), not the resolver.
