# Manual archetype campaign: `instinctive` (monster-ai-manual-evidence)

- Baseline commit: `79d24012656fd0eeac00df5e85495d47de4fe65c`
- Configuration fingerprint: `e40c071ef3a428c419c6ff58c9750c77b93d01d01911b3dc2f3c62f09ac20232`
- Allocation: 24 encounters (['finishing_choice', 'area_versus_single', 'resource_exhaustion', 'mandatory_targeting', 'support_and_focus', 'long_lifecycle'] situations x 2 seeds x 2 intelligence values), round cap 30

Overall: 24 win / 0 loss / 0 capped, mean rounds 8.71 (denominator 24 encounters), highest-utility fraction 0.240, selected illegal 0.

No-action causes (legal restriction / estimator exclusion / budget omission): 0 / 0 / 0.

Target concentration over encounter-local roles: mean top-role share 0.694, 22 encounter(s) put at least half their choices on one role. Every decision's effective seed, execution identity, sampled plans, selected plan and initial observation snapshot are recorded in `raw[].decision_records`.

| situation | intelligence | win/loss/capped | mean rounds | highest-utility |
| --- | ---: | --- | ---: | ---: |
| finishing_choice | 10 | 2/0/0 | 5.50 | 0.200 |
| finishing_choice | 90 | 2/0/0 | 5.50 | 0.182 |
| area_versus_single | 10 | 2/0/0 | 8.00 | 0.067 |
| area_versus_single | 90 | 2/0/0 | 8.50 | 0.312 |
| resource_exhaustion | 10 | 2/0/0 | 12.00 | 0.261 |
| resource_exhaustion | 90 | 2/0/0 | 8.00 | 0.500 |
| mandatory_targeting | 10 | 2/0/0 | 6.50 | 0.000 |
| mandatory_targeting | 90 | 2/0/0 | 6.00 | 0.000 |
| support_and_focus | 10 | 2/0/0 | 5.50 | 0.000 |
| support_and_focus | 90 | 2/0/0 | 9.50 | 0.400 |
| long_lifecycle | 10 | 2/0/0 | 17.50 | 0.206 |
| long_lifecycle | 90 | 2/0/0 | 12.00 | 0.435 |

Unresolved (capped) encounters: 0. Two seeds per situation cannot certify balance; the acceptance claims are valid execution, replay, distinct profiles and intelligence affecting decision quality while stats stay identical.
