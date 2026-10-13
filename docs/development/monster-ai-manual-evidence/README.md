# Monster AI manual acceptance evidence (monster-ai-manual-evidence)

Raw reports produced by the manual tool for this change. They are manual
acceptance evidence only: no default test, CI job or contract gate runs the
campaign, and the focused test module
(`world.rules.tests.test_monster_ai_manual_reports`) establishes the tool's own
contracts without ever rerunning the allocation.

Baseline commit: `ab8b457ddc4265482766d601d99a6555e3f88e82` (the implementation
commit these reports were generated from). Host: `Jim-Fedora`,
`Linux-7.2.6-200.fc44.x86_64-x86_64-with-glibc2.43`, CPython 3.13.14, Evennia
`6.1.0 (rev ab8b457d)`.

## Exact operations

Each operation is one explicit command, run from the repository root, and each
writes its JSON/Markdown pair into the tool's own default output directory
(`.var/monster-ai-manual-reports`); the files beside this README are those
outputs copied verbatim.

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

The opt-in detailed trace is a separate explicit invocation and a separate
document: `--detailed-trace` writes `archetype-<name>-traces.json` beside the
report (the normalized per-decision `DecisionTrace` projection, which excludes
queued and private intent). No such file is committed here; the compact reports
never embed traces.

Every run configures its own fresh isolated temporary SQLite database *before*
Django initializes: `DJANGO_SETTINGS_MODULE` points at the tool's own
`tools/monster_ai_manual_reports_settings.py`, which publishes the scratch path
as `DATABASES["default"]["NAME"]`, and the tool then verifies the resolved
default connection is that scratch file before it migrates anything. A named
`MUD_MANUAL_REPORT_DB` override must not already exist, and the live
`server/db/evennia.db3` and the retained `server/db/evennia-test.sqlite3` can
never be named. No network or model service is touched.

The six archetypes are the authored behaviour profiles of
`world/rules/rulebook/monster_behaviour.yaml`. Each `archetype` invocation runs
exactly that archetype's 24 encounters (six situations x two documented seeds x
intelligence 10/90, round cap 30) through the real combat-session
round/resolver boundary; the six invocations total 144 utility encounters, 1242
recorded monster decisions and 1198 committed rounds.

## What each encounter verifies

Each encounter materializes its situation with real production entities and
shipped effects, and the engaged roster is the same one production collects: the
initiating player plus companion NPCs bound through `join_party`, so
`combat_companions` really engages the multi-opponent side. The serialized
`scenarios` block records every materialized declaration, maximum and initial
hit points kept apart.

* **finishing_choice** declares an *injured* opponent (maximum 90, initial 12,
  plus a healthy second companion) and the one situation-specific monster
  offense (25) that makes a knockout of it credibly projectable. At a decision
  boundary some legal plan must project a knockout of that opponent, and every
  decision must still consider it.
* **area_versus_single** must present a legal area plan and a decision with two
  or more legal single-target plans.
* **resource_exhaustion** lowers the monster's MP pool (9) below the sum of its
  two cheapest useful skills, so at a decision boundary two accepted plans
  really compete for a pool that cannot afford both.
