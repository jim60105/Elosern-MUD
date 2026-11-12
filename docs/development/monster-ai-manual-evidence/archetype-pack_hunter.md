# Manual archetype campaign: `pack_hunter` (monster-ai-manual-evidence)

- Baseline commit: `113014bf9dae5d5b2e354f4c4afdbe61006454e2`
- Configuration fingerprint: `6c8e5bdab452aa2b15963a91978e145bec3c6642b49e2b3da46f2b8f3c58f921`
- Allocation: 24 encounters (['finishing_choice', 'area_versus_single', 'resource_exhaustion', 'mandatory_targeting', 'support_and_focus', 'long_lifecycle'] situations x 2 seeds x 2 intelligence values), round cap 30

Overall: 24 win / 0 loss / 0 capped, mean rounds 8.25 (denominator 24 encounters), highest-utility fraction 0.401, selected illegal 0.

No-action causes (legal restriction / estimator exclusion / budget omission): 0 / 0 / 0.

Target concentration over encounter-local roles: mean top-role share 0.775, 23 encounter(s) put at least half their choices on one role. Every decision's effective seed, execution identity, sampled plans, selected plan and initial observation snapshot are recorded in `raw[].decision_records`.

| situation | intelligence | win/loss/capped | mean rounds | highest-utility |
| --- | ---: | --- | ---: | ---: |
| finishing_choice | 10 | 2/0/0 | 3.00 | 0.000 |
| finishing_choice | 90 | 2/0/0 | 3.50 | 0.167 |
| area_versus_single | 10 | 2/0/0 | 9.00 | 0.235 |
| area_versus_single | 90 | 2/0/0 | 7.00 | 0.571 |
| resource_exhaustion | 10 | 2/0/0 | 8.00 | 0.067 |
| resource_exhaustion | 90 | 2/0/0 | 7.50 | 0.538 |
| mandatory_targeting | 10 | 2/0/0 | 7.50 | 0.571 |
| mandatory_targeting | 90 | 2/0/0 | 11.00 | 0.818 |
| support_and_focus | 10 | 2/0/0 | 8.00 | 0.292 |
| support_and_focus | 90 | 2/0/0 | 9.00 | 0.682 |
| long_lifecycle | 10 | 2/0/0 | 12.50 | 0.120 |
| long_lifecycle | 90 | 2/0/0 | 13.00 | 0.360 |

Unresolved (capped) encounters: 0. Two seeds per situation cannot certify balance; the acceptance claims are valid execution, replay, distinct profiles and intelligence affecting decision quality while stats stay identical.
