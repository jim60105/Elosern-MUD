# blueprint-portrait-policy Tasks

## 1. Shared validation helper

- [ ] 1.1 Add `world/quests/characterization.py` with the shared bound helper validating
      `display_name`, paired `age`/`apparent_age`, and `portrait.stable_key` against a resolved
      race-lifespan upper bound: `type(value) is int` (booleans and `None` reject), missing-key
      vs `None` distinction, portrait must be a mapping with exactly one `stable_key` field, adult
      floor 18 as a named constant, bounded text/key rules
- [ ] 1.2 Add pure `unittest.TestCase` coverage: valid adult values; unpaired ages; `None`-valued
      key; `true`/`30.5` non-integers; underage (17); race-band overflow (human 120, elf 1300);
      malformed/empty/overlong/colon `stable_key`; portrait with extra keys; portrait not a
      mapping; empty/overlong `display_name`; absent-fields no-op

## 2. Blueprint shape, value object, and lifecycle (scenario director)

- [ ] 2.1 Add the frozen `BlueprintPortrait` value object (exactly one `stable_key` field) and
      extend `BlueprintNpcReq` with optional `display_name`, `age`, `apparent_age`, and
      `portrait`; verify the immutability guard (`_reject_mutable_containers`) passes for a
      frozen dataclass field
- [ ] 2.2 Wire the scenario director's blueprint validation to the shared helper (resolving the
      upper bound via `NPC_TIER_REGISTRY[tier].race_key` → `RACE_REGISTRY[race].lifespan`), with
      no inline duplicate of the rules
- [ ] 2.3 Extend the output jsonschema, `to_payload()`, and `from_payload()` to carry all four
      fields; add a round-trip test (`from_payload(to_payload(b))` preserves all fields) and a
      digest test (characterization differences yield different digest keys)
- [ ] 2.4 Add scenario-director validation tests: valid named occupant (human 68 / elf 300 via
      the new elven tier) passes; unpaired/`None`/boolean/fractional/underage/out-of-band/
      malformed-key/overlong-name/conflicting-duplicate-key entries reject and retry; field-less
      entries validate unchanged

## 3. Elven tier content

- [ ] 3.1 Add `NPCTier("elven_civilian", ...)` (elf / `elf_common`) to `world/lore/npc_tiers.py`,
      consistent with the existing registry test (referenced static tier belongs to the referenced
      race)
- [ ] 3.2 Add registry tests: the elven tier validates and its race resolves to the elf lifespan
      band

## 4. Compile boundary carry-through

- [ ] 4.1 Extend `StageSpawnRequirement` in `world/quests/compile.py` to carry the optional
      characterization fields in deterministic order (frozen value)
- [ ] 4.2 Wire `compile_quest_blueprint`'s `npc_req` parsing to the shared helper so malformed
      characterization rejects before registration or materialization; include the fields in the
      canonical digest serialization
- [ ] 4.3 Add compile tests: valid fields preserved; unpaired/underage/out-of-band/malformed
      reject; digest differs on characterization differences; field-less blueprint compiles
      byte-identical in shape to today's output

## 5. Template pool, anti-hallucination delta, and repository guards

- [ ] 5.1 Update `world/ai/director_templates.py` to support the optional fields on template
      `npc_reqs` entries, with a valid named example
- [ ] 5.2 Add a template registration test: malformed (underage) template rejected at
      registration; valid named template registers
- [ ] 5.3 Apply the `scene-builder` anti-hallucination narrowing (mechanical numbers only) and
      add a test that a validated characterization age never enters a stored trait and all stored
      stats still derive from the lore tables
- [ ] 5.4 Add a repository guard test asserting both validation layers (scenario director and
      compile) call the shared helper and no inline duplicate implementation exists

## 6. Verification

- [ ] 6.1 Run the affected Evennia test domains
      (`uv run --locked evennia test --settings settings.py world.quests.tests.test_compile
      world.ai.tests.test_scenario_director` and the characterization unit tests) and the
      repository-wide contract tests
- [ ] 6.2 Run `uv run --locked python -m tools.spec_traceability check` and confirm the new main
      requirements carry `covers_requirement` annotations
- [ ] 6.3 Run `openspec validate blueprint-portrait-policy --strict` and confirm the change is
      apply-ready
