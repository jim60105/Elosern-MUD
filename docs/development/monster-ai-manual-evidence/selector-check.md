# Manual selector check (monster-ai-manual-evidence)

- Baseline commit: `2750fd0316d725a33b92836a8fc5c5a7db1f940a`
- Algorithm version: 5
- Configuration fingerprint: `5f4a45066c0f3fb8f1e8afe081d2fc0cef9a97757f41172f0b4da0f3df1d26ee`
- Seeds: 128 documented injected seeds at intelligence [10, 90]
- Utility gap: 0.5

| intelligence | highest-utility count | proportion | Wilson 95% |
| --- | ---: | ---: | --- |
| 10 | 74 | 0.578 | [0.492, 0.660] |
| 90 | 118 | 0.922 | [0.862, 0.957] |

Paired difference (high - low): **0.344** (required >= 0.15): met.

This is an isolated selector measurement, not an encounter win-rate result. Identical seeds, input and configuration reproduce every chosen candidate.
