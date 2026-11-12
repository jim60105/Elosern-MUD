# Manual selector check (monster-ai-manual-evidence)

- Baseline commit: `1088d7e1c19c2c0ce66639e9b1c68026511b9bb8`
- Algorithm version: 5
- Configuration fingerprint: `8b56d98c1221048d0ea7a4dc39dc5613cdafbf692e78d895204456ae464e9968`
- Seeds: 128 documented injected seeds at intelligence [10, 90]
- Utility gap: 0.5

| intelligence | highest-utility count | proportion | Wilson 95% |
| --- | ---: | ---: | --- |
| 10 | 74 | 0.578 | [0.492, 0.660] |
| 90 | 118 | 0.922 | [0.862, 0.957] |

Paired difference (high - low): **0.344** (required >= 0.15): met.

This is an isolated selector measurement, not an encounter win-rate result. Identical seeds, input and configuration reproduce every chosen candidate.
