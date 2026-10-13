# Manual archetype campaign: `ambush_predator` (monster-ai-manual-evidence)

- Baseline commit: `ab8b457ddc4265482766d601d99a6555e3f88e82`
- Configuration fingerprint: `e40c071ef3a428c419c6ff58c9750c77b93d01d01911b3dc2f3c62f09ac20232`
- Allocation: 24 encounters (['finishing_choice', 'area_versus_single', 'resource_exhaustion', 'mandatory_targeting', 'support_and_focus', 'long_lifecycle'] situations x 2 seeds x 2 intelligence values), round cap 30

Overall: 24 win / 0 loss / 0 capped, mean rounds 8.17 (denominator 24 encounters), highest-utility fraction 0.348, selected illegal 0.

No-action causes (legal restriction / estimator exclusion / budget omission): 0 / 0 / 0.

Target concentration over encounter-local roles: mean top-role share 0.680, 23 encounter(s) put at least half their choices on one role. Every decision's effective seed, execution identity, sampled plans, selected plan and initial observation snapshot are recorded in `raw[].decision_records`.

| situation | intelligence | win/loss/capped | mean rounds | highest-utility |
| --- | ---: | --- | ---: | ---: |
| finishing_choice | 10 | 2/0/0 | 4.50 | 0.000 |
| finishing_choice | 90 | 2/0/0 | 4.50 | 0.125 |
| area_versus_single | 10 | 2/0/0 | 5.50 | 0.400 |
| area_versus_single | 90 | 2/0/0 | 6.00 | 0.455 |
| resource_exhaustion | 10 | 2/0/0 | 13.50 | 0.308 |
| resource_exhaustion | 90 | 2/0/0 | 9.50 | 0.556 |
| mandatory_targeting | 10 | 2/0/0 | 8.50 | 0.294 |
| mandatory_targeting | 90 | 2/0/0 | 6.50 | 0.308 |
| support_and_focus | 10 | 2/0/0 | 8.00 | 0.300 |
| support_and_focus | 90 | 2/0/0 | 8.50 | 0.591 |
| long_lifecycle | 10 | 2/0/0 | 12.00 | 0.174 |
| long_lifecycle | 90 | 2/0/0 | 11.00 | 0.409 |

Unresolved (capped) encounters: 0. Two seeds per situation cannot certify balance; the acceptance claims are valid execution, replay, distinct profiles and intelligence affecting decision quality while stats stay identical.
