# Manual archetype campaign: `apex_predator` (monster-ai-manual-evidence)

- Baseline commit: `ab8b457ddc4265482766d601d99a6555e3f88e82`
- Configuration fingerprint: `e40c071ef3a428c419c6ff58c9750c77b93d01d01911b3dc2f3c62f09ac20232`
- Allocation: 24 encounters (['finishing_choice', 'area_versus_single', 'resource_exhaustion', 'mandatory_targeting', 'support_and_focus', 'long_lifecycle'] situations x 2 seeds x 2 intelligence values), round cap 30

Overall: 24 win / 0 loss / 0 capped, mean rounds 8.42 (denominator 24 encounters), highest-utility fraction 0.370, selected illegal 0.

No-action causes (legal restriction / estimator exclusion / budget omission): 0 / 0 / 0.

Target concentration over encounter-local roles: mean top-role share 0.746, 21 encounter(s) put at least half their choices on one role. Every decision's effective seed, execution identity, sampled plans, selected plan and initial observation snapshot are recorded in `raw[].decision_records`.

| situation | intelligence | win/loss/capped | mean rounds | highest-utility |
| --- | ---: | --- | ---: | ---: |
| finishing_choice | 10 | 2/0/0 | 4.00 | 0.143 |
| finishing_choice | 90 | 2/0/0 | 4.00 | 0.143 |
| area_versus_single | 10 | 2/0/0 | 8.00 | 0.188 |
| area_versus_single | 90 | 2/0/0 | 8.50 | 0.438 |
| resource_exhaustion | 10 | 2/0/0 | 7.50 | 0.500 |
| resource_exhaustion | 90 | 2/0/0 | 7.50 | 0.857 |
| mandatory_targeting | 10 | 2/0/0 | 5.50 | 0.333 |
| mandatory_targeting | 90 | 2/0/0 | 6.50 | 0.667 |
| support_and_focus | 10 | 2/0/0 | 10.00 | 0.182 |
| support_and_focus | 90 | 2/0/0 | 11.50 | 0.686 |
| long_lifecycle | 10 | 2/0/0 | 15.00 | 0.034 |
| long_lifecycle | 90 | 2/0/0 | 13.00 | 0.292 |

Unresolved (capped) encounters: 0. Two seeds per situation cannot certify balance; the acceptance claims are valid execution, replay, distinct profiles and intelligence affecting decision quality while stats stay identical.
