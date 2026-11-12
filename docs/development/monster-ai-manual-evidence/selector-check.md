# Manual selector check (monster-ai-manual-evidence)

- Baseline commit: `40866b9cf647bfb75702ab8a820683959c36a2b5`
- Algorithm version: 5
- Configuration fingerprint: `383b1eff83cbae5592a5ea4ba2998249ecb95a024582c76b8a74e99bcc4436af`
- Seeds: 128 documented injected seeds at intelligence [10, 90]
- Utility gap: 0.5

| intelligence | highest-utility count | proportion | Wilson 95% |
| --- | ---: | ---: | --- |
| 10 | 74 | 0.578 | [0.492, 0.660] |
| 90 | 118 | 0.922 | [0.862, 0.957] |

Paired difference (high - low): **0.344** (required >= 0.15): met.

This is an isolated selector measurement, not an encounter win-rate result. Identical seeds, input and configuration reproduce every chosen candidate.
