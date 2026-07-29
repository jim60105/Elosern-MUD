## 1. Package layout and new dependency

- [ ] 1.1 Confirm `world/imports/` exists as an empty stub package from change 1; add
      `world/imports/tests/__init__.py` and `world/imports/examples/`.
- [ ] 1.2 Add and pin the `jsonschema` package to the project's dependency file (per design.md D-2),
      verifying the installed version supports draft 2020-12 `$schema` documents.
- [ ] 1.3 Create `world/imports/schema.py`, `world/imports/validate.py`, `world/imports/loader.py`,
      and `world/lore/sexual_vocab.py` as empty modules with module docstrings referencing design
      doc §5.3 and this change (per design.md D-6 for `sexual_vocab.py` specifically).

## 2. Sexual vocabulary (`world/lore/sexual_vocab.py`)

- [ ] 2.1 Define the six ordered tuples per design.md D-6: `AROUSAL_LEVELS`, `WETNESS_LEVELS`,
      `SHAME_LEVELS`, `EXPOSURE_LEVELS`, `CLIMAX_PHASE_LEVELS`, `SENSITIVITY_LEVELS`, transcribed
      exactly from design doc §6.4. No behavior, no imports from `world.rules` or `world.imports`.
- [ ] 2.2 Write the module docstring naming `CHARACTER_SCHEMA_V1` as the current consumer and
      stating that a future `sexual-state` change (change 7) is expected to import these same
      tuples rather than redefine the ladder.
- [ ] 2.3 Add a re-export of these six tuples to `world/lore/__init__.py` (a one-line addition to
      that file, per proposal.md's Impact section — not a redesign of change 2's scope).

## 3. Character and world schemas (`world/imports/schema.py`)

- [ ] 3.1 Define `CHARACTER_SCHEMA_V1` as a JSON Schema (draft 2020-12) dict per design.md D-1/D-3/
      D-4: `required` includes `schema_version`, `key`, `display_name`, `age`, `apparent_age`,
      `race`, `stats`, `disguised_stats`, `skills`, `passives`, `equipment`, `inventory`,
      `sexual_baseline`, `persona`; `subrace` is present in `properties` but not `required`.
- [ ] 3.2 Set `age` and `apparent_age` to `{"type": "integer", "minimum": 18, "description": ...}`
      per design.md D-3, with the description stating the hard-gate, never-a-warning nature of the
      check in language readable without the design doc.
- [ ] 3.3 Set `stats` per design.md D-4: `type: object`, `additionalProperties: false`, exactly the
      eight keys `hp`/`mp`/`sp`/`atk_phys`/`agility`/`defense`/`magic_level`/`guild_merit` (each a
      non-negative integer, `hp` strictly positive), and a `description` stating the base-value,
      pre-skill-multiplier convention loudly and self-containedly (quote the `88*1000` example
      directly in the description text).
- [ ] 3.4 Set `disguised_stats` to `{"type": "object", "additionalProperties": {"type":
      "integer"}}` per design.md D-8 — no key constraint at the schema layer; the subset check is
      semantic-layer (task 4.3).
- [ ] 3.5 Set `persona` to `{"type": "object", "description": ...}` per design.md's Non-Negotiable
      Rule 4 and the `import-schema` capability — no required keys, no `additionalProperties:
      false`, no nested constraints. The description states persona is opaque and never inspected
      beyond confirming it is an object.
- [ ] 3.6 Set `sexual_baseline` per design.md D-6/D-7: `type: object`, `required: ["arousal",
      "virgin", "sensitivity"]`, `additionalProperties: false`; `arousal` constrained to
      `sexual_vocab.AROUSAL_LEVELS` (as an `enum`), `wetness`/`shame`/`exposure`/`climax_phase`
      each optional and constrained to their respective vocab tuples when present, `sensitivity`
      typed as `{"type": "object", "additionalProperties": {"enum": list(sexual_vocab
      .SENSITIVITY_LEVELS)}}` (free-form keys, constrained values), `virgin` typed `boolean`.
      Import the six tuples from `world.lore.sexual_vocab` (task 2.1) rather than re-typing the
      Chinese strings a second time.
