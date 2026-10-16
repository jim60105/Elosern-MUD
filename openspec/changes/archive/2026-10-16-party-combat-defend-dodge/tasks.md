# Tasks

Total estimate: **7 hours**, including implementation, focused verification, documentation and integration. Direct prerequisites and file/spec conflicts are in proposal.md and the shared batch contract. Each group lands its own tests/docs; the final group checks integration.

## 1. Bounded implementation and evidence (1.5h)

- [x] 1.1 Add closed tactical requests and validated constants; test zero MP/SP, consecutive use, actor eligibility and enemy nonavailability.

  Evidence: finite `tactics.defend_reduction` in `[0, 1)` and finite
  non-negative `tactics.dodge_threshold_bonus` are required and bounded at
  `world/rules/combat/battlefield.py::validate_combat_rulebook` (the existing
  rulebook load boundary); the closed `defend`/`dodge` tactical draft keys are
  accepted by `combat_session/rounds.py::_draft_tactical_declarations` and the
  actor's own roster key is the only channel
  (`test_defend_dodge.py::RoundStartConstantValidationTests`,
  `::EnemyUnavailableTests`). Zero MP/SP and no cooldown follow from the
  declaration never being a skill occurrence: it costs nothing and consumes
  only the actor's selected action
  (`test_combat_session_persistence.py::test_round_start_declaration_is_projected_and_skips_the_ordinary_request`).
  Enemies gain neither: declarations map only accepted allied draft entries.

## 2. Bounded implementation and evidence (1.5h)

- [x] 2.1 Activate Defend/Dodge at the round-start hook and implement shared scalar inputs; prove slow actor protection, 40 to 26 flooring, bypass/upkeep exceptions and no-check behavior.

  Evidence: `run_round` is the sole writer of the round execution context and
  activates the declarations on `battlefield.tactical` before
  `_resolve_round` rolls initiative, clearing them in a `finally`
  (`test_defend_dodge.py::RoundTacticalScopeTests`, which proves the fast
  enemy sees the active declaration before the slow declarer acts, that the
  second round sees none, and that a raising round clears the context).
  `strike_amount` applies `max(floor(scaled * (1 - reduction)), floor)` after
  scale (`::DefendScalarTests`, the 40 -> 26 example);
  `damage.py::_handle_damage` applies it to the recipient's declaration and
  skips it for an explicitly defense-bypassing occurrence while a zero-defense
  recipient still receives it (`::DamageHandlerTacticalTests`). Damaging
  upkeep is structurally exempt because `tick_buffs` never enters
  `strike_amount`; unchecked damage gets no invented roll because Defend never
  rolls.

## 3. Bounded implementation and evidence (1.5h)

- [x] 3.1 Use the same context in AI estimation and every per-strike hit check; pin solid-hit/critical placement, AREA checks and no initiative/flee changes.

  Evidence: `hit_margin` gains the rulebook threshold bonus for a dodging
  defender and `damage.py::_to_hit` passes it per recipient, so AREA resolves
  each recipient's own check and raw-100 still requires landing
  (`test_defend_dodge.py::DodgeScalarTests`,
  `::DamageHandlerTacticalTests::test_dodge_is_applied_per_recipient_and_raw_100_never_overrides_it`).
  `monster_ai/estimation.py::_Decision` reads the same round context and
  `_strike_outcomes` mirrors settlement's bypass rule; the numeric parity for a
  defending and a dodging recipient is pinned by
  `test_monster_ai_estimation.py::ScaleGateAndPoolTests::test_round_start_declarations_drive_the_estimated_strike`.
  Initiative (`roll_initiative`) and the retreat contest are untouched: the
  dodge bonus is added only inside `hit_margin`.

## 4. Bounded implementation and evidence (1h)

- [x] 4.1 Test round-end, rollback, disconnect and next-round expiry without stacking or durable buff leakage; update affected developer arithmetic docs.

  Evidence: the tactical lives only in the transient round execution context
  (`Battlefield.tactical`), cleared in `run_round`'s `finally` on normal return
  and on a technical failure, so nothing durable is written, nothing stacks
  across rounds, and a recovered draft carries the choice, not an activated
  effect (`test_defend_dodge.py::RoundTacticalScopeTests`). The engine design's
  damage formula is amended for both stages
  (`docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md`).

## 5. Bounded implementation and evidence (0.75h)

- [x] 5.1 Update canonical traceability and fixture/shard ownership; migrate scalar callsites without optional compatibility branches.

  Evidence: the dodge tests carry the MODIFIED to-hit requirement id that
  exists in the main spec; the new pure module is registered in exactly one
  shard (`.github/evennia-shards.json`). All callers of the shared scalars were
  migrated to the new inputs in this change
  (`damage.py::_to_hit`/`_handle_damage`, `monster_ai/estimation.py::_strike_outcomes`);
  no adapter, duplicate formula or optional branch remains.

  Traceability ordering (`docs/development/spec-test-traceability.md`):
  `tools.spec_traceability` resolves ids against main specs under
  `openspec/specs/` only, so the ids this change ADDS
  (`combat-resolution::defend-and-dodge-consume-one-zero-resource-round-start-action`,
  `combat-resolution::defend-reduces-eligible-final-scaled-direct-damage`,
  `combat-resolution::dodge-affects-only-shared-hit-checks-and-their-margins`)
  do not exist until `openspec archive` syncs the delta and cannot be
  annotated now: an annotation with one of them fails `tools.spec_traceability
  check` with `unknown-requirement-id`. They are annotated at archive time;
  the MODIFIED to-hit id is annotated on its establishing dodge tests today.

## 6. Integration gate (0.75h)

- [x] 6.1 Run focused tactical/scalar/estimator/round tests and tools.contract_gate; run observability lint only if boundary logging changed.

  Evidence: focused modules pass standalone — `test_defend_dodge`,
  `test_damage_bands`, `test_monster_ai_estimation`,
  `test_monster_ai_activation` (the tuning fingerprint is unchanged),
  `test_combat_session_persistence.SessionPersistenceTests`,
  `test_combat_session_flow.test_engage_group_flow`,
  `test_combat_session_flow.test_opening_dispatch_selection`,
  `test_item_combat_turn`, `test_party_offline_loop`,
  `test_on_hit_counter_damage`, `test_initiative_and_turn_loop`,
  `test_combat_party`, `test_lightning_turn_behavior`.
  `tools.contract_gate` passes (traceability, both lints, manifests,
  contracts). No boundary logging changed, so the observability lint was not
  re-run beyond the gate's own pass.
