# Monster AI staged activation evidence (monster-ai-staged-activation)

Release record for the first production utility activation. It is manual release
evidence, not a test input beyond the machine-readable companion
(`activation.json`), which
`world.rules.tests.test_monster_ai_activation` reads to establish that this
record still describes the tuning the process loads.

## What is activated

Three registered variants are switched from the permanent legacy decision to the
utility decision by `variant_decision_mode` in
`world/rules/rulebook/monster_behaviour.yaml`, each with its own explicitly
authored intelligence:

| variant | display | tier | archetype | intelligence | why this value |
| --- | --- | --- | --- | ---: | --- |
| `flock_leader` | 領群型 | low | instinctive | 58 | Its own lore has it coordinate the flock's calls and vary its own angle of attack, so it weighs several allies and targets at once. |
| `reef_warden` | 守礁型 | low | instinctive | 66 | Its own lore has it pick and hold the narrowest reef mouth that shields its group: it reads the terrain and the group it protects before acting. |
| `trail_hunter` | 獵道型 | mid | ambush_predator | 44 | Its own lore is one repeated rule -- probe the party's edge, avoid a formed line -- which is the least decision depth of the three. |

The values are read from each row's authored bestiary lore, never from its
threat tier, ordinary/stronger rank, combat numbers or archetype: the low-tier
reef warden deliberately outranks the mid-tier trail hunter. Every other
registered variant authors neither an intelligence nor a mode override and keeps
its archetype's legacy mode; nothing supplies intelligence or a mode by tier,
species, rank, stat or archetype.

Tuning fingerprint of the activated configuration (algorithm version 5):
`23e711e9bb93a0c9c0e0b66a72f5c17bb4c9bb78c6693b540b34ad54b7da37ba`.

## Evidence linkage

Every acceptance clause of the change, and where it is established:

| acceptance clause | evidence |
| --- | --- |
| Attack/tactics regressions, real production smoke and the repository contract gate | `gates.txt` and `focused-tests.txt` beside this record. `uv run --locked python -m tools.contract_gate` passes observability, test-data, shard manifests and the ownership contracts; its traceability gate reports the change's own four new capability IDs as `unknown-requirement-id`, which is the documented pre-sync state of an active change (its requirements enter the index only when the archive workflow syncs the delta; see `scripts/openspec-gates.sh`). Verified green against the equivalent delta-applied tree: 2189 requirements, 0 uncovered, 0 errors. The post-sync check is the authoritative one and belongs to the archive workflow. |
| The approved manual campaign was executed with raw reports | `docs/development/monster-ai-manual-evidence/` (144 encounters, two documented seeds, intelligence 10/90; selector and performance operations), fingerprint `e40c071ef3a428c419c6ff58c9750c77b93d01d01911b3dc2f3c62f09ac20232` |
| Selector threshold | `selector-check.json`: paired difference 0.344 against the required 0.15, `margin_met` true; the report was regenerated under the activated fingerprint `23e711e9...` |
| Complete-policy performance | `performance.json`: warm utility p95 15.78 ms and p50 15.50 ms against the 50 ms budget, `budget_met` true, `dice_isolated` true |
| A small explicit named registered set with independently authored intelligence | `activation.json` `activated` + the table above; `ActivationBindingTests` resolves each name through the real species/variant registry and proves every other registered variant still resolves legacy |
| A real affected encounter | `RealEncounterTests`: one real `Monster` row of an activated variant decides inside a real round scope **through the production session adapter** (`_enemy_policy`), its selected candidate is the request that settlement receives, the round writes a damage entry and the defender's committed hit points fall, and the monster's own statistics, resources, kit and proficiency are unchanged |
| Rollback without migration or restore | `legacy_rollback` below, with `RollbackTests` |
| Release evidence is reproducible and scoped | `ActivationRecordTests` re-derives the record's name set, fingerprints and evidence files from this tuning; the new test module has one shard owner and the manual operations stayed manual tools |

## Exact operations

Captured outputs are committed beside this record: `focused-tests.txt` (the
focused labels) and `gates.txt` (the repository gates). Focused slice
verification is the only locally run test command; the full suite, browser
suites and automatic manual campaigns are CI- or human-owned:

```sh
printf 'MUD_TEST_SETTINGS=1\n' > /tmp/mud-test-env
uv run --locked --env-file=/tmp/mud-test-env evennia test --settings test_settings.py --keepdb \
  world.rules.tests.test_monster_ai_activation
rm /tmp/mud-test-env
```

The affected existing labels of the same run (all green):

```sh
uv run --locked --env-file=/tmp/mud-test-env evennia test --settings test_settings.py --keepdb \
  world.rules.tests.test_monster_behaviour_profile \
  world.rules.tests.test_monster_ai_tuning \
  world.rules.tests.test_monster_behaviour_policy \
  world.rules.tests.test_monster_behaviour_integration \
  world.rules.tests.test_monster_behaviour_golden \
  world.rules.tests.test_monster_behaviour_determinism \
  world.rules.tests.test_monster_behaviour_selection \
  world.rules.tests.test_monster_composition_coverage \
  world.rules.tests.test_crocodile_resource_skill \
  world.rules.tests.test_sway_whistle_sparrow_resource_skill \
  world.rules.tests.test_tide_lamp_crab_resource_skill \
  world.rules.tests.test_monster_individual \
  world.rules.tests.test_monster_scale \
  world.rules.tests.test_monster_ai_candidates \
  world.rules.tests.test_monster_ai_estimation \
  world.rules.tests.test_monster_ai_memory \
  world.rules.tests.test_monster_ai_coordination \
  world.rules.tests.test_monster_ai_selection \
  world.rules.tests.test_monster_ai_support \
  world.rules.tests.test_monster_ai_snapshots \
  world.rules.tests.test_monster_ai_manual_reports \
  world.rules.tests.test_human_combat_calibration
```

