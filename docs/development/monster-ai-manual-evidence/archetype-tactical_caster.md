# Manual archetype campaign: `tactical_caster` (monster-ai-manual-evidence)

- Baseline commit: `143b28d6f2cb07090f88753eacd4ea0c32e0246c`
- Configuration fingerprint: `e40c071ef3a428c419c6ff58c9750c77b93d01d01911b3dc2f3c62f09ac20232`
- Allocation: 24 encounters (['finishing_choice', 'area_versus_single', 'resource_exhaustion', 'mandatory_targeting', 'support_and_focus', 'long_lifecycle'] situations x 2 seeds x 2 intelligence values), round cap 30

Overall: 20 win / 0 loss / 4 capped, mean rounds 6.96 (denominator 24 encounters), highest-utility fraction 0.446, selected illegal 0.

No-action causes (legal restriction / estimator exclusion / budget omission): 0 / 0 / 0.

| situation | intelligence | win/loss/capped | mean rounds | highest-utility |
| --- | ---: | --- | ---: | ---: |
| finishing_choice | 10 | 2/0/0 | 7.00 | 0.308 |
| finishing_choice | 90 | 2/0/0 | 6.00 | 0.300 |
| area_versus_single | 10 | 2/0/0 | 6.00 | 0.182 |
| area_versus_single | 90 | 2/0/0 | 4.00 | 0.375 |
| resource_exhaustion | 10 | 2/0/0 | 7.00 | 0.769 |
| resource_exhaustion | 90 | 2/0/0 | 2.50 | 0.750 |
| mandatory_targeting | 10 | 2/0/0 | 5.00 | 0.333 |
| mandatory_targeting | 90 | 2/0/0 | 6.00 | 0.273 |
| support_and_focus | 10 | 0/0/2 | 8.00 | 0.429 |
| support_and_focus | 90 | 0/0/2 | 5.50 | 0.722 |
| long_lifecycle | 10 | 2/0/0 | 9.00 | 0.375 |
| long_lifecycle | 90 | 2/0/0 | 17.50 | 0.471 |

Unresolved (capped) encounters: 4. Two seeds per situation cannot certify balance; the acceptance claims are valid execution, replay, distinct profiles and intelligence affecting decision quality while stats stay identical.