- [ ] 3.7 Define `WORLD_SCHEMA_V1` per design.md D-14: `required: ["schema_version", "key",
      "content"]`, `content` a non-empty string with the opaque/narrative-only description quoted
      in D-14, `tags` an optional array of strings, `additionalProperties: false`.

## 4. Semantic validation layer (`world/imports/validate.py`)

- [ ] 4.1 Implement `classify_record(raw: dict) -> Literal["character", "world_entry"]` per
      design.md D-1: dispatch on presence of `age` vs `content`; raise a clear error naming the
      record's `key` (or `<unknown>`) if neither is present.
- [ ] 4.2 Implement structural validation: run `jsonschema.validate()` against `CHARACTER_SCHEMA_V1`
      or `WORLD_SCHEMA_V1` per the classification, translating `jsonschema.ValidationError` into
      this module's `Issue` type (field path, message) so reject-report formatting is consistent
      across both the structural and semantic passes.
- [ ] 4.3 Implement `_check_disguised_stats_subset(record) -> list[Issue]` per design.md D-8:
      reject (return as a rejection-class `Issue`) every `disguised_stats` key not present in
      `stats`, naming each offending key.
- [ ] 4.4 Implement `_check_race_subrace(record) -> list[Issue]` per design.md D-10: reject if
      `race` is not a `RACE_REGISTRY` key; reject if `subrace` is present and either not a
      `SUBRACE_REGISTRY` key or its `race_key` does not equal the record's `race`. Import
      `RACE_REGISTRY`/`SUBRACE_REGISTRY` from `world.lore.races`.
- [ ] 4.5 Implement `_check_stats_band(record) -> list[Issue]` per design.md D-9: compare each
      present `stats` key against `RACE_REGISTRY[race].vital_baseline`/`static_baseline`/
      `magic_cap`, adjusted for `Subrace.vital_overrides` when a subrace with an override is
      present (replace, not blend — same rule as change 3 D-5); every out-of-band value produces a
      warning-class `Issue`, never a rejection-class one. No literal band number written in this
      function — every bound is a direct registry read.
- [ ] 4.6 Implement `_resolve_skill_registry() -> Mapping[str, Any] | None` and
      `_check_skills(record) -> tuple[list[Issue], list[Issue]]` per design.md D-5: attempt `from
      world.skills.registry import SKILL_REGISTRY` inside a `try/except ImportError`, returning
      `None` on failure. For every key in `skills` + `passives`: if the registry is `None`, emit a
      warning-class `Issue` stating the registry is unavailable; if not `None` and the key is
      absent from it, emit a rejection-class `Issue`; if present, emit nothing. Document the
      forward-declared module path (`world.skills.registry.SKILL_REGISTRY`) directly in this
      function's docstring.
- [ ] 4.7 Implement `_check_world_entry_key_uniqueness(records) -> list[Issue]` (batch-level, world
      schema only): reject on duplicate `key` values across a batch of world-info records.
- [ ] 4.8 Implement `validate_character(record: dict) -> RecordReport` and `validate_world_entry
      (record: dict) -> RecordReport` composing tasks 4.2–4.6/4.7 respectively into one
      `RecordReport` (record key, list of rejection `Issue`s, list of warning `Issue`s, `is_valid`
      property).
- [ ] 4.9 Implement `validate_batch(paths: list[Path]) -> BatchReport` per design.md D-11: reads
      and classifies every file (task 4.1), dispatches to `validate_character`/`validate_world_entry`
      (task 4.8) plus the batch-level uniqueness check (task 4.7), and aggregates into a
      `BatchReport` with an `all_valid` property (true only if zero rejections across every record)
      and a way to retrieve the validated character records for `loader.py`'s use.
