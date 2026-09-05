# Proposal: service-anchoring-gate

## Why

Every service gate today checks exactly one location fact — host shares the actor's room
(`_require_local_merchant`, registration's local-staff rule, the exam authority check). Party
follow makes hosts mobile, and "does the service travel with the host" was never ruled on: a
confessor-type profession should serve anywhere, a storefront should not. This change turns the
profession row's `default_binding` (stored by the registry, D6 seam) into load-bearing data:
components carry `person|place` + anchor, one read-only resolver answers service availability,
and every existing gate routes through it.
Source design: `docs/superpowers/specs/2026-09-05-service-anchoring-design.md` (D1–D4).

## What Changes

- New capability: `world/rules/service_gate.py` — `service_available(actor, host, component)`
  returning `ServiceVerdict(allowed, reason)` with stable reason codes `remote |
  off_anchor | malformed_binding`; ordered rules (co-location first), malformed stored data fails
  closed with one bounded warn event.
- Assembly (shared `profession_assembly.py` + roster rows) copies each blueprint component's
  `default_binding` onto the created component as persistent `DBField`s and, for `place` rows,
  persists the anchor room
  identity from the roster's resolved room; `person` components store no anchor. Invalid
  combinations (`place` without anchor, `person` with anchor) are rejected where they are
  authored: config validation for the roster, schema validation for import records.
- **Gate rewiring, behavior-neutral until an off-anchor host exists:** `shop-economy`'s
  `_require_local_merchant` and the guild registration local-staff rule consult the resolver;
  an off-anchor place-bound host is refused with its own fixed message; the `guild-rank-exams`
  examiner authority check moves onto the resolver (MODIFIED delta) so an off-anchor examiner is
  refused like a remote one; shipped hosts stay at anchor while synced there, so every current
  scenario keeps passing.
- Schedule-state interaction (`interaction_reason`) and all four invite conditions are untouched
  (D7 orthogonality).

## Capabilities

### New Capabilities

- `service-anchoring`: binding/anchor persistence on components and the shared availability
  resolver with its reason vocabulary and fail-closed posture.

### Modified Capabilities

- `profession-registries`: `default_binding` graduates from stored-not-read to consumed by the
  gate (the D6 seam closes in this change).
- `shop-economy`: shop commands resolve the merchant through the resolver — `off_anchor` is
  refused alongside `remote`.
- `guild-registration`: registration rejects a place-bound off-anchor staff the same way it
  rejects remote staff.
- `guild-rank-exams`: `start_guild_exam` validates examiner authority through the shared resolver
  (`remote`/`off_anchor`/`malformed_binding` all refuse) instead of a bare co-location test.

## Impact

- New `world/rules/service_gate.py` + tests; edits in `world/rules/economy.py`,
  `world/rules/guild.py` (registration access), `world/rules/profession_assembly.py`,
  `world/rules/guild_config.py` (anchor validation), `world/imports/schema.py` (record-level
  binding/anchor validation), plus each touched gate's test modules.
- Depends on: `declarative-service-hosts` (assembly helper + roster anchor fields), which
  depends on `profession-import-assembly` → `profession-rulebook-registry`. Dependents:
  `service-anchor-presentation-silence` (renders this capability's verdicts), possession
  (silences reuse the same read surface). No player-facing command changes.
