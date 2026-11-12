# Manual archetype campaign: `ambush_predator` (monster-ai-manual-evidence)

- Baseline commit: `113014bf9dae5d5b2e354f4c4afdbe61006454e2`
- Configuration fingerprint: `6c8e5bdab452aa2b15963a91978e145bec3c6642b49e2b3da46f2b8f3c58f921`
- Allocation: 24 encounters (['finishing_choice', 'area_versus_single', 'resource_exhaustion', 'mandatory_targeting', 'support_and_focus', 'long_lifecycle'] situations x 2 seeds x 2 intelligence values), round cap 30

Overall: 24 win / 0 loss / 0 capped, mean rounds 7.83 (denominator 24 encounters), highest-utility fraction 0.359, selected illegal 0.

No-action causes (legal restriction / estimator exclusion / budget omission): 0 / 0 / 0.

Target concentration over encounter-local roles: mean top-role share 0.662, 19 encounter(s) put at least half their choices on one role. Every decision's effective seed, execution identity, sampled plans, selected plan and initial observation snapshot are recorded in `raw[].decision_records`.

| situation | intelligence | win/loss/capped | mean rounds | highest-utility |
| --- | ---: | --- | ---: | ---: |
| finishing_choice | 10 | 2/0/0 | 4.00 | 0.125 |
| finishing_choice | 90 | 2/0/0 | 5.00 | 0.222 |
| area_versus_single | 10 | 2/0/0 | 6.50 | 0.273 |
| area_versus_single | 90 | 2/0/0 | 5.50 | 0.545 |
| resource_exhaustion | 10 | 2/0/0 | 11.00 | 0.095 |
| resource_exhaustion | 90 | 2/0/0 | 9.50 | 0.632 |
| mandatory_targeting | 10 | 2/0/0 | 6.50 | 0.182 |
| mandatory_targeting | 90 | 2/0/0 | 7.00 | 0.385 |
| support_and_focus | 10 | 2/0/0 | 10.00 | 0.185 |
| support_and_focus | 90 | 2/0/0 | 10.50 | 0.800 |
| long_lifecycle | 10 | 2/0/0 | 8.50 | 0.235 |
| long_lifecycle | 90 | 2/0/0 | 10.00 | 0.350 |

Unresolved (capped) encounters: 0. Two seeds per situation cannot certify balance; the acceptance claims are valid execution, replay, distinct profiles and intelligence affecting decision quality while stats stay identical.
