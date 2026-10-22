# Manual selector check (monster-ai-manual-evidence)

- Baseline commit: `42692a02afa4c9d06eef58d797542ac27fb42b01`
- Algorithm version: 5
- Configuration fingerprint: `e2677d39e27adff0bc12f19478fe552a83d65695e0bcb8f6b5aa6273986c9866`
- Seeds: 128 documented injected seeds at intelligence [10, 90]
- Utility gap: 0.5

| intelligence | highest-utility count | proportion | Wilson 95% |
| --- | ---: | ---: | --- |
| 10 | 74 | 0.578 | [0.492, 0.660] |
| 90 | 118 | 0.922 | [0.862, 0.957] |

Paired difference (high - low): **0.344** (required >= 0.15): met.

This is an isolated selector measurement, not an encounter win-rate result. Identical seeds, input and configuration reproduce every chosen candidate.
