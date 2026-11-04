# Design

## Context

See `proposal.md` for motivation and the supplied baseline failure evidence. Inspection is against `master` at `11de2a59ba4a549ad0c3bf5611b08001dba3b497`.

`world/rules/combat_identity.py:stable_actor_id(entity: Any) -> str` gives a positive integer `pk` precedence and returns `dbref:<pk>`. Only an actor without a pk uses explicit `combat_identity` and returns `fixture:<identity>`. Adding `combat_identity` to an existing positive-pk double cannot change its domain. `Battlefield.__post_init__` requires exactly two teams, unique team membership, matching roster membership, and canonical roster keys. Keep this production code unchanged.

### Construction inventory

Line numbers describe the inspected baseline, not future patch positions.

| Site | Actual participants | Defect and required repair |
| --- | --- | --- |
| `ConditionalDamageMechanicsTests._resolve_cast`, lines 460-463 | `self.actor` and `self.target`, created with `create_object(PlayerCharacter, ...)` in `setUp` | Real persisted characters, not monsters. `fixture:cond_actor` and `fixture:cond_target` conflict with dbref identities. Use the local factory below. This helper serves ten failing test methods. |
| `test_conditional_damage_preserves_nonlethal_outcome`, lines 722-725 | Same persisted characters | Same domain error; use the same factory, retaining `nonlethal=True`, success assertion and HP floor 1. |
| `test_transaction_rollback_restores_hp_on_late_failure`, lines 825-828 | Same persisted characters | Same domain error; use the factory, retaining the late `_commit` fault and unchanged-HP assertion. |
| `SkipSafetyTests.test_active_battlefield_rejects_but_fled_actor_does_not`, lines 35-38 | `actor("first", 1)` and `actor("second", 2)` | SimpleNamespace doubles deliberately model persisted actors. Derive dbref keys for both teams and roster. Line 41 also writes the label `"first"` to `fled`; replace it with `stable_actor_id(first)`. |
| `test_same_key_entities_in_separate_battlefields_do_not_cross_evict`, `field_a`, lines 64-67 | Same-label actor pk 1, opponent pk 3 | Derive both keys from the actual participants. Retain registry assertions in decimal-string pk domain. |
| Same test, `field_b`, lines 68-71 | Same-label actor pk 2, opponent pk 4 | Derive distinct keys; never reuse `fixture:shared` for pk 1 and pk 2. |
| `test_in_combat_lookup_resolves_by_actor_dbref`, lines 85-88 | Fighter pk 10, opponent pk 12 | Derive both keys; preserve same-label clone pk 13 exclusion and bystander setup. |

The ten shared-helper consumers are `test_two_facts_match_once_not_squared`, `test_bypass_and_bonus_are_independent`, `test_percent_rider_requires_a_hit`, `test_dynamic_buff_predicate_matches_while_live`, `test_dynamic_buff_predicate_composes_any_match_once`, `test_unconditional_defense_bypass_bypasses_for_all_targets`, `test_unconditional_rider_applies_even_when_predicate_does_not_match`, `test_high_defense_clamped_to_floor_without_bypass_and_full_with_bypass`, `test_second_synthetic_non_light_configuration`, and `test_unconditional_execution_bypass_ignores_defense`. The freeform-scaling test uses the damage handler directly and needs no identity repair.

### Production boundary

The failing calls are direct test constructors. `world/rules/combat_session/battlefield.py:reconstruct_battlefield` already resolves distinct participant dbrefs, computes `identity = stable_actor_id(entity)`, builds teams from `key_by_pk`, and constructs the canonical `Battlefield`. `world/rules/skip_safety.py` consumes an existing battlefield; it does not construct another one. Its `_BATTLEFIELDS` keys intentionally remain `str(entity.pk)`, while roster/team/fled keys use `dbref:`. No production call on these failing paths requires a fix.

## Goals / Non-Goals

Restore the original assertions and add executable identity controls in the same two modules. No production edits, shared `combat_fixtures.py` edits, identity-contract refactor, registry-key redesign, runtime migration, shipped-data assertion, or regional-population edit belongs to this change.

## Decisions

### Local construction, canonical keys

Import `stable_actor_id` from `world.rules.combat_identity` in both modules. In `ConditionalDamageMechanicsTests`, add this exact private interface and route all three construction sites through it:

```python
def _make_battlefield(self) -> Battlefield:
    actor_id = stable_actor_id(self.actor)
    target_id = stable_actor_id(self.target)
    return Battlefield(
        {"party": frozenset({actor_id}), "foes": frozenset({target_id})},
        {actor_id: self.actor, target_id: self.target},
    )
```

This is a file-local fixture construction point, not a second runtime path. `_resolve_cast(self, skill_key: str, roll: int = 60, scale: float = 1.0)` retains its signature and behavior. The nonlethal and rollback tests retain their distinct action contexts and fault behavior.

