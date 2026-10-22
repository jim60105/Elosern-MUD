# Tasks

Estimated effort: 6.5 hours for the implementing worker, including every required verification step below. Follow design.md verification commands and scope; check a box only after its assertions and evidence are verified.

## 1. Exact protocol cutover (2 hours)

- [ ] 1.1 Extend builder node output and normalization on both validators with required exact gateway/null semantics, matching existing 256-code-point limits and schema_version 1; preserve deduplication metadata.
- [ ] 1.2 Populate registered current/in-view grid gate rooms and wilderness-adjacent grid gate targets through existing gateway helpers; ordinary and coordinate-free nodes carry null.

## 2. Fixtures and focused behavior evidence (2 hours)

- [ ] 2.1 Migrate all affected local-map payload factories/inline fixtures across Python, Node, Vue, Storybook and browser tests in the same change, with no validator fallback for missing fields.
- [ ] 2.2 Add matching gateway ordinary/gate/interior assertions and malformed-field cases to existing test_schema/test_grid_gateways/test_wilderness modules; retain size-limit rejection assertions and model pass-through checks.

## 3. Required verification and handoff (2.5 hours)

- [ ] 3.1 Run the smallest affected schema/presenter Python method/class labels using the documented Evennia env-file command, then the separate protocol_local_map.test.js and local_map.test.js Node files. Do not run their parent packages.
- [ ] 3.2 Use agent-browser to capture and inspect the existing World/LocalMap gate/action and instance/interior stories after fixture cutover; record screenshot paths and unchanged layout/action results.
- [ ] 3.3 Obtain canonical IDs through tools.spec_traceability list, annotate matching discoverable tests/evidence methods, confirm unchanged or update exact shard ownership under the rules in design.md, run traceability check and tools.contract_gate, and run openspec validate add-local-map-gateway-metadata --strict. Update touched protocol comments/story docs and the implementation handoff.

