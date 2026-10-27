# Tasks

## 1. Closed implementation units

- [x] 1.1 Convert continent/classifier/region/site sources and all geographic locations with a temporary semantic comparison; remove duplicate Python authorities and document the D9 map-only exception.
- [x] 1.2 Compose immutable game lore/provider views from explicit loaded geography and untouched non-map lore, testing unbuilt locations without fabricated rooms or game imports in core.
- [x] 1.3 Migrate terrain, geographical search, scene-association and map/quest presenter consumers; exercise two reloads and bounded local lookup with synthetic worlds.
- [x] 1.4 Replace incidental Python-source/value pins with schema/identity/consumer evidence, update traceability/shards, remove temporary conversion tools, and run focused and contract checks.

## Workflow follow-up

- Archive remains the main agent's step; this branch only implements and verifies the slice.
- The new `map-geographic-sources` requirement ID does not exist until the archive sync, so its discoverable tests carry no `covers_requirement` annotation yet; attach the canonical ID after merge from `tools.spec_traceability list`. Existing canonical IDs keep their coverage, and no copied-data pin or waiver is introduced.
