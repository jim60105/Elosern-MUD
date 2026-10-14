# Design

## Context

world/maps/{bootstrap.py,wilderness_provider.py,instance.py,map_data.py}; typeclasses/rooms.py; authored settlement/place/wilderness records; world/art/scene_definitions.py authored room-key registry; map/typeclass tests.

Observed current panel contracts are art v2, roster v2, gallery v2 and dream v2. The official catalog indexes external monster/preset/npc content, while figures/scenes/avatars/editors own separate loading flags. The approved design and proposal.md define the named slice; planned later versions are batch contracts, not existing implementation claims.

## Goals / Non-Goals

**Goals:** Deliver this complete independently testable production boundary with exact source ownership and objective acceptance.

**Non-Goals:** Gameplay, generation scheduling, new production commands, global cache/retry/store, telemetry transport, GM previews, compatibility/migrations and hot reload. Text clients/favicons/unrelated icons remain unchanged.

## Decisions

Add an explicit authored mapping for grid/place/interior/instance metadata, registered under the art room-key vocabulary. Extend the existing map input records only where needed; do not derive room_art_key from names or dynamic ids. Map startup/construction writes scene_archetype and optional room_art_key idempotently. Permanent Room interiors must expose readable scene metadata without changing doorway/typeclass behavior. Store fields via existing AttributeProperty/attributes ownership; raw mixin assignment remains permissive while authored definitions/construction validate keys.

Current wilderness_provider.at_prepare_room assigns region_for_coordinates directly to scene_archetype, but region keys are not registered scene types. Add a source-authored region-to-scene mapping: forest regions use forest_path, central mountains mountain_path, coastal regions coastal_path and plains/hills wilderness_path. Preparation recomputes every logical scene fact and removes a preceding room_art_key when absent, before consumers resolve the view. Identity derives from wilderness name plus coordinates, never TerrainRoom pk. Grid identity uses authored map/z coordinate identity, permanent interiors authored place key, dynamic nonpooled instances their stable instance identity (not art key). Do not fabricate coordinates for exit-graph interiors. The art view reads metadata; it never writes or repairs it. No queue/prompt/per-room generated asset is added.

## Risks / Trade-offs

- Cross-surface shape mismatch: every wire owner ships its serializers, active schema/version/validators and all production readers together. Internal loading/source prerequisites keep one current wire until its named cutover.
- Unsafe retention or hidden fault: stable layer ranks and explicit authorized retention tokens distinguish priority/regeneration from removal/access loss; availability failure is separate from expected absence.
- Asset rights/budget uncertainty: all real artwork production has a complete owning pack, including two terminal images; catalog assumes no uncertain promotion/reproduction branch.
- Shared files/manifests: obey Batch dependencies and serialize overlapping edits; unrelated asset bytes have disjoint ownership.

## Migration Plan

Apply only after listed prerequisites land. This pre-release project has no compatibility/data migrations. Keep the current single wire shape until its atomic owning serializer/client cutover; remove obsolete internal projections/readers in that owner, never aliases/re-exports. Each named slice delivers its tests/docs/runtime boundary within the itemized 6.25 hours. Rollback reverts the complete owning slice and consumers together. Planning does not apply or archive these artifacts.
