# Traceability cutover matrix

The delta renames the party-system requirement
`Any present forced sleeper makes party travel stationary` to
`Any present sleeper makes party travel stationary`. The canonical ID therefore
changes from `party-system::any-present-forced-sleeper-makes-party-travel-stationary`
(retired) to `party-system::any-present-sleeper-makes-party-travel-stationary`
(produced by `uv run --locked python -m tools.spec_traceability list` after the
rename).

The main spec `openspec/specs/party-system/spec.md` was synced in this change so
the canonical ID exists before the archive step. The archive workflow treats the
capability as already synced (new heading present, old heading absent) rather
than replaying the rename.

## Remounted annotations

Every annotation below previously carried the retired forced-only ID. Each one
is remounted only where its input, action and assertions establish the broadened
requirement (all sleep postures, every real travel consumer, pre-write refusal).

| Test | Role | Target ID | Basis |
| --- | --- | --- | --- |
| `world.rules.tests.test_party_time_settlement.MovementPartySettlementTests.test_every_sleep_posture_blocks_a_plain_exit_with_zero_writes` | representative consumer smoke | `party-system::any-present-sleeper-makes-party-travel-stationary` | Real plain `Exit` traversal refuses forced and voluntary sleepers with unchanged locations, tick, gauges and reserve state |
| `world.rules.tests.test_party_time_settlement.MovementPartySettlementTests.test_a_remote_sleeper_does_not_block_the_present_party` | synthetic mechanism | same | A remote sleeper of either posture grants no travelling membership; the source-present party still travels |
| `world.rules.tests.test_party_time_settlement.MovementPartySettlementTests.test_possessing_an_awake_member_cannot_carry_a_sleeper` | representative consumer smoke | same | A possessed controller with a sleeping follower and with a sleeping owner refuses the real exit for both postures |
| `world.rules.tests.test_party_time_settlement.WildernessPartySettlementTests.test_every_sleep_posture_blocks_gate_entry_with_zero_writes` | representative consumer smoke | same | Real grid-to-wilderness gate entry refuses both postures before relocation |
| `world.rules.tests.test_party_time_settlement.WildernessPartySettlementTests.test_every_sleep_posture_blocks_a_wilderness_step` | representative consumer smoke | same | Real wilderness step refuses both postures with unchanged coordinates and tick |

## Added coverage for the broadened contract

| Test | Role | Basis |
| --- | --- | --- |
| `world.rules.tests.test_movement.ChargeMovementTests.test_a_flight_waiver_never_carries_a_sleeping_member` | synthetic mechanism | The `wilderness_move` flight waiver is an early return after admission; both postures refuse with `party_sleeping` |
| `world.rules.tests.test_movement.ChargeMovementTests.test_a_waived_possessed_traverser_cannot_carry_a_sleeping_owner` | synthetic mechanism | The owner body inside the possessed traverse scope refuses a waived charge |
| `world.rules.tests.test_movement.TerrainCalibrationTests.test_prediction_refuses_a_full_reserve_voluntary_sleeper` | synthetic mechanism | Prediction refuses posture carried by state, and the same route prices 3,600 s once awake (independently known) |
| `typeclasses.tests.test_exit_movement_cost.SleepingPartyExitTests.test_every_sleep_posture_refuses_the_connector_before_any_write` | representative consumer smoke | Real interior connector refusal logs `party_sleeping` and writes nothing |
| `typeclasses.tests.test_exit_movement_cost.FlightRequiredExitTests.test_a_lawful_waiver_owner_cannot_carry_a_sleeping_companion` | representative consumer smoke | `flight` and `flash_step` access waivers pass the access gate but never the sleep barrier |
| `world.rules.tests.test_movement_settlement.MovementSettlementWildernessTests.*` | representative consumer smoke | Gate entry, wilderness step and grid return leave locations, tick, gauges, knowledge, home, reserve and pool bookkeeping unchanged |
| `world.rules.tests.test_party_identity.PartyIdentityTests.test_a_sleeping_temporary_escort_blocks_through_the_canonical_scope` | synthetic mechanism | A temporary-only effective member is inside the canonical scope and blocks |
| `commands.tests.test_handoff_command.HandoffCommandTests.test_sleeping_body_still_cannot_cast_use_items_or_travel` | representative command smoke | A real `Exit` traversal refuses while the party contains the sleeping body; `foot_speed_scale` policy is asserted separately |
| `world.rules.tests.test_combat_party.EngagePartyTests.test_a_sleeping_companion_leaves_local_engagement_available` | synthetic mechanism | Local combat remains lawful with a sleeping companion, so the barrier adds no action lock |
