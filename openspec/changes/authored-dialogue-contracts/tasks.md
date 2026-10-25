# Tasks

Read design.md and the named dependency shared contracts first. All boxes are future implementation tasks; this proposal implements nothing. Each unit includes its own tests/documentation and is bounded to 45-120 minutes.

## 1. Frozen scene contract

- [ ] 1.1 Implement Speech/Narration/Scene and strict IDs, Unicode/codepoint bounds, plain-data serialization; add synthetic roundtrip/rejection tests and document reuse in the module docstring. Verify frozen mutation raises and narration cannot carry a speaker.

## 2. Topic and condition declarations

- [ ] 2.1 Add the exact frozen union and AuthoredTopic/AuthoredDialogue/SceneVariant constructors from Shared contract v1; validate uniqueness, complete actor opening, priority, fallback and predecessor DAG. Tests cover duplicate IDs, ties, dangling/cyclic predecessors and illegal pure-chain eligibility/effects.

## 3. Focused model acceptance

- [ ] 3.1 Register new Python test module in .github/evennia-shards.json and data-independent traceability ownership; run focused model tests and contract_gate. Keep existing live KeywordResponse rows untouched until runtime cutover; no fake runtime evaluator or new empty subsystem.

