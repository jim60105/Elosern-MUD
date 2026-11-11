# Manual selector check (monster-ai-manual-evidence)

- Baseline commit: `405ac3b052c64d981a69df3b1585dc4920554709`
- Algorithm version: 5
- Configuration fingerprint: `fc1dd26350fccc5b9682fe62ca632f2c12931bb53504ad9f106d35cbd8c4f64f`
- Seeds: 128 documented injected seeds at intelligence [10, 90]
- Utility gap: 0.5

| intelligence | highest-utility count | proportion | Wilson 95% |
| --- | ---: | ---: | --- |
| 10 | 74 | 0.578 | [0.492, 0.660] |
| 90 | 118 | 0.922 | [0.862, 0.957] |

Paired difference (high - low): **0.344** (required >= 0.15): met.

This is an isolated selector measurement, not an encounter win-rate result. Identical seeds, input and configuration reproduce every chosen candidate.
