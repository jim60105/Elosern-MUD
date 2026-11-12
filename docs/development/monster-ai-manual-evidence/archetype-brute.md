# Manual archetype campaign: `brute` (monster-ai-manual-evidence)

- Baseline commit: `113014bf9dae5d5b2e354f4c4afdbe61006454e2`
- Configuration fingerprint: `6c8e5bdab452aa2b15963a91978e145bec3c6642b49e2b3da46f2b8f3c58f921`
- Allocation: 24 encounters (['finishing_choice', 'area_versus_single', 'resource_exhaustion', 'mandatory_targeting', 'support_and_focus', 'long_lifecycle'] situations x 2 seeds x 2 intelligence values), round cap 30

Overall: 24 win / 0 loss / 0 capped, mean rounds 7.58 (denominator 24 encounters), highest-utility fraction 0.238, selected illegal 0.

No-action causes (legal restriction / estimator exclusion / budget omission): 0 / 0 / 0.

Target concentration over encounter-local roles: mean top-role share 0.640, 20 encounter(s) put at least half their choices on one role. Every decision's effective seed, execution identity, sampled plans, selected plan and initial observation snapshot are recorded in `raw[].decision_records`.

| situation | intelligence | win/loss/capped | mean rounds | highest-utility |
| --- | ---: | --- | ---: | ---: |
| finishing_choice | 10 | 2/0/0 | 4.50 | 0.000 |
| finishing_choice | 90 | 2/0/0 | 4.50 | 0.429 |
| area_versus_single | 10 | 2/0/0 | 6.00 | 0.083 |
| area_versus_single | 90 | 2/0/0 | 6.00 | 0.083 |
| resource_exhaustion | 10 | 2/0/0 | 8.00 | 0.133 |
| resource_exhaustion | 90 | 2/0/0 | 10.50 | 0.500 |
| mandatory_targeting | 10 | 2/0/0 | 7.50 | 0.286 |
| mandatory_targeting | 90 | 2/0/0 | 4.50 | 0.750 |
| support_and_focus | 10 | 2/0/0 | 12.00 | 0.172 |
| support_and_focus | 90 | 2/0/0 | 6.00 | 0.412 |
| long_lifecycle | 10 | 2/0/0 | 9.50 | 0.053 |
| long_lifecycle | 90 | 2/0/0 | 12.00 | 0.167 |

Unresolved (capped) encounters: 0. Two seeds per situation cannot certify balance; the acceptance claims are valid execution, replay, distinct profiles and intelligence affecting decision quality while stats stay identical.
