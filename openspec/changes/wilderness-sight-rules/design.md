# Design

## Context

Observed owners and nearby test targets: world/maps/wilderness_provider.py terrain delegation; new world/rules/sight.py and rulebook/sight.yaml; schema.py/documents.py DistrictDeclaration; map_district_lighting.py exact landmark membership; new world/rules/tests/test_sight.py and existing authoring tests.

## Goals / Non-Goals

Calculate ground sight and transient distant sightings from validated policy. Keep the named slice complete and independently runnable after prerequisites; dependent behavior is owned elsewhere.

## Decisions

Pure functions light_phase(calendar), ground_radius(cell,calendar,inputs), in_ground_disc(observer,target,radius), distant_markers(observer,calendar,sources,lit_districts) use immutable inputs. sight.yaml owns hours/radii/factors, separate from clock.yaml anchor hours. Initial policy is detailed design §3: day07-17, dusk17-19, night19-05, dawn05-07, boundaries inclusive at phase start. Terrain rows day/twilight/night: open/coast4/3/1, hills3/2/1, mountain2/2/1, woodland/deep forest1/1/0. Tier bonuses0=0/0/0,1=1/0/0,2=2/1/0,3=3/2/0; vantage8/5/2. Validate coverage, finite nonnegative factors and radius<=8; tests inject a policy rather than pin shipped values.

Radius=max(terrain+prominence,vantage or0); canopy forces tier0 before addition but vantage remains eligible. Disc uses dx²+dy²<=(r+0.5)², radius0 only origin; no occlusion or mountain-pass logic. Bands are rendering only. Add optional district fields vantage:boolean(default false), sight_km/light_km:finite nonnegative numbers and silhouette_zh:nonblank<=256 codepoints. Positive sight/light requires silhouette. Preserve optional fields through parser/frozen published district/editor save, without adding shipped values. No distant marker for a landmark with no authored range.

Non-hidden settlements derive source position from existing location identity and footprint size sqrt(occupied cell count), multiplied by sight.yaml day/night footprint factors. Twilight uses its factor on daytime range. Hidden/elven villages never become distant sources. If a district landmark references that same location, merge one source identity, not duplicate markers. Landmarks elsewhere have stable internal district/source identity. Source cell must be outside ground sight and distance<=current range. Observer canopy hides all distant markers. At night use light_km only; elevation never changes distant range.

Internal source_key is comparison-only. Wire marker is exactly {bearing,distance_km,silhouette_zh,name}, bearing one of16 north-clockwise zh-TW labels, half-sector ties clockwise, distance nearest5km with ties upward (zero allowed), name nullable and present only when containing district is lit. No source cell, target ID or district key in wire marker. Reads recompute and write nothing; seeing never lights districts. Initial unspecified twilight/footprint factors are authored balance policy chosen in sight.yaml, documented once, not duplicated approval tests. Human review of silhouette wording uses approved design §6. Update existing authoring/rulebook guidance.

## Dependency contracts

- [wilderness-elevation-runtime](../wilderness-elevation-runtime/design.md) must land first.

## Planning and implementation boundaries

This artifact set covers sub-project1 only. Read the [blueprint](../../../docs/superpowers/specs/2026-10-30-wilderness-travel-mode-blueprint-design.md) §7.1, the [detailed sight design](../../../docs/superpowers/specs/2026-10-30-wilderness-sight-and-fog-reveal-design.md) and [engine architecture](../../../docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md) §§2/3/6.5/10. Preserve single-writer ownership and server exploration mode. No travel HUD/input queue/log/tint, camping/dream/art changes, authored geography/landmark-content changes, new roads, migrations or compatibility paths. Generated elevation and the approved sight rulebook are explicitly allowed.

Implementation will be performed by gpt-luna-level workers. Follow the named owners and exact contracts; read each prerequisite design first. Do not invent downstream stubs or leave unresolved behavior to a worker. Each change is capped at one workday including focused evidence/docs. Independent roots can run concurrently only with one owner integrating shared test-manifest/doc edits.

## Evidence and requirement shape

Use synthetic documents, policies and parties with independent expected results. Do not pin shipped data, text, markup or counts. Appearance/wording judgments are human-reviewed against the approved detailed design, outside SHALL requirements. For each requirement implement a discoverable test named from its mechanism, covering every delta scenario and both raising/non-raising cases. Test paths are named in Context. New package-local server tests join exactly one shard in .github/evennia-shards.json; avoid new modules when an existing test file is sufficient.

Requirement IDs must come from tools.spec_traceability list on the equivalent merged spec tree, never hand-composed. Before sync associate only the nearest current canonical requirement and report the temporary mapping per docs/development/spec-test-traceability.md. Sync remounts to the generated IDs with no uncovered requirements or waiver. Modified requirements retain identity except an explicit RENAMED window title. Mechanism tests must exist before that sync.

## Risks / Trade-offs

[Read side effects] -> Pure projections and object/Attribute/clock snapshots in integration tests. [Shared files] -> Serialize shard-manifest, schema and documentation changes even when roots are independent. [Data echo tests] -> Assert mechanics on synthetic fixtures and treat visual review separately. No new permanent lighting or walking state is allowed.

## Rollout / Rollback

Apply only after dependencies land. Development database reset is needed for the schema2 cutover; never automate deleting the user's database. No migration or dual decoder is added. Rollback is source reversal and a deliberate development reset where applicable. This proposal task does not start apply, sync or archive.
