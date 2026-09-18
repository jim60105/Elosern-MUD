## 1. Write semantics

- [ ] 1.1 Change `record_conferred_grant()` in `world/rules/skill_effects.py` to replace any existing
      grant with the same `(source_key, skill_key)` instead of appending, preserving grants from other
      sources and keeping the stored order deterministic.
- [ ] 1.2 Add `validate_source_owns_skill(actor, skill_key)` to the same module, raising
      `RejectedAction(EFFECT_RESOLUTION_FAILED)` when the key is absent from the actor's directly owned
      keys.
- [ ] 1.3 Tests: a repeated conferral from one source yields exactly one grant at the newest scale;
      two sources yield two grants; an unowned skill is rejected and writes nothing; a skill held only
      as a conferred grant cannot be conferred onward.

## 2. Derived set and data-driven scale

- [ ] 2.0 Admit a non-identity `EffectPolicy.coefficient` on the two conferral effect classes in
      `SkillDef._validate_effect_policies()` (`world/skills/registry.py`). Without this the validator
      raises at registry import for every conferral node AND for this change's own synthetic fixtures.
      Test: a synthetic skill declaring a conferral effect with a non-identity coefficient constructs,
      and a prefix outside the allow-list still raises.
- [ ] 2.1 Rewrite `_handle_confer_skill_partial` in `world/rules/action.py` to read the scale from the
      occurrence's `EffectPolicy.coefficient` and to stage one grant per directly-owned skill passing
      `validate_conferrable_skill`, rejecting with `EFFECT_RESOLUTION_FAILED` when the derived set is
      empty.
- [ ] 2.2 Rewrite `_handle_confer_growth_rate` to read its scale from the same per-occurrence policy.
- [ ] 2.3 Re-register both prefixes with an empty `requires_event_context`.
- [ ] 2.4 Tests: a cast with no conferral keys in `event_context` resolves and writes one grant per
      conferrable owned skill at the declared coefficient; a caster with nothing conferrable is
      rejected; a caller-supplied `confer_scale` is ignored.

## 3. Preview parity

- [ ] 3.1 Test: the shared action preview reports no missing-effect-context failure for a conferral
      skill on an owner with an empty `event_context`.
- [ ] 3.2 If the preview still rejects, fix `world/rules/action_preview.py` so it reads the same
      required-context table as the resolver.

## 4. Rollback face

- [ ] 4.1 Test: a resolution whose later pending effect fails restores `skill_grants` byte-equal,
      including the multi-grant derived-set case.

## 5. Behavior contract tests and docs

- [ ] 5.1 Put the new tests in `world/rules/tests/test_conferral_cast.py`, composed from synthetic
      skill definitions only — no shipped-content skill names, no data-contract tagging.
- [ ] 5.2 Annotate with `covers_requirement` using IDs from
      `uv run --locked python -m tools.spec_traceability list`.
- [ ] 5.3 Register the module in exactly one shard of `.github/evennia-shards.json`.
- [ ] 5.4 Confirm `docs/lore/skill-trees/divine-mystery.md` still matches the implemented contract —
      §2's `dominion_art` row, §6's balance bullet and §7 item 2 were amended when this change was
      authored to describe the derived set and the coefficient gate. Update them if implementation
      diverges.

## 6. Verification

- [ ] 6.1 Run the focused label
      `uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_conferral_cast`
      with `MUD_TEST_SETTINGS=1` passed through the tool's `env` input.
- [ ] 6.2 Run the focused existing labels covering the conferral read side and the action preview to
      prove neither changed behavior.
- [ ] 6.3 Run `uv run --locked python -m tools.spec_traceability check` and
      `uv run --locked evennia test --settings test_settings.py --keepdb tests.test_evennia_test_optimization_contract`.
- [ ] 6.4 `openspec validate conferral-grant-store --strict`.