- [ ] 4.10 Implement the `python -m world.imports.validate <files...>` CLI entry point: reads file
      arguments (glob-expanded by the shell before this process sees them), calls `validate_batch`,
      prints a per-record, per-issue report (record key or path, field, reason, reject/warning
      marker), and exits 0 if `all_valid` else a non-zero status.

## 5. Loader (`world/imports/loader.py`)

- [ ] 5.1 Implement `_resolve_trait_values(record: dict) -> dict[str, int]` per design.md D-12:
      starts from `world.rules.traits.race_floor(RACE_REGISTRY[record["race"]])` (reused from
      change 3, not reimplemented), then `.update(record["stats"])` so every literal imported value
      wins over the floor.
- [ ] 5.2 Implement `instantiate_character(record: dict, typeclass: type = NPC) -> LivingEntity` per
      design.md D-12/D-13: constructs `typeclass`, sets `entity.race`/`entity.subrace`, populates
      `entity.traits` from task 5.1's values via `TraitHandler` (matching the same
      `initial_trait_config`-style kwargs shape change 3's `world/rules/traits.py` already uses —
      reuse that helper if its signature accepts literal values, or call `TraitHandler.add()`
      directly with the same keyword shape), sets `entity.db.disguised_stats`, `entity.persona`,
      `entity.sexual`, `entity.skills` (`{"active": ..., "passive": ...}`), `entity.equipment`, and
      `entity.db.inventory` verbatim from the validated record. Default `typeclass` is `NPC`; no
      Account/session binding performed for `PlayerCharacter`.
- [ ] 5.3 Implement `load_batch(paths: list[Path], typeclass: type = NPC) -> list[LivingEntity]` per
      design.md D-11: calls `world.imports.validate.validate_batch()`; if `not report.all_valid`,
      raises `ImportRejected(report)` without constructing anything; otherwise calls
      `instantiate_character` (task 5.2) once per validated character record and returns the list.
      World-info records in the same batch do not produce entities.
- [ ] 5.4 Define `ImportRejected(Exception)` carrying the full `BatchReport` so a caller can render
      the same per-record/per-field detail the CLI does without re-running validation.

## 6. Reference example (`world/imports/examples/`)

