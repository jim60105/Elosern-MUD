# Tasks

Read design.md and the named dependency shared contracts first. All boxes are future implementation tasks; this proposal implements nothing. Each unit includes its own tests/documentation and is bounded to 45-120 minutes.

## 1. Frozen scene contract

- [x] 1.1 Implement Speech/Narration/Scene and strict IDs, Unicode/codepoint and canonical UTF-8 Scene/bundle bounds, plain-data serialization; add synthetic roundtrip/rejection tests and document reuse in the module docstring. Verify frozen mutation raises and narration cannot carry a speaker.

## 2. Topic and condition declarations

- [x] 2.1 Add exact Shared contract v2 frozen union, constructors, primitive parser/schema fragment, pure validator and canonical/package reference catalog interfaces. Test static/generated codecs, maximal Unicode/delimiter collisions, duplicate IDs, actor opening, priorities, fallback, DAG and effect-free chains; document exact provider-independent schema.

## 3. Focused model acceptance

- [x] 3.1 Register new Python test module in .github/evennia-shards.json and data-independent traceability ownership; run focused model tests and contract_gate. Keep existing live KeywordResponse rows untouched until runtime cutover; no fake runtime evaluator or new empty subsystem.

