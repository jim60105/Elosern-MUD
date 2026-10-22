# Manual archetype campaign: `tactical_caster` (monster-ai-manual-evidence)

- Baseline commit: `4bbe4f0c9372b745b68de43c1b2ba8a552ab8ba4`
- Configuration fingerprint: `497df2c1a7427a646c531d98a89daf2273dad1abf2767b70fd25d1a4300a0e0f`
- Allocation: 24 encounters (['finishing_choice', 'area_versus_single', 'resource_exhaustion', 'mandatory_targeting', 'support_and_focus', 'long_lifecycle'] situations x 2 seeds x 2 intelligence values), round cap 30

Overall: 24 win / 0 loss / 0 capped, mean rounds 8.21 (denominator 24 encounters), highest-utility fraction 0.309, selected illegal 0.

No-action causes (legal restriction / estimator exclusion / budget omission): 0 / 0 / 0.

Target concentration over encounter-local roles: mean top-role share 0.739, 21 encounter(s) put at least half their choices on one role. Every decision's effective seed, execution identity, sampled plans, selected plan and initial observation snapshot are recorded in `raw[].decision_records`.

| situation | intelligence | win/loss/capped | mean rounds | highest-utility |
| --- | ---: | --- | ---: | ---: |
| finishing_choice | 10 | 2/0/0 | 8.50 | 0.067 |
| finishing_choice | 90 | 2/0/0 | 5.50 | 0.273 |
| area_versus_single | 10 | 2/0/0 | 6.00 | 0.091 |
| area_versus_single | 90 | 2/0/0 | 6.50 | 0.308 |
| resource_exhaustion | 10 | 2/0/0 | 13.00 | 0.292 |
| resource_exhaustion | 90 | 2/0/0 | 7.00 | 0.615 |
| mandatory_targeting | 10 | 2/0/0 | 5.00 | 0.333 |
| mandatory_targeting | 90 | 2/0/0 | 5.50 | 0.900 |
| support_and_focus | 10 | 2/0/0 | 6.50 | 0.143 |
| support_and_focus | 90 | 2/0/0 | 8.00 | 0.440 |
| long_lifecycle | 10 | 2/0/0 | 14.00 | 0.185 |
| long_lifecycle | 90 | 2/0/0 | 13.00 | 0.320 |

Unresolved (capped) encounters: 0. Two seeds per situation cannot certify balance; the acceptance claims are valid execution, replay, distinct profiles and intelligence affecting decision quality while stats stay identical.
