# Design

## Context

world/art/presenter.py; gallery_match.py/gallery_fallback.py; world/art/tests/test_portrait_attempts.py and affected existing direct presenter tests; art developer docs.

Observed current panel contracts are art v2, roster v2, gallery v2 and dream v2. The official catalog indexes external monster/preset/npc content, while figures/scenes/avatars/editors own separate loading flags. The approved design and proposal.md define the named slice; planned later versions are batch contracts, not existing implementation claims.

## Goals / Non-Goals

**Goals:** Deliver this complete independently testable production boundary with exact source ownership and objective acceptance.

**Non-Goals:** Gameplay, generation scheduling, new production commands, global cache/retry/store, telemetry transport, GM previews, compatibility/migrations and hot reload. Text clients/favicons/unrelated icons remain unchanged.

## Decisions

Introduce one canonical portrait attempt enumerator using the already shipped art-domain descriptor vocabulary. Existing resolve_entity/resolve_character select from that enumerator to satisfy their current flat API until the atomic portrait serializer/client migration; all callers still consume exactly one current contract. The enumerator is used in production immediately for selection and attributed facade diagnostics, not only tests. No alias, dual-version client, re-export or second selector exists. Keep resolve_subject/resolve_scene scene delegation untouched; test current v2 art and roster serializer parity while this change lands. Portrait wire owner removes the selected-flat portrait projection when it migrates every reader. This staged internal refactor is not a persistent compatibility layer.

Ranks/ids and reason classification are fixed by the shared design. Preserve bound-card specificity/newest tie, personal official selection, record default, classic, optional official default and alpha policies. Existence/identity faults remain at the original source slot; explicit preferences remain stored; unselected sibling rejections do not taint selected sources. Recorded generation and official availability remain independent even with generation disabled. No new queue/status/gallery/room/file write occurs while presenting. Current flat serializers retain their pre-existing vocabulary until owning cutover rather than falsely marking official/alpha as generated success.

Register pure/synthetic tests and production construction/selection smoke using real writer/admission boundaries. The canonical geometry wire relocation is owned by portrait-image-contract, while current chain/fallback semantics and source facts are owned here. Both named slices include the affected direct caller/test files so no old shape assertion survives the final cutover.


## Risks / Trade-offs

- Cross-surface shape mismatch: every wire owner ships its serializers, active schema/version/validators and all production readers together. Internal loading/source prerequisites keep one current wire until its named cutover.
- Unsafe retention or hidden fault: stable layer ranks and explicit authorized retention tokens distinguish priority/regeneration from removal/access loss; availability failure is separate from expected absence.
- Asset rights/budget uncertainty: all real artwork production has a complete owning pack, including two terminal images; catalog assumes no uncertain promotion/reproduction branch.
- Shared files/manifests: obey Batch dependencies and serialize overlapping edits; unrelated asset bytes have disjoint ownership.

## Migration Plan

Apply only after listed prerequisites land. This pre-release project has no compatibility/data migrations. Keep the current single wire shape until its atomic owning serializer/client cutover; remove obsolete internal projections/readers in that owner, never aliases/re-exports. Each named slice delivers its tests/docs/runtime boundary within the itemized 6.5 hours. Rollback reverts the complete owning slice and consumers together. Planning does not apply or archive these artifacts.