- [ ] 6.1 Author `world/imports/examples/example_character.json` per design.md D-15: an elf,
      `subrace: "ciaran"`, `age`/`apparent_age` both comfortably above 18 (e.g. 22, not exactly 18),
      all eight `stats` keys set with `atk_phys`/`agility`/`defense` inside the elf `static_baseline`
      band (70-95) and `hp`/`mp`/`sp` at or near the elf `vital_baseline` (10000), a non-empty
      `disguised_stats` that is a proper subset of `stats`' keys, non-empty `skills` and `passives`
      arrays, `equipment`/`inventory` present (may be empty per the design doc's own example),
      `sexual_baseline` with `arousal`/`virgin`/`sensitivity` plus at least one of `wetness`/
      `shame`/`exposure`/`climax_phase` set, all values drawn from `world.lore.sexual_vocab`, and a
      non-trivial `persona` object with multiple top-level keys (`identity`, `personality`,
      `life_story`, `habit`, `appearance`, `social_connection`, per design doc §5.2's `PersonaStore`
      description), populated with placeholder-but-non-empty content.
- [ ] 6.2 Confirm by hand that `example_character.json`'s `stats.atk_phys`/`agility`/`defense` are
      base values, not skill-multiplied ones — cross-check against
      `RACE_REGISTRY["elf"].static_baseline` before finalizing the file.

## 7. Tests

- [ ] 7.1 `world/imports/tests/test_age_gate.py` — **permanent, non-removable per design doc §10**:
      an age-17 record (otherwise identical to the reference example) is rejected;
      an apparent_age-17-with-age-22 record is rejected independently; a record with both fields at
      exactly 18 passes the age check; a record omitting either field is rejected. Mark this test
      module's docstring explicitly as a permanent regression guard that must never be deleted or
      loosened.
- [ ] 7.2 `world/imports/tests/test_schema.py` — structural validation for every property in
      `CHARACTER_SCHEMA_V1`/`WORLD_SCHEMA_V1` per the `import-schema` capability: stats
      `additionalProperties: false` and non-negative constraint; disguised_stats integer-value
      constraint with no key constraint at schema layer; persona accepts arbitrary object shapes
      and rejects non-objects; sexual_baseline required-field and vocabulary-enum enforcement for
      all six fields; world entry required-field enforcement. Assert the `age`, `apparent_age`, and
      `stats` `description` strings contain the documented invariant language (tasks 3.2/3.3).
- [ ] 7.3 `world/imports/tests/test_validation_semantics.py` — per the `import-validation`
      capability: race/subrace existence and cross-reference (task 4.4); disguised_stats subset
      check (task 4.3); stats-band warning behavior including the `foxkin` vital-override case
      (task 4.5); sexual_baseline shape violations reported as rejections, not warnings (design.md
      D-7); the pluggable skill-registry check in both its degraded (module absent, warning) and
      promoted (module present via mock, reject-on-unknown-key) states (task 4.6) — this is the
      test that proves design.md D-5's self-upgrading behavior actually works, not just one branch
      of it.
- [ ] 7.4 `world/imports/tests/test_batch_all_or_nothing.py` — per the `import-validation` and
      `import-loader` capabilities: a batch with one rejecting file among otherwise-valid files
      fails the whole batch (CLI exit code non-zero, report lists all files); `load_batch()`
      constructs zero entities for such a batch and raises `ImportRejected` carrying the full
      report; a fully valid batch produces one entity per character record and zero for world-info
      records in the same batch.
- [ ] 7.5 `world/imports/tests/test_loader_trait_values.py` — per the `import-loader` capability:
      literal imported stat values land in `entity.traits` verbatim; an omitted stat key falls back
      to `race_floor()`'s value; every loaded trait value stays within the constructing race's
      documented band (catching an accidentally-baked-in skill multiplier the same way change 3's
      own regression test does); `entity.persona`/`entity.sexual`/`entity.skills`/`entity.equipment`
      /`entity.db.disguised_stats`/`entity.db.inventory` are all stored verbatim with no
      interpretation; `instantiate_character()` defaults to `NPC` and accepts `typeclass=
      PlayerCharacter` with no Account/session side effects.
- [ ] 7.6 `world/lore/tests/test_sexual_vocab.py` — the six tuples match design doc §6.4 exactly, in
      order (per the `sexual-vocabulary` capability); the module imports nothing from `world.rules`
      or `world.imports`.
- [ ] 7.7 `world/imports/tests/test_reference_example.py` — **permanent**: loads
      `examples/example_character.json` and asserts zero rejections and zero warnings against the
      current schema and lore registries (per the `import-reference-example` capability); asserts
      the example sets a subrace, all eight stats keys, a non-empty disguised_stats subset,
      non-empty skills/passives, a sexual_baseline with an optional field beyond the required three,
      and a multi-key persona.

## 8. Verification

- [ ] 8.1 Run the full `world/imports/tests/` and `world/lore/tests/test_sexual_vocab.py` suites and
      confirm all tests pass.
- [ ] 8.2 Run `python -m world.imports.validate world/imports/examples/example_character.json` from
      a shell and confirm it exits 0 with a clean report, matching what task 7.7 asserts
      programmatically.
- [ ] 8.3 Run `openspec validate import-contract --strict` and confirm it passes.
- [ ] 8.4 Confirm no function in `world/imports/loader.py` multiplies a stored trait value by 10,
      100, or 1000 (grep by hand as a spot check, mirroring change 3's task 7.5 discipline).
- [ ] 8.5 Confirm `world/imports/schema.py` contains no hardcoded race-band or magic-cap number —
      every band used by the semantic layer (task 4.5) is a direct `RACE_REGISTRY`/`Subrace` read,
      never a literal copied from `world_info.md` or the design doc.
