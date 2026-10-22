# Manual archetype campaign: `pack_hunter` (monster-ai-manual-evidence)

- Baseline commit: `4bbe4f0c9372b745b68de43c1b2ba8a552ab8ba4`
- Configuration fingerprint: `497df2c1a7427a646c531d98a89daf2273dad1abf2767b70fd25d1a4300a0e0f`
- Allocation: 24 encounters (['finishing_choice', 'area_versus_single', 'resource_exhaustion', 'mandatory_targeting', 'support_and_focus', 'long_lifecycle'] situations x 2 seeds x 2 intelligence values), round cap 30

Overall: 24 win / 0 loss / 0 capped, mean rounds 7.92 (denominator 24 encounters), highest-utility fraction 0.311, selected illegal 0.

No-action causes (legal restriction / estimator exclusion / budget omission): 0 / 0 / 0.

Target concentration over encounter-local roles: mean top-role share 0.748, 21 encounter(s) put at least half their choices on one role. Every decision's effective seed, execution identity, sampled plans, selected plan and initial observation snapshot are recorded in `raw[].decision_records`.

| situation | intelligence | win/loss/capped | mean rounds | highest-utility |
| --- | ---: | --- | ---: | ---: |
| finishing_choice | 10 | 2/0/0 | 3.50 | 0.167 |
| finishing_choice | 90 | 2/0/0 | 3.50 | 0.333 |
| area_versus_single | 10 | 2/0/0 | 7.00 | 0.231 |
| area_versus_single | 90 | 2/0/0 | 6.00 | 0.250 |
| resource_exhaustion | 10 | 2/0/0 | 9.00 | 0.278 |
| resource_exhaustion | 90 | 2/0/0 | 7.50 | 0.571 |
| mandatory_targeting | 10 | 2/0/0 | 8.00 | 0.438 |
| mandatory_targeting | 90 | 2/0/0 | 9.00 | 0.833 |
| support_and_focus | 10 | 2/0/0 | 8.00 | 0.143 |
| support_and_focus | 90 | 2/0/0 | 8.00 | 0.333 |
| long_lifecycle | 10 | 2/0/0 | 12.50 | 0.040 |
| long_lifecycle | 90 | 2/0/0 | 13.00 | 0.231 |

Unresolved (capped) encounters: 0. Two seeds per situation cannot certify balance; the acceptance claims are valid execution, replay, distinct profiles and intelligence affecting decision quality while stats stay identical.