In skip-safety tests, keep `actor(key, pk, hp=10, contents=())` unchanged. Bind each inline opponent to a local variable, derive a local ID for every participant, and use those IDs for team members and roster keys in the existing four calls. Keep explicit distinct pks. Do not strip pks or assign `combat_identity` to hide this mismatch.

### Discoverable regression controls

Add `ConditionalDamageMechanicsTests.test_battlefield_construction_uses_persisted_identity`. Give both real characters the same synthetic display key, construct through `_make_battlefield`, and assert each ID independently equals `f"dbref:{entity.pk}"`, the IDs differ, the roster maps each to the original object, and team membership is correct. Rename one character and assert its ID and context presence/team remain unchanged. Construct a deliberately invalid field with matching teams/roster using `fixture:` labels for these persisted objects; assert `ValueError` with `does not match combatant identity`. Also reject placing one canonical ID in both teams. No production validator patching is permitted.

Add `SkipSafetyTests.test_battlefield_construction_preserves_explicit_identity_domains`. Use two same-label `actor` doubles with distinct positive pks, also supplying distinct explicit `combat_identity` attributes. Assert their independently expected dbref IDs, canonical roster lookup and distinct teams. Assert the same fixture-key mismatch raises `ValueError` before registration, and `_BATTLEFIELDS` is unchanged. In a separate subcase use two `SimpleNamespace` pure doubles without pks and with explicit distinct `combat_identity` values; assert expected `fixture:` IDs and successful ordinary `Battlefield` construction despite the shared label. Reject duplicate team membership. Keep `BattlefieldIsolation` cleanup.

The migrated active/fled test must observe `IN_COMBAT`, then `None` after adding the canonical ID to `fled`. The existing separate-field test must retain successful unregister of pk 1 without evicting pk 2. These controls detect both the fixture drift and a reintroduced label fallback through actual construction and state transitions; no text-pinning test is needed.

### Requirement shape and traceability

Modify only `BattlefieldActionContext conforms to change 8's ActionContext protocol`. Keep its heading and canonical ID unchanged and its SHALL body below 500 characters. Scenarios describe identity rules; do not introduce a test-module-health requirement or a requirement that pins source text or shipped data. This fix adds no production behavior and adds zero new requirements.

Obtain the existing ID with `uv run --locked python -m tools.spec_traceability list --json-output <scratch-path>`; the current canonical ID is `battlefield-action-context::battlefieldactioncontext-conforms-to-change-8-s-actioncontext-protocol`. Decorate both new discoverable tests with this literal ID using `covers_requirement`. Their construction, identity-domain and rejection assertions support that claim. Preserve all existing damage and skip-safety decorators. Because the modified requirement retains its identity, no guessed IDs, temporary aliases or post-sync remapping are needed. Run local `check`; complete evidence verification remains CI-owned.

### Acceptance commands and evidence ownership

Run from the repository root after implementation. Create a scratch environment file outside the checkout containing exactly `MUD_TEST_SETTINGS=1`; substitute its absolute path for `<test-env>`. Use single-token `--env-file=<test-env>`, never an inline environment prefix. Do not run CI shard commands locally.

1. `uv run --locked --env-file=<test-env> evennia test --settings test_settings.py --keepdb world.rules.tests.test_conditional_damage`
2. `uv run --locked --env-file=<test-env> evennia test --settings test_settings.py --keepdb world.rules.tests.test_skip_safety`
3. `uv run --locked --env-file=<test-env> evennia test --settings test_settings.py --keepdb tests.test_evennia_test_optimization_contract`
4. `uv run --locked python -m tools.spec_traceability check`
5. `uv run --locked python -m tools.contract_gate`
6. `openspec validate fix-combat-fixture-roster-identities --strict`

Each command must exit 0; the focused modules and ownership contract must report `OK` with no errors or failures, and both new tests must be collected rather than skipped. Record actual test counts and the two new test labels in the implementation handoff. Do not equate static traceability success with execution evidence. CI owns complete `verify --evidence` and aggregate coverage; no full-suite local run is required for this test-only repair.

Retain `.github/evennia-shards.json` unchanged: both existing module labels remain registered exactly once in their current shards. Adding test methods changes no module ownership. Preserve the exact-root branch-coverage contract over `commands`, `server`, `typeclasses`, `web`, `world`, omitting only `*/tests/*`, at least 80%; do not weaken gates or exclusions to repair these fixtures.

Review the implementation diff to confirm no production file changed and no identity fallback, `key:` path, alternative constructor, or shim was added. The negative controls provide executable evidence that a wrong-domain key still fails closed. Planning handoff runs only strict artifact validation and the required contract gate, not the reported-red module commands.

## Risks / Trade-offs

The fled-label write is masked by the constructor exception and must be repaired in the same patch. Changing registry assertions to `dbref:` would introduce a new bug because the registry has a different key domain. Centralizing only the three conditional test constructors avoids divergence while keeping the shared fixture API unchanged. Real persisted characters must remain real so nonlethal and transaction rollback coverage retains its integration boundary. No schema or data migration is involved.