* **mandatory_targeting** seals two opponents and displaces the leading one. The
  player's round driver is the non-strike magic single (`t_campaign_driver`,
  `is_strike_class` is false), because a strike-class actor clears its own
  positional marker at resolution (attack design D4) and would erase the
  constraint before the monster ever decided; the mounted positional row is the
  longest-lived authored one (`displaced_apotheosis`, 90 game seconds). At every
  monster decision the seal and the displacement must still be live on the
  bearer, no strike-class plan may name it, and the legal non-strike hostile
  alternative (the kit's magic-school single) must be offered at least once.
* **support_and_focus** gives the second monster a heal kit and requires that a
  decision which observes an injured ally also offers a legal heal.
* **long_lifecycle** mounts a real finite effect (`apotheosis_retreat`) on the
  monster and checks at every decision that observation memory stays inside its
  documented retention window and record cap.

Beyond the per-decision checks, each encounter verifies its preconditions before
the first round (engaged companions, live seal and displacement, a declared
injured opponent that really starts injured, a finite effect that really
mounted), re-reads every participant from a fresh row after dropping both the
idmapper instance cache and the attribute cache and compares hit points,
resources and live effects against what the round wrote plus the session's
committed round count, and after a terminal settlement asserts the durable
session record is gone, the markers and seals are swept, and (once the
transaction has really committed) the session's observation memory is
discarded. A refused monster action aborts the whole batch with the decision's
own identity and the rejection reason instead of being recorded as a weaker
result, so `selected_illegal` in a published report is zero by construction.
Reaching the 30-round bound is reported as capped/unresolved, never as a win or
a loss.

## Decision identity and replay

The manual selection seam makes corresponding paired decisions comparable.
Before its first round each encounter rewrites its durable session record's
`session_id` to the documented scenario identity
(`manual:<situation>:<archetype>:<seed_index>`, reported beside the identity the
scratch database's own engagement allocated as
`engine_session_id`/`origin_session_id`), and each decision's scope substitutes
the encounter-local actor role (`role:monster-0`) for the scratch dbref. The
five selector-seed inputs are therefore the documented session identity, the
real round index, the encounter-local actor identity, the action slot and the
tuning fingerprint; the paired intelligence variants share all of them, so their
corresponding decisions carry identical selector seeds and differ only in the
intelligence-derived sampling temperature.

Every decision is recorded with everything a replay needs: the effective
selector seed, the temperature, the configuration fingerprint, both execution
identities, the scored plans it sampled from, the selected plan, the
examined/accepted/omitted proposal counters and its own initial observation
snapshot (`raw[].decision_records`). `examined` is the candidate set's own
counter: accepted candidates plus rejections plus mandatory-filter exclusions.

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
| ambush_predator | 24 | 24 | 0 | 0 | 8.17 | 0.348 | 198 | 0 |
| apex_predator | 24 | 24 | 0 | 0 | 8.42 | 0.370 | 216 | 0 |
| brute | 24 | 24 | 0 | 0 | 7.96 | 0.404 | 198 | 0 |
| instinctive | 24 | 24 | 0 | 0 | 8.71 | 0.240 | 217 | 0 |
| pack_hunter | 24 | 24 | 0 | 0 | 8.42 | 0.446 | 204 | 0 |
| tactical_caster | 24 | 24 | 0 | 0 | 8.25 | 0.349 | 209 | 0 |

Every archetype totals 24 encounters (144 across the six) and every encounter
reached a terminal settlement: no encounter reached the 30-round bound in this
run, so `capped` is 0 everywhere and every `unresolved` list is empty. No
decision hit a legitimate-restriction, estimator-exclusion or budget-omission
no-action boundary in these fixtures (`no_action` is 0 for all four causes), no
candidate was rejected or excluded and no budget was exhausted, and no selected
action was refused by settlement.

Target concentration is reported over encounter-local roles (the decision's own
target roles, never scratch dbrefs): per-archetype mean top-role share runs
0.650-0.775, and 21-23 of each archetype's 24 encounters put at least half their
choices on one role - the monster really does focus, and that focus is
distinguishable from choices spread across unrelated entities.

Each situation is distinct in the decisions it produces:

| situation | encounters | decisions | committed rounds | chosen skills |
| --- | ---: | ---: | ---: | --- |
| finishing_choice | 24 | 99 | 109 | strike_1 38, basic_attack 26, strike_0 22, selfheal_0 5, area_0 5, heal_0 3 |
| area_versus_single | 24 | 166 | 172 | basic_attack 61, strike_0 38, strike_1 35, area_0 14, selfheal_0 10, heal_0 8 |
| resource_exhaustion | 24 | 215 | 227 | basic_attack 91, strike_0 79, selfheal_0 25, strike_1 18, heal_0 2 |
| mandatory_targeting | 24 | 156 | 163 | strike_0 57, area_0 46, selfheal_0 32, heal_0 21 |
| support_and_focus | 24 | 288 | 198 | basic_attack 104, strike_0 98, heal_0 40, selfheal_0 20, strike_1 18, area_0 8 |
| long_lifecycle | 24 | 318 | 329 | basic_attack 96, strike_1 76, strike_0 70, area_0 28, selfheal_0 27, heal_0 21 |

`strike_0` is the kit's magic-school single strike, `strike_1` and
`basic_attack` are the physical, strike-class ones; `basic_attack` is the
production innate row the synthetic catalog carries. The mandatory-targeting
situation is the only one whose chosen skills contain **no strike-class skill at
all**: its 156 decisions across 24 encounters chose the magic single, the area
shape and the two heals, because the displaced, sealed bearer can only be named
by a non-strike plan while the constraint is live. Counts alone do not establish
that the constraints caused the difference; the constraints themselves are
verified at every decision boundary in-run, and the per-decision shares are
reported beside them for interpretation.

### Whole-policy performance (`performance.json` / `.md`)

Reference envelope: 16 participants, up to 16 owned active skills, candidate
budget 256; one cold call, five warm-ups and fifty measured decisions per mode.

| mode | cold ms | p50 ms | p95 ms | queries | examined | accepted | omitted | dice isolated |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| legacy | 4.10 | 0.60 | 0.77 | 10 | 0 | 0 | 0 | False |
| utility | 45.53 | 15.50 | 15.78 | 97 | 108 | 108 | 0 | True |

Warm utility p95 budget 50 ms: met. The utility policy draws from its own
generator and never advances the combat dice stream; the legacy body is the
retained rulebook policy and legitimately consumes it.

The candidate-query scaling probe holds **one fixed reference roster and
state** and varies only the decision's examined-proposal budget; every probe
drops the idmapper instance cache and each participant's attribute cache first,
so each one re-reads the same participants and skills:

| examined-proposal budget | queries | examined | accepted | omitted |
| ---: | ---: | ---: | ---: | ---: |
| 16 | 168 | 16 | 16 | 105 |
| 64 | 168 | 64 | 64 | 57 |
| 256 | 168 | 108 | 108 | 0 |

Query work stays at 168 queries while the examined proposals rise from 16 to
108 and the budget omissions fall from 105 to 0: the ORM work scales with the
initial participant/skill read, never with the proposals a decision examined.
This is a manual measurement on the recorded host, never a permanent timing
assertion.

## Interpretation limits

Two seeds per situation cannot certify balance: the report states uncertainty,
makes no balance-certification claim, and does not claim monotonically
increasing win rates. Every encounter in this run ended in the engaged side
defeating the monster, because each situation's synthetic monster faces two or
three production combatants at once; the finishing situation's higher monster
offense is a declared scenario parameter (reported in `scenarios`), not a
balance statement. The evidence is the exercised boundaries, the verified
preconditions, the decision shares, the replay inputs and the timing envelope,
not a difficulty verdict.

The decision seeds, combat seeds and each decision's initial observation
snapshot are recorded so a same-process replay has its inputs; the report
deliberately does not claim that a rerun on a later commit reproduces
byte-identical decisions, because the encounter's own durable identity and the
scratch database's allocated dbrefs still take part in what settlement does,
even though the selector's own inputs are documented and matched.