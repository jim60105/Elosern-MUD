## 1. Services V2 Projection

- [ ] 1.1 Depend on the merged `add-item-presentation-metadata` registry and add a frozen nullable presentation projection to `InventoryRowView`.
- [ ] 1.2 Build registered rows from immutable registry metadata and unknown-key rows with `presentation: null` without changing aggregation, equipment detection, ordering, ceilings, or persistent state.
- [ ] 1.3 Advance the services serializer and Python validation contract from schema version 1 to version 2 with strict exact-field, identifier, summary, and canonical-byte bounds.

## 2. Browser Contract Adoption

- [ ] 2.1 Update the dependency-free protocol validator, fixtures, and schema-version assertions to accept only services v2 inventory rows.
- [ ] 2.2 Update Vue store, transport, component fixtures, and stories to use valid registered and unknown-key presentation cases without adding visual behavior in this change.

## 3. Verification

- [ ] 3.1 Add focused Python tests for registered projection, null unknown-key projection, no-mutation behavior, strict validation, and a maximal legal services-v2 payload containing presentation metadata that remains below the 65,536-byte canonical JSON limit.
- [ ] 3.2 Add focused Node tests for services v2 acceptance and malformed, extra, unknown, and invalid presentation-field rejection.
- [ ] 3.3 Annotate substantive Python or JavaScript tests for the modified main requirement, run the focused Python and Node suites, and run `uv run --locked python -m tools.spec_traceability check`.
