# Manual archetype campaign: `ambush_predator` (monster-ai-manual-evidence)

- Baseline commit: `4bbe4f0c9372b745b68de43c1b2ba8a552ab8ba4`
- Configuration fingerprint: `497df2c1a7427a646c531d98a89daf2273dad1abf2767b70fd25d1a4300a0e0f`
- Allocation: 24 encounters (['finishing_choice', 'area_versus_single', 'resource_exhaustion', 'mandatory_targeting', 'support_and_focus', 'long_lifecycle'] situations x 2 seeds x 2 intelligence values), round cap 30

Overall: 24 win / 0 loss / 0 capped, mean rounds 7.54 (denominator 24 encounters), highest-utility fraction 0.362, selected illegal 0.

No-action causes (legal restriction / estimator exclusion / budget omission): 0 / 0 / 0.

Target concentration over encounter-local roles: mean top-role share 0.701, 21 encounter(s) put at least half their choices on one role. Every decision's effective seed, execution identity, sampled plans, selected plan and initial observation snapshot are recorded in `raw[].decision_records`.

| situation | intelligence | win/loss/capped | mean rounds | highest-utility |
| --- | ---: | --- | ---: | ---: |
| finishing_choice | 10 | 2/0/0 | 4.00 | 0.000 |
| finishing_choice | 90 | 2/0/0 | 5.50 | 0.273 |
| area_versus_single | 10 | 2/0/0 | 5.50 | 0.182 |
| area_versus_single | 90 | 2/0/0 | 5.50 | 0.364 |
| resource_exhaustion | 10 | 2/0/0 | 9.50 | 0.158 |
| resource_exhaustion | 90 | 2/0/0 | 11.00 | 0.364 |
| mandatory_targeting | 10 | 2/0/0 | 6.50 | 0.231 |
| mandatory_targeting | 90 | 2/0/0 | 7.50 | 0.643 |
| support_and_focus | 10 | 2/0/0 | 6.00 | 0.214 |
| support_and_focus | 90 | 2/0/0 | 10.00 | 0.630 |
| long_lifecycle | 10 | 2/0/0 | 9.00 | 0.333 |
| long_lifecycle | 90 | 2/0/0 | 10.50 | 0.476 |

Unresolved (capped) encounters: 0. Two seeds per situation cannot certify balance; the acceptance claims are valid execution, replay, distinct profiles and intelligence affecting decision quality while stats stay identical.
