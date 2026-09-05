# Service Anchoring — Design

**Date:** 2026-09-05
**Status:** Approved (brainstorming session 2026-09-05); second of three sequenced designs
(R3 → R2 → R1). Depends on the profession registries design
(`2026-09-05-profession-registries-design.md`); consumed by the companion-possession design
(`2026-09-05-companion-possession-design.md`).
**Scope:** Making "does this NPC's service travel with them" an authored datum
(`service_binding: person | place`), centralizing the scattered co-location gates behind one
read-only service resolver, defining anchor-darkness presentation, and ruling on schedule
interaction for traveling place-bound hosts.

---

## 1. Product Context

Every service gate today checks exactly one location fact: the host stands in the actor's room
(`world/rules/economy.py::_require_local_merchant` → `TradeReason.REMOTE_MERCHANT`; the guild
staff/examiner paths likewise). No gate asks whether the host is "at their shop", because hosts
were immobile sync fixtures. Party-follow (`world/rules/party.py::follow_companions`) breaks
that premise: any co-located LLMNPC — including a merchant or guild clerk after hours — can be
invited and walked anywhere, and their services follow implicitly. That emergent behavior was
never ruled on.

The user's authored-content requirement: a future confessor-style profession (a service
inherently performed anywhere) must be declarable as such in game data, exactly like a
brick-and-mortar shop declared as anchored — no code change either way. The flag is therefore
not "portable yes/no" but the binding axis `person | place`:

- `person` — co-presence is the service. This is today's behavior; declaring it converts an
  emergent accident into a contract.
- `place` — service additionally requires the host to stand at their authored anchor; a
  place-bound host traveling in a party turns their home anchor dark.

## 2. Design Decisions

| # | Decision | Rationale |
|---|---|---|
| D1 | **Co-presence is the default; anchoring is the declared exception**, expressed as `service_binding: person | place` per service component. `place` requires an anchor; `person` must carry none — both invalid combinations rejected fail-fast at load. | Matches the engine's current semantics (zero migration for existing services) and the lore intuition (confession travels, a storefront does not). |
| D2 | **Values are copied onto the component instance at construction** from the profession blueprint's `default_binding` (stored by R3, read here), overridable per NPC by import records/roster rows. | Assembly-time blueprint discipline (R3 D1): runtime gates read component fields with zero registry indirection; per-NPC exceptions (a legendary traveling antique dealer) stay data. |
| D3 | **One read-only resolver**: `world/rules/service_gate.py::service_available(host, actor, component) -> ServiceVerdict(allowed, reason)`. All service gates (economy buy/sell, guild staff board, examiner, future confessors) route through it. | One gate vocabulary; new professions wire in instead of re-deciding location semantics. |
| D4 | **Stable reason codes**: `remote` (not co-located — today's `REMOTE_MERCHANT` semantics preserved) and `off_anchor` (co-located but host is away from their place-binding anchor). | The webclient's existing `disabled_reason` affordance pattern renders both without new protocol shape. |
| D5 | **Anchor darkness is honest absence**: a place-bound host not present at the anchor room emits no service affordances there; the anchor room shows no ghost shop. | Mirrors the services-panel precedent "services are hosts, not data sources" — never invent stock rows for an absent host. |
| D6 | **Place-bound hosts fall silent while party-bound**: `settle_npc_schedules` skips a place-bound host who is a bound companion and currently off-anchor. Person-bound professions express "no work schedule" with `schedule_template: null` in their profession row. | Prevents the authored shift schedule dragging the merchant back to the storefront mid-adventure; the silence gate is the same mechanism the possession design reuses ("party-bound ⇒ autonomy suspended"). |
| D7 | **Invite availability is orthogonal to service binding.** The invite gate keeps exactly its four current conditions plus the busy gate; no profession may or may not be invited because of its binding. | Keeping the two axes separate avoids welding "can I party them" to "does their shop travel". |
| D8 | **`anchor_room` interpretation moves from placement-only (R3) to the binding anchor** with no data change — same authored field, now load-bearing. | One authored truth; R3 stored it, R2 gives it meaning. |

## 3. Resolver Contract

```
service_available(host, actor, component) ->
    ServiceVerdict(allowed: bool, reason: ServiceGateReason | None)

ServiceGateReason: REMOTE | OFF_ANCHOR | MALFORMED_BINDING
```

Rules, in order: actor and host co-located (else `REMOTE`); component binding is `place` and
`host.location != anchor` (else `OFF_ANCHOR`); malformed stored binding (unknown value, `place`
without anchor) fails closed as `MALFORMED_BINDING` — never defaults open, mirroring the
equipment fail-closed normalization idiom.

Migration: `_require_local_merchant`, the guild-staff board host check, and the examiner
co-location re-check all delegate. The existing test suites act as the behavior-equivalence
control: they pass unmodified except new `off_anchor` cases.

## 4. Presentation

- Exploration affordances for a service whose host is co-located but off-anchor render
  **disabled** with a fixed 正體中文 `disabled_reason` (「他的服務不在這裡營業。」类), using the
  affordance `disabled_reason.message` pattern already specified in exploration-affordances.
- Anchor-room darkness (D5): the room's affordance scan finds no present host → no entry, no
  placeholder. Re-opening happens automatically the moment the host is co-present again — no
  per-room state.
- The `off_anchor` verdict never blocks movement, combat, or party membership; it is a service
  availability read only.

## 5. Error Handling & Failure Modes

| Case | Behavior |
|---|---|
| Component with `place` binding, anchor attribute missing/corrupt | `MALFORMED_BINDING`, service unavailable, one bounded `log_warn` with host/service context |
| Host deleted while party-bound | Existing purge path unchanged; anchor goes dark through absence (no special handling) |
| Host re-invited back to anchor room | Availability recovers on the next presentation snapshot; no state to clear |
| Schedule settlement for a silent place-bound companion | Skipped silently by D6 gate; a person-bound host never had a schedule to skip |

## 6. Testing

- Pure: resolver matrix (co-located/remote × person/place × at-anchor/off-anchor/malformed),
  load-time invalid-combination rejections.
- Integration: economy buy/sell and guild board/examiner suites pass **unmodified** (the
  migration equivalence proof); new `off_anchor` rejection cases ride each gate.
- Presentation: affordance disabled-reason case for off-anchor co-present host; absence case at
  the darkened anchor room.
- Schedule: silence gate skips settlement for the traveling place-bound companion; unaffected
  NPCs settle byte-identically.
- New main capability `service-anchoring`; shard manifest updated; no LLM/network.

## 7. Non-Goals

- Possession (next design), invite-gate changes (D7), new profession content, anchor as a
  gameplay entity (no multiple anchors per host, no anchor relocation surface — a place-bound
  host's anchor is authored, not movable), merchant wallet/purse economics.
