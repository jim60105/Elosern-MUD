# Tasks

## 1. Snapshot settled locations

- [ ] 1.1 Add a bounded location reference (durable identity plus readable label) to each supported producer's settlement metadata using that source's actual location owner, verifying quest, examination, terminal combat, action and owner-local milestone evidence each retain their own location.
- [ ] 1.2 Keep an unknown location explicitly unknown, verifying a producer without an authoritative location records that state rather than inferring a live room at read time.
- [ ] 1.3 Update producer documentation and verify the documented metadata fields match what consumers read.

## 2. Carry location and objective context into rendering

- [ ] 2.1 Carry the location reference and occurrence tick through `AuthorizedDeedRecord`, grouping and serialization, verifying a compressed group spanning rooms keeps each occurrence's own time and location.
- [ ] 2.2 Preserve the completion objective snapshot without resolving mutable quest or room registries during selection, verifying a renamed or removed room still renders the committed snapshot and IDs.
- [ ] 2.3 Keep the existing group and JSON budgets authoritative, verifying added context drops only whole groups and every retained fact keeps its source IDs and outcome.
- [ ] 2.4 Extend the selection tests for differing-location compression and budget-driven group removal, replacing any assertion that only checks key presence.

## 3. Freeze the admitted tick

- [ ] 3.1 Carry the selector's frozen tick into the detached nomination context and use it for admission, selection and failure diagnostics, verifying a nonzero-tick run never logs zero.
- [ ] 3.2 Reuse the admitted tick after model response and persistence rather than reading a later clock, verifying a nomination admitted while time advances still reports its original window.
- [ ] 3.3 Verify a clock read failure ends the read workflow without a ballot, cooldown or gameplay change.

## 4. Integration verification

- [ ] 4.1 Run a real settlement with distinct locations through committed selection into rendered JSON, verifying facts, sources and frozen tick agree and no private prose appears in diagnostics.
- [ ] 4.2 Run the focused selection, service and producer test labels plus `uv run --locked python -m tools.contract_gate`, verifying the 48-hour, eight-group and code-point limits are unchanged.
