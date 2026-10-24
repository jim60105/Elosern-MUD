# Focused verification evidence

Local focused runs only; CI owns the full shard, browser and `verify --evidence`
suites.

## Consumer matrix (tasks 3.1, 3.2)

Every row was exercised through the real consumer boundary with synthetic party
members and a fixed reserve/posture write. "Both postures" means
`SleepPosture.FORCED` at zero reserve and `SleepPosture.VOLUNTARY` at the full
360,000 reserve, so a full reserve can never be read as awake.

| Consumer | Traverser / party shape | Labels | Observation |
| --- | --- | --- | --- |
| Plain/interior connector (`Exit`, `MovementCostMixin`) | owner + sleeping follower; possessed controller + sleeping follower; possessed controller + sleeping owner | `typeclasses.tests.test_exit_movement_cost`, `world.rules.tests.test_party_time_settlement`, `commands.tests.test_handoff_command` | `party_sleeping`; no relocation, tick, gauge or reserve change |
| Settlement/grid exit | owner + sleeping follower | `world.rules.tests.test_party_time_settlement` | unchanged locations, tick and gauges |
| Wilderness step | owner + sleeping follower | `world.rules.tests.test_movement_settlement`, `world.rules.tests.test_party_time_settlement` | unchanged coordinates, tick, knowledge, home, gauges and pool bookkeeping |
| Grid-to-wilderness gate | owner + sleeping follower; possessed controller + sleeping owner | `world.rules.tests.test_movement_settlement`, `world.rules.tests.test_party_time_settlement` | refusal before `enter_wilderness`: no destination room, registration or arrival side effect |
| Wilderness-to-grid return | owner + sleeping follower | `world.rules.tests.test_movement_settlement` | refusal before return relocation and re-anchor |
| Flight waiver (`wilderness_move`) | owner and possessed traverser, waiver owner | `world.rules.tests.test_movement` | refusal precedes waived pricing; tick unchanged |
| `flight` / `flash_step` access waiver | owner of either waiver key | `typeclasses.tests.test_exit_movement_cost` | access passes, traversal refuses before relocation |
| Pure prediction | voluntary sleeper at full reserve | `world.rules.tests.test_movement` | `party_sleeping` before integration; the same awake route prices exactly 3,600 s |
| Handoff command journey | possessed sleeping companion in the owner's party | `commands.tests.test_handoff_command` | real exit refusal with unchanged tick/locations; cast/item gates unchanged |

All-awake controls in the same modules keep the existing charge, waiver, follow
and `MOVE` pricing intact; the existing independently known threshold and
exact-zero-at-arrival tests were left unchanged
(`test_a_threshold_inside_an_edge_slows_only_the_remaining_distance`,
`test_exact_zero_arrival_applies_forced_sleep_and_refuses_the_next_departure`,
`test_a_flight_waiver...` successors above).

## Commands run

```sh
uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb world.rules.tests.test_movement
uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb typeclasses.tests.test_exit_movement_cost
uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb world.rules.tests.test_movement_settlement
uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb world.rules.tests.test_party_time_settlement
uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb commands.tests.test_handoff_command world.rules.tests.test_party_identity world.rules.tests.test_combat_party
uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb world.maps.tests.test_city_movement_cost world.maps.tests.test_movement_roundtrip world.rules.tests.test_party_follow world.rules.tests.test_party_follow_possession typeclasses.tests.test_exits
```

Results: 34, 22, 18, 34, 91 and 66 tests, all OK.

## Gates (task 3.3)

```sh
uv run --locked python -m tools.spec_traceability check   # 2495 requirements, 0 uncovered, 0 errors
uv run --locked python -m tools.contract_gate             # traceability, observability, test-data, manifests, contracts: passed
openspec validate block-travel-for-all-party-sleep --strict  # valid
openspec validate --specs                                 # 369 passed, 0 failed
```

Browser journey: no browser surface or browser method changed in this change, so
no browser shard was run. The dependent `align-sleep-handoff-and-owner-dream`
journey owns the automatic-popup integration and is reused rather than
duplicated. No full CI shard, browser suite or `verify --evidence` run was made.
