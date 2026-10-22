# Tasks

## 1. Correct combat upkeep milestones

- [x] 1.1 Capture the milestone baseline before `tick_buffs` and compare after buff reactions, decay and climax settlement, verifying a committed upkeep reaction that crosses an onset or unlock threshold records that crossing once.
- [x] 1.2 Key upkeep evidence to the engagement, round and entity identity, verifying a later clock read records no duplicate milestone and later rounds do not reuse the first round's source.
- [x] 1.3 Add the facade event for the upkeep evidence repair and run the observability lint with the focused upkeep tests.

## 2. Record accepted item-use transitions

- [x] 2.1 Allocate an immutable accepted-operation identity in the deterministic item acceptance owner, verifying callers pass it into settlement and no identity is derived from item key or tick alone.
- [x] 2.2 Capture every affected recipient before the first item effect step and record only actual new adult milestones in that same transaction, verifying affected recipients gain evidence while an unaffected control and non-adult item use do not.
- [x] 2.3 Record combat item use under its combat slot identity, verifying two accepted operations in different slots retain distinct sources and join the correct encounter.
- [x] 2.4 Inject a failure after item evidence recording, verifying consumption, effects, counters, evidence and memory work roll back together.
- [x] 2.5 Document the accepted-operation identity contract and verify the documented callers match the migrated settlement surface.

## 3. Record defeat-aftermath adult evidence

- [x] 3.1 Allocate the attempt identity from engagement, aggressor, attempt ordinal and selected victim, verifying repeated attempts in one aftermath stay distinct and a later aftermath does not reuse an earlier identity.
- [x] 3.2 Compare pleasure and counters around the declared adult changes, recording the eligible adult action, its actual landed or resisted outcomes, and newly crossed victim-private milestones in the owning transaction, verifying the resistance verdict keeps its actual meaning.
- [x] 3.3 Verify no participation inference: an unselected pool member and an untouched ally receive no act, milestone or disclosure.
- [x] 3.4 Inject a failure after aftermath evidence recording, verifying aftermath undo, gameplay state, counters and evidence remain all-or-nothing.
- [x] 3.5 Verify committed upkeep, item and defeat settlement notifications replayed for the same operation reuse the original evidence without applying gameplay again.

## 4. Integration verification

- [x] 4.1 Run a real upkeep crossing, item acceptance and defeat aftermath through storage and selection, verifying each transition-time milestone is cited once by its own source and existing balance values are unchanged.
- [x] 4.2 Run the focused upkeep, item, defeat and narrative test labels plus `uv run --locked python -m tools.contract_gate`, verifying no ordinary item or upkeep nomination trigger was introduced.
