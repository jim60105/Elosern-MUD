# Monster AI staged activation evidence (monster-ai-staged-activation)

Release record for the production deliberation activation. It is manual release
evidence, not a test input beyond the machine-readable companion
(`activation.json`), which
`world.rules.tests.test_monster_ai_activation` reads to establish that this
record still describes the tuning the process loads.

## What is activated

Six registered variants are switched from the permanent reflex decision to the
deliberation decision by `variant_decision_mode` in
`world/rules/rulebook/monster_behaviour.yaml`, each with its own explicitly
authored intelligence:

| variant | display | tier | archetype | intelligence | why this value |
| --- | --- | --- | --- | ---: | --- |
| `flock_leader` | 領群型 | low | instinctive | 58 | Its own lore has it coordinate the flock's calls and vary its own angle of attack, so it weighs several allies and targets at once. |
| `mudbank_dweller` | 濕岸型 | low | instinctive | 20 | Its own lore has it tighten its film only when pressed and bump back at short range, so reflexive self-protection is the least decision depth of the activated set. |
| `reef_warden` | 守礁型 | low | instinctive | 66 | Its own lore has it pick and hold the narrowest reef mouth that shields its group: it reads the terrain and the group it protects before acting. |
| `reservoir_warden` | 蓄潮型 | high | ambush_predator | 62 | Its own lore has it weigh drawing an opponent's magic against spending its own on the film, a recurring trade-off read from its own resources. |
| `trail_hunter` | 獵道型 | mid | ambush_predator | 44 | Its own lore is one repeated rule -- probe the party's edge, avoid a formed line -- which is the least decision depth of the earlier three. |
| `wax_cache_forager` | 藏穀型 | low | instinctive | 30 | Its own lore has it time its slip around a defended cache and family foraging, a little more situational reading than the slime's reflexive film. |

The values are read from each row's authored bestiary lore, never from its
threat tier, ordinary/stronger rank, combat numbers or archetype: the low-tier
reef warden deliberately outranks the mid-tier trail hunter. Every other
registered variant authors neither an intelligence nor a mode override and keeps
its archetype's reflex mode; nothing supplies intelligence or a mode by tier,
species, rank, stat or archetype.

Tuning fingerprint of the activated configuration (algorithm version 6):
`5b46ee570d95fc99507b303509e634f9387830a4a7fa87249d23a1d05bb9fba3`.

`reservoir-warden-variant` adds the high-tier 蓄潮型 `reservoir_warden` to the
named set with its own authored intelligence of 62. Its new buff definition and
modifier rule also move the startup fingerprint because every estimate averages
over them. `膠掌小鬼` stays reflex, so it keeps its archetype's flee threshold
and never enters this table.

## Evidence linkage

Every acceptance clause of the change, and where it is established:

| acceptance clause | evidence |
| --- | --- |
| Attack/tactics regressions, real production smoke and the repository contract gate | `gates.txt` and `focused-tests.txt` beside this record. `uv run --locked python -m tools.contract_gate --change monster-decision-modes-rename-and-reflex-area-estimate` passes reference-context, traceability, observability, test-data, shard manifests and the ownership contracts: 2726 requirements, 0 uncovered, 0 errors, and zero observability or test-data violations. This change adds no new capability or requirement heading, so the pre-sync gate is already authoritative for it; the archive workflow's post-sync run remains the final check. |
| The approved manual campaign was executed with raw reports | `docs/development/monster-ai-manual-evidence/` (144 encounters, two documented seeds, intelligence 10/90; selector and performance operations), fingerprint `6c8e5bdab452aa2b15963a91978e145bec3c6642b49e2b3da46f2b8f3c58f921` |
| Selector threshold | `selector-check.json`: paired difference 0.344 against the required 0.15, `margin_met` true; the report was regenerated under the activated fingerprint `5b46ee57...` |
| Complete-policy performance | `performance.json`: warm deliberation p95 17.18 ms and p50 16.86 ms against the 50 ms budget, `budget_met` true, `dice_isolated` true |
| A small explicit named registered set with independently authored intelligence | `activation.json` `activated` + the table above; `ActivationBindingTests` resolves each name through the real species/variant registry and proves every other registered variant still resolves reflex |
| A real affected encounter | `RealEncounterTests`: one real `Monster` row of an activated variant decides inside a real round scope **through the production session adapter** (`_enemy_policy`), its selected candidate is the request that settlement receives, the round writes a damage entry and the defender's committed hit points fall, and the monster's own statistics, resources, kit and proficiency are unchanged |
| Rollback without migration or restore | `reflex_rollback` below, with `RollbackTests` |
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

