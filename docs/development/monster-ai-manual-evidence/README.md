# Monster AI manual acceptance evidence (monster-ai-manual-evidence)

Raw reports produced by the manual tool for this change. They are manual
acceptance evidence only: no default test, CI job or contract gate runs the
campaign, and the focused test module
(`world.rules.tests.test_monster_ai_manual_reports`) establishes the tool's own
contracts without ever rerunning the allocation.

Baseline commit: `143b28d6f2cb07090f88753eacd4ea0c32e0246c` (the merge that this
feature branch was cut from). Host: `Jim-Fedora`,
`Linux-7.2.6-200.fc44.x86_64-x86_64-with-glibc2.43`, CPython 3.13.14.

## Exact operations

Each operation is one explicit command, run from the repository root. Every run
configures a fresh isolated temporary SQLite database (the tool refuses the live
`server/db/evennia.db3` and the retained `server/db/evennia-test.sqlite3`) and
touches no network or model service.

```sh
uv run --locked python tools/monster_ai_manual_reports.py selector
uv run --locked python tools/monster_ai_manual_reports.py archetype --archetype ambush_predator
uv run --locked python tools/monster_ai_manual_reports.py archetype --archetype apex_predator
uv run --locked python tools/monster_ai_manual_reports.py archetype --archetype brute
uv run --locked python tools/monster_ai_manual_reports.py archetype --archetype instinctive
uv run --locked python tools/monster_ai_manual_reports.py archetype --archetype pack_hunter
uv run --locked python tools/monster_ai_manual_reports.py archetype --archetype tactical_caster
uv run --locked python tools/monster_ai_manual_reports.py performance
```

The six archetypes are the authored behaviour profiles of
`world/rules/rulebook/monster_behaviour.yaml`. Each `archetype` invocation runs
exactly that archetype's 24 encounters (six situations x two documented seeds x
intelligence 10/90, round cap 30) through the real combat-session
round/resolver boundary with committed reload; the six invocations total 144
utility encounters. The whole set completed in 94 s wall clock.

Configuration fingerprint (all campaign and performance reports):
`e40c071ef3a428c419c6ff58c9750c77b93d01d01911b3dc2f3c62f09ac20232`
(algorithm version 5). Selector-check fingerprint:
`a29fd4fac5f07d65eb40377ee4dafe400c977738a321e8028852c9169cefe9c4`.

## Results

### Paired selector check (`selector-check.json` / `.md`)

Two legal candidates with a fixed utility gap of 0.5, the same 128 documented
injected seeds at intelligence 10 and 90, sampled with the production selection
function and stable candidate ordering.

| intelligence | highest-utility count | proportion | Wilson 95% |
| --- | ---: | ---: | --- |
| 10 | 74 | 0.578 | [0.492, 0.660] |
| 90 | 118 | 0.922 | [0.862, 0.957] |

Paired difference (high - low): **0.344** (required >= 0.15): met.

### Archetype campaigns (`archetype-<name>.json` / `.md`)

| archetype | encounters | win | loss | capped | mean rounds | highest-utility fraction | decisions | selected illegal |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ambush_predator | 24 | 20 | 0 | 4 | 6.79 | 0.489 | 190 | 0 |
| apex_predator | 24 | 20 | 0 | 4 | 5.33 | 0.368 | 125 | 0 |
| brute | 24 | 20 | 0 | 4 | 7.46 | 0.378 | 193 | 0 |
| instinctive | 24 | 20 | 0 | 4 | 6.08 | 0.390 | 159 | 0 |
| pack_hunter | 24 | 20 | 0 | 4 | 6.42 | 0.383 | 154 | 0 |
| tactical_caster | 24 | 20 | 0 | 4 | 6.96 | 0.446 | 175 | 0 |

Every archetype totals 24 encounters (144 across the six); capped encounters
are reported as unresolved, never as a win or loss; no selected action was
refused by settlement and no decision hit a legitimate-restriction,
estimator-exclusion or budget-omission no-action boundary in these fixtures.

### Whole-policy performance (`performance.json` / `.md`)

Reference envelope: 16 participants, up to 16 owned active skills, candidate
budget 256; one cold call, five warm-ups and fifty measured decisions per mode.

| mode | cold ms | p50 ms | p95 ms | queries | examined | accepted | omitted | dice isolated |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| legacy | 3.98 | 0.56 | 0.74 | 10 | 0 | 0 | 0 | False |
| utility | 44.53 | 14.79 | 14.96 | 97 | 98 | 98 | 0 | True |

Warm utility p95 budget 50 ms: met. The candidate-scaling probe holds the
16-participant envelope fixed and trades allies for enemies: examined
42 / 98 / 154 candidates at 97 queries each, i.e. no candidate-proportional ORM
work. The utility policy draws from its own generator and never advances the
combat dice stream; the legacy body is the retained rulebook policy and
legitimately consumes it.

## Interpretation limits

Two seeds per situation cannot certify balance: the report states uncertainty,
makes no balance-certification claim, and does not claim monotonically
increasing win rates. The acceptance claims are valid execution, replay,
distinct profiles and intelligence affecting decision quality while stats,
ownership and proficiency stay identical between the paired variants.