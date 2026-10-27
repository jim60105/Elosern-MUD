# Services Panel Protocol (schema 8) and the Selected-Provider Read

This document records the version-8 `services` presentation panel, the
provider identity every service section carries, and the private
`services.open` read a provider drawer uses. It supplements the version-1
service panel contract in
[WebClient Service and Character-Creation UI](/superpowers/specs/2026-08-02-webclient-service-creation-ui-design).

## Registration and Surface

The production presentation registry registers one `services` panel at
schema version 8. It is available in exploration mode. Every producer,
serializer, validator and client mirror reads the same `SERVICES_SCHEMA_VERSION`
(8) and the same section field sets.

The available payload contains exactly `schema_version`, `available`, `kind`,
`host`, `player`, `guild`, `rank`, `shop`, and `pagination`. `available` is
true and `kind` is `"services"`. The common unavailable form
(`{available: false, reason}`) still replaces the whole panel when a global
prerequisite, such as the actor or player summary, cannot be read without
mutation.

Personal inventory is not part of this panel. The `party_inventory` panel owns
it, including the purse rows.

## Provider Identity

Every non-null service section names the exact NPC it was built from:

| Section | Required fields | Provider rule |
| --- | --- | --- |
| `guild` | `provider_id`, `branch_label`, `rank_ladder`, `registration`, `board`, `quests` | The selected `GuildStaff` holder. |
| `rank` | `provider_id`, `rank`, `merit`, `next_rank`, `next_threshold`, `merit_qualified`, `exam_request` | The selected `GuildExamReception` holder, never a `GuildStaff` requirement. |
| `shop` | `provider_id`, `open`, `member_id`, `stock`, `sellable` | The selected `Merchant` holder. |

`provider_id` is a positive JavaScript-safe integer dbref, at most
`9_007_199_254_740_991`. The top-level `host` object remains display-only
metadata and is never authority for a mutation. A mutation carries its own
`npc_id`, which the adapter revalidates against committed state.

The `rank` surface moved from `guild.rank` to the top level so a reception-only
counter can publish it without guild staff, board or registration. When both
the guild and rank sections ship, the rank's grade keys must belong to the
guild section's `rank_ladder`; a reception-only snapshot ships `guild: null`.

## Untargeted and Targeted Reads

`build_services_view(actor, viewed=None, *, provider_id=None)` has two modes.

Without `provider_id` the read keeps the existing room discovery for the full
snapshot. Zero or multiple providers of one class make only that class's
surface unavailable with a stable reason such as `no_local_service_host` or
`ambiguous_service_host`.

With `provider_id` the read resolves one exact visible, co-present NPC through
`world.rules.service_targets.require_service_provider` and builds every section
from that NPC alone. A capability the selected NPC lacks stays null. No
co-located provider contributes a surface to the selection, and an unusable
selection raises instead of reading an empty snapshot.

Both modes are read-only. Combat suppresses the remote service surfaces while
keeping the canonical player summary. Possession omits the guild and rank
surfaces while the merchant surface keeps its ordinary viewed-member rows.

## The `services.open` Action

`services.open` is a registered session read. It has no game clock or effect,
publishes no panel, and is not a typed command.

The exact request payload is `{npc_id}`. The private success result carries its
own data slot, exactly two fields:

```json
{
  "npc_id": 612,
  "services": { "schema_version": 8, "available": true, "kind": "services", "...": "the complete schema-8 snapshot" }
}
```

`npc_id` repeats the selected provider and every shipped section names the same
provider. The complete result is validated before delivery, including the
eight-field result-data ceiling and the existing result-data byte budget. A
read that cannot fit returns the bounded `services_too_large` refusal instead of
truncating rows or relaxing a transport limit.

Every outcome is presentation-free (`no_presentation: true`), and a successful
read declares an empty `affected_panels` tuple. Rejections omit `data`
entirely. Stable rejection codes are `no_such_target` (unknown, invisible,
departed or malformed identity), `wrong_capability`, `off_anchor`,
`malformed_binding`, `schedule_blocked`, `active_combat`, `possessed_service`,
`not_allowed_mode` and `services_too_large`.

A client drawer adopts a result only when the wrapper is exactly
`{npc_id, services}`, the echoed `npc_id` is the one it asked for, and every
shipped section names that provider. A stale, foreign, substituted or rejected
answer closes the drawer's snapshot instead of reopening another provider's
surface. While a drawer stays open, a committed presentation revision repeats
the read for the same provider. The selection is never persisted on the actor
or the NPC, and no polling runs.

## Provider Mutations

`guild.register`, `guild.quest_accept`, `guild.quest_turnin`,
`guild.exam_request`, `shop.buy` and `shop.sell` require `npc_id` in addition to
their existing bounded fields. The adapter resolves that identity through
`world.rules.service_targets.require_service_mutation`, which rechecks
visibility, co-presence, capability, binding, schedule, active combat and
possession before the deterministic domain API runs. `guild.exam_request`
passes the resolved reception as the request speaker.

`guild.quest_abandon` admits exactly two shapes. An ordinary guild record
requires `{quest_id, npc_id}` and its selected staff host. A private escort
record keeps `{quest_id}` alone and needs no host. The adapter reads the
canonical record kind and rejects the wrong shape with
`abandon_target_mismatch`, so a missing `npc_id` can never turn an ordinary
record into host-free abandonment.

`guild.quest_track` and the personal inventory actions remain host-independent.

## Bounds

| Surface | Ceiling |
| --- | ---: |
| `guild.board` | 12 rows |
| `guild.quests` | 12 rows |
| `shop.stock` | 12 rows |
| `shop.sellable` | 12 rows |
| Canonical services payload | 65,536 bytes |
| `services.open` result data | 65,536 bytes minus the standard result reserve |

Pagination totals equal the shipped row counts for their surface and stay zero
for a null surface. Every refusal writes nothing.