`monster-decision-modes-rename-and-reflex-area-estimate` reran **all eight**
manual operations, because the mode rename and the new reflex estimate change
what an identical tuning decides, so neither the startup-fingerprint selector
report nor the campaign/performance harness reports could stand:

```sh
uv run --locked python tools/monster_ai_manual_reports.py selector
uv run --locked python tools/monster_ai_manual_reports.py archetype --archetype <name>
uv run --locked python tools/monster_ai_manual_reports.py performance
```

Their outputs replace the whole of `docs/development/monster-ai-manual-evidence/`:
the selector pair now records the startup fingerprint `5b46ee57...` and the six
campaigns plus the performance report record the version 6 harness fingerprint
`6c8e5bdab452...`. Every earlier value is superseded history.

## Seeds

* Real affected encounter: session `activation:1:0`, round `1`, the actor's own
  allocated dbref identity, and the combat initiative and to-hit dice patched to
  `95`. The decision's own selector seed is derived by the production function
  from that scope and the tuning fingerprint, so it is recorded by the trace the
  test asserts on, not invented here.
* Reflex smoke: the same field, with the selection roller patched to raise, so
  the reflex body must return its deterministic target and skill without
  spending a selection die; the flee case is exercised at the archetype's own
  authored fraction.
* Manual selector check: the documented 128 injected seeds, intelligence 10/90.

## Rollback

The activation is a rulebook mode map, so rollback is an edit plus a restart:

1. Set `variant_decision_mode: {}` (the six named entries removed;
   `variant_intelligence` is kept and remains validated).
2. Restart the process. Startup validation is the only path that loads a
   changed on-disk mode; there is no hot reload, and a new *session* in the
   running process keeps the tuning the process already recorded.
3. Continue playing: the selected variants take the permanent reflex decision
   again -- reflex target strategy, reflex skill choice, reflex flee priority,
   the exact `E = A * c * R` estimate and its target tie-break dice -- with no
   data migration and no database restore.
   Restarting also clears the in-process tactical history (recorded session
   tuning and the observation memory).

Rollback fingerprint of the edited configuration:
`6703850479fbbf10e9ad925032947f124520f45972a9779ad67d1ee843450d87`. Recorded
acceptance claims made under `5b46ee57...` do not describe it, which is exactly
what the fingerprinted record and the focused tests enforce. The earlier
activation fingerprints `bd82767e...`, `8b56d98c...`, `877fdd6d...`, `70e5f38d...`, `383b1eff...`, `ef4b4b14...`, `5828d932...`, `75b74aa1...`, `b0dd9da6...`, `955832b5...`, `5f4a4506...`, `03ad9da4...`, `abb0989c...`, `3232b667...`, `d65909aa...`, `cd78725a...`, `f8858072...`, `3030d4a3...`, `fc1dd263...`, `7c1cafd7...` and their predecessors, together with the earlier rollback fingerprints `56152d3a...`, `4c696e11...`, `6639e736...` and their predecessors, describe tunings
production no longer loads and are superseded, not evidence for the changed
tuning.

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
* Six activated variants are a small named set, not a policy for the whole
  bestiary; the remaining registered variants stay reflex until their own
  evidence exists.
* The deliberation decision samples with a temperature derived from intelligence, so
  a single encounter is one draw, not a deterministic script; the recorded
  decision scope, tuning fingerprint and trace are what make a decision
  reproducible, not the encounter.
* An activated variant no longer takes the reflex flee action: the deliberation
  decision proposes owned, modelable actions only, and the flee thresholds,
  `FLEE_SKILL_KEY` and the flee priority stay with the permanent reflex mode.
  The original three activated variants are low- and mid-tier monsters whose
  own lore keeps them in the fight (a flock leader coordinating, a reef warden
  holding its narrow mouth, a trail hunter probing the edge); the slime's and
  the rat's retreat orientation are expressed instead through passive or
  defended-area field aggression, the known deviation recorded in design
  §12.4 and `docs/development/monster-content-expansion.md`. The high-tier
  crocodile boss follows the same trade-off: its escapes in play come from the
  opposing party's paid retreat, and rollback restores the reflex flee priority
  for all six immediately.
* Reaching production does not add a player command or a browser action.