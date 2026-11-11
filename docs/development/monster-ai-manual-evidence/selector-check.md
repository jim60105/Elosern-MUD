# Manual selector check (monster-ai-manual-evidence)

- Baseline commit: `5ed54e47e89bbe99b6118d9b5999657e094008c1`
- Algorithm version: 5
- Configuration fingerprint: `3232b667996417f09624c159fa191e36bd88b5597b0ae4f07efeef2a2c7ac487`
- Seeds: 128 documented injected seeds at intelligence [10, 90]
- Utility gap: 0.5

| intelligence | highest-utility count | proportion | Wilson 95% |
| --- | ---: | ---: | --- |
| 10 | 74 | 0.578 | [0.492, 0.660] |
| 90 | 118 | 0.922 | [0.862, 0.957] |

Paired difference (high - low): **0.344** (required >= 0.15): met.

This is an isolated selector measurement, not an encounter win-rate result. Identical seeds, input and configuration reproduce every chosen candidate.
