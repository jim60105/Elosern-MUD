# Manual selector check (monster-ai-manual-evidence)

- Baseline commit: `14b4dff09b06852b8e0dcec126de0f50a50c8b45`
- Algorithm version: 5
- Configuration fingerprint: `e583cb956f90c0827c6c04526c6001238b93a85673d4a0bce941fa9b48e535f4`
- Seeds: 128 documented injected seeds at intelligence [10, 90]
- Utility gap: 0.5

| intelligence | highest-utility count | proportion | Wilson 95% |
| --- | ---: | ---: | --- |
| 10 | 74 | 0.578 | [0.492, 0.660] |
| 90 | 118 | 0.922 | [0.862, 0.957] |

Paired difference (high - low): **0.344** (required >= 0.15): met.

This is an isolated selector measurement, not an encounter win-rate result. Identical seeds, input and configuration reproduce every chosen candidate.
