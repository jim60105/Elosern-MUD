# Manual archetype campaign: `instinctive` (monster-ai-manual-evidence)

- Baseline commit: `1a141247996b5b17c28404bbd6ba058c34de3d21`
- Configuration fingerprint: `497df2c1a7427a646c531d98a89daf2273dad1abf2767b70fd25d1a4300a0e0f`
- Allocation: 24 encounters (['finishing_choice', 'area_versus_single', 'resource_exhaustion', 'mandatory_targeting', 'support_and_focus', 'long_lifecycle'] situations x 2 seeds x 2 intelligence values), round cap 30

Overall: 24 win / 0 loss / 0 capped, mean rounds 7.38 (denominator 24 encounters), highest-utility fraction 0.226, selected illegal 0.

No-action causes (legal restriction / estimator exclusion / budget omission): 0 / 0 / 0.

Target concentration over encounter-local roles: mean top-role share 0.623, 20 encounter(s) put at least half their choices on one role. Every decision's effective seed, execution identity, sampled plans, selected plan and initial observation snapshot are recorded in `raw[].decision_records`.

| situation | intelligence | win/loss/capped | mean rounds | highest-utility |
| --- | ---: | --- | ---: | ---: |
| finishing_choice | 10 | 2/0/0 | 4.50 | 0.000 |
| finishing_choice | 90 | 2/0/0 | 5.50 | 0.455 |
| area_versus_single | 10 | 2/0/0 | 7.50 | 0.133 |
| area_versus_single | 90 | 2/0/0 | 5.00 | 0.375 |
| resource_exhaustion | 10 | 2/0/0 | 8.50 | 0.062 |
| resource_exhaustion | 90 | 2/0/0 | 7.00 | 0.308 |
| mandatory_targeting | 10 | 2/0/0 | 6.50 | 0.167 |
| mandatory_targeting | 90 | 2/0/0 | 6.50 | 0.462 |
| support_and_focus | 10 | 2/0/0 | 10.50 | 0.147 |
| support_and_focus | 90 | 2/0/0 | 6.50 | 0.500 |
| long_lifecycle | 10 | 2/0/0 | 9.50 | 0.105 |
| long_lifecycle | 90 | 2/0/0 | 11.00 | 0.182 |

Unresolved (capped) encounters: 0. Two seeds per situation cannot certify balance; the acceptance claims are valid execution, replay, distinct profiles and intelligence affecting decision quality while stats stay identical.
