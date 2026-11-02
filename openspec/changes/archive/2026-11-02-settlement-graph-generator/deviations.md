# Implementation deviations

The implementation departs from `design.md` in six deliberate places. Each one
is required by the delta spec that the archive synced into
`openspec/specs/settlement-graph-generation/spec.md`; the emitted behaviour is
never weaker than the plan.

1. **Degree cap 6.** `GenerationConfig.max_degree` defaults to and is bounded at
   6, so `degree_overflow` refuses anything above six instead of the design's
   8. Justification:
   `settlement-graph-generation::generated-graphs-satisfy-the-structure-rules-and-the-terrain-fit-lint`
   ("No node SHALL have ... more than six roads").
2. **`water_unreachable` refusal.** A waterside, harbour or crossing layout whose
   water is within reach but unreachable is refused, where the design implied
   the contact target simply drops. Justification:
   `settlement-graph-generation::generated-footprints-are-connected-walkable-masks-centred-on-the-location`
   ("For a waterside, harbour or crossing layout it SHALL touch its water").
3. **Existing-binding refusal breadth.** Refusal also covers a location bound by
   a document under a different map identity (map-core rejects
   `duplicate_location_binding`), and `--missing` excludes bound locations.
   Justification:
   `settlement-graph-generation::the-generator-never-overwrites-and-batches-in-a-fixed-order`
   ("SHALL refuse a location that already has a settlement document").
4. **`loop_shortfall` reconciled after pruning.** The warning reports the deficit
   against the final, post-pruning loop count. Justification: the same structure
   requirement's loop clause ("loops up to the tier target").
5. **`footprint_cells` is the actual length.** The report emits the real footprint
   size, which reach overflow can enlarge above the budget. Justification:
   `settlement-graph-generation::generated-footprints-are-connected-walkable-masks-centred-on-the-location`
   ("the budgeted cell count plus any water-reach cells").
6. **Crossing collision split.** A ford on the location cell collides with the
   plaza and is separated by the document's 1 m shift; road directions are then
   assigned from the emitted coordinates. Justification:
   `settlement-graph-generation::generated-graphs-satisfy-the-structure-rules-and-the-terrain-fit-lint`
   ("Its coordinates SHALL be unique"; "Directions stay near geometry").
