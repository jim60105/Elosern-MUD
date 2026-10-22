# Tasks

## 1. Share one authorized adult projection

- [ ] 1.1 Extract the recipient-parameterized adult field projection from `world/narrative/recent_deeds.py` into a pure narrative-owned helper with an allowlisted detached shape, verifying `recent_deeds` behavior is unchanged for the player's own authorized facts.
- [ ] 1.2 Replace the generic adult branch in `world/narrative/memory.py` with that helper, verifying public actor, participant and third-living-bystander memories contain only knowable fields and no private milestone or counter.
- [ ] 1.3 Keep private event projection skipped and private-authoring exclusions intact, verifying existing memory visibility behavior for non-adult and private sources is unchanged.
- [ ] 1.4 Derive any readable memory summary only from authorized fields, verifying no raw compliance reasoning, roll or other participant's private history appears in the stored summary.
- [ ] 1.5 Document the per-recipient adult knowledge boundary shared by nomination and memory, verifying the document names both consumers and the event-visibility distinction.

## 2. Preserve transaction and replay boundaries

- [ ] 2.1 Keep per-owner memory creation and projection progress atomic and restart-safe, verifying a retried or resumed projection creates one memory per authorized owner with no newly authorized private fields.
- [ ] 2.2 Make an unsupported or malformed adult payload fail closed with a bounded diagnostic, verifying no raw-content memory is created and the existing failure path leaves gameplay untouched.
- [ ] 2.3 Inject a failure after memory creation in the projection workflow, verifying the memory, progress and evidence work roll back without partially authorized content.
- [ ] 2.4 Run the observability lint with the focused memory and selector tests, verifying the new failure and projection events carry identifiers without private prose.

## 3. Integration verification

- [ ] 3.1 Verify the player's own private adult experience still reaches nomination through its authorized path while the same occurrence's memory projection omits fields belonging to another participant.
- [ ] 3.2 Verify nomination selection and memory projection read the same source record without either consumer importing the AI proposer or writing gameplay state.
- [ ] 3.3 Run the focused narrative-memory and title test labels plus `uv run --locked python -m tools.contract_gate`, verifying no unrelated narrative consumer changed behavior.