One unrelated label stays red on `master` as well and is not this slice's:
`world.rules.tests.test_monster_flee_decision.MonsterFleePolicyTests.test_source_preserves_deterministic_single_writer_boundary`
compares `world/rules/monster_behaviour.py` against a forbidden-literal list
that still bans `0.25`, while that file legitimately carries
`THREAT_DECAY_STEPS = (1.0, 0.5, 0.25)` from the observed-coordination slice.
The conflict exists in the branch's base commit.

Repository gates:

```sh
uv run --locked openspec validate monster-ai-staged-activation --type change --strict
uv run --locked python -m tools.contract_gate
uv run --locked python -m tools.test_data_lint check
```

The one manual operation this slice reran, because its report records the
process's *startup* fingerprint and the activation moved it:

```sh
uv run --locked python tools/monster_ai_manual_reports.py selector
```

Its outputs replace `docs/development/monster-ai-manual-evidence/selector-check.json`
and `.md`; the six archetype campaigns and the performance report were *not*
rerun, because their harness builds the campaign's own synthetic variant pairs
and copies only the archetypes from the shipped rulebook, so the shipped
variant maps do not enter their tuning or their recorded fingerprint
(`e40c071e...`, unchanged).

## Seeds

* Real affected encounter: session `activation:1:0`, round `1`, the actor's own
  allocated dbref identity, and the combat initiative and to-hit dice patched to
  `95`. The decision's own selector seed is derived by the production function
  from that scope and the tuning fingerprint, so it is recorded by the trace the
  test asserts on, not invented here.
* Legacy smoke: the same field, with the selection roller patched to raise, so
  the legacy body must return its deterministic target and skill without
  spending a selection die; the flee case is exercised at the archetype's own
  authored fraction.
* Manual selector check: the documented 128 injected seeds, intelligence 10/90.

## Rollback

The activation is a rulebook mode map, so rollback is an edit plus a restart:

1. Set `variant_decision_mode: {}` (the three named entries removed;
   `variant_intelligence` is kept and remains validated).
2. Restart the process. Startup validation is the only path that loads a
   changed on-disk mode; there is no hot reload, and a new *session* in the
   running process keeps the tuning the process already recorded.
3. Continue playing: the selected variants take the permanent legacy decision
   again -- legacy target strategy, legacy skill choice, legacy flee priority
   and the legacy dice usage -- with no data migration and no database restore.
   Restarting also clears the in-process tactical history (recorded session
   tuning and the observation memory).

Rollback fingerprint of the edited configuration:
`878a9106ed51750c5079ea02e910b92c5037d4b08b8033a767d063945125bcd8`. Recorded
acceptance claims made under `23e711e9...` do not describe it, which is exactly
what the fingerprinted record and the focused tests enforce.

## Expansion and retuning

To activate more variants, or to retune one of these:

1. Author the intelligence and the mode for the named registered variant only,
   justified from that variant's own lore (never from its tier, rank or stats).
2. Rerun the *affected* focused scenarios only: the activation contract module,
   the tuning/profile contracts, and -- when the utility arithmetic itself
   changes -- the archetype campaign of the affected profile. Never rerun every
   archetype automatically, and never treat a retune as a statistic rebalance:
   intelligence changes decisions only.
3. Record the new tuning fingerprint in this directory and regenerate the
   evidence whose header carries the moved fingerprint (the selector report
   records the startup fingerprint; the campaign and performance reports record
   their own harness tuning).
4. Archive the previous fingerprint's claims as superseded. An acceptance claim
   made under an older fingerprint is not evidence for the changed tuning.

## Uncertainty and volatility

* Two documented seeds per situation cannot certify balance, and this record
  makes no difficulty claim: the manual evidence establishes exercised
  boundaries, verified preconditions, decision shares, replay inputs and a
  timing envelope.
* Three variants of one archetype pair is a first small set, not a policy for
  the whole bestiary; the remaining registered variants stay legacy until their
  own evidence exists.
* The utility decision samples with a temperature derived from intelligence, so
  a single encounter is one draw, not a deterministic script; the recorded
  decision scope, tuning fingerprint and trace are what make a decision
  reproducible, not the encounter.
* An activated variant no longer takes the legacy flee action: the utility
  decision proposes owned, modelable actions only, and the flee thresholds,
  `FLEE_SKILL_KEY` and the flee priority stay with the permanent legacy mode.
  All three activated variants are low- and mid-tier monsters whose own lore
  keeps them in the fight (a flock leader coordinating, a reef warden holding
  its narrow mouth, a trail hunter probing the edge), and rollback restores the
  legacy flee priority for them immediately.
* Reaching production does not add a player command or a browser action.