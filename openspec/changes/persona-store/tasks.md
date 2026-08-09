# persona-store — Tasks

## 1. PersonaStore handler

- [ ] 1.1 Create `world/rules/persona.py` with the `PersonaStore` class: constructor takes the
      entity, reads `entity.db.persona`, and exposes `get(field: str) -> Any | None` returning
      values verbatim (`None` for missing key / non-dict / missing record, never raising)
- [ ] 1.2 Implement `flatten(fields=("personality", "life_story", "habit")) -> str | None` with
      labeled sections in declared field order (性格：… / 人生經歷：… / 習慣：…), per-field caps,
      and a combined block cap following the `_cap_string` idiom; only non-empty string fields
      produce sections; `None` for missing/non-dict/no-section fields, never raising
- [ ] 1.3 Ensure the module has no write API and imports no state-mutating module (module
      docstring documents the read-only contract)

## 2. LivingEntity mount

- [ ] 2.1 Replace `typeclasses/entities.py`'s `persona: Any | None = AttributeProperty(default=None)`
      with a `lazy_property` returning `PersonaStore(self)`, mirroring the `relations` mount
- [ ] 2.2 Confirm `world/imports/loader.py` still writes `entity.db.persona` verbatim with no edits

## 3. Tests

- [ ] 3.1 Pure `unittest.TestCase` suite for `PersonaStore` in `world/rules/tests/`: `get()`
      verbatim/None contract, three-field flatten order and labels, absent-field omission,
      non-string field treated as absent, missing/non-dict/no-fields records → `None`, field and
      block cap truncation, no-write-surface and no-writer-import assertions
- [ ] 3.2 Update/extend `typeclasses` or `living-entity-hierarchy` integration tests: fresh entity
      exposes a `PersonaStore` mount; no-persona entity flattens to `None`
- [ ] 3.3 Update the `living-entity-hierarchy` "no PersonaStore class definition" test to the new
      working-handler contract (flip the seam)

## 4. Traceability and verification

- [ ] 4.1 Annotate the discoverable tests covering the new and modified requirements with
      `covers_requirement` using canonical IDs from
      `uv run --locked python -m tools.spec_traceability list`
- [ ] 4.2 Run `uv run --locked python -m tools.spec_traceability check` and confirm the
      persona-store and living-entity-hierarchy requirements are covered
- [ ] 4.3 Run the focused test packages (world rules tests plus the living-entity hierarchy tests)
      and confirm green
