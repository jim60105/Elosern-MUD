# Manual selector check (monster-ai-manual-evidence)

- Baseline commit: `addec86009eb6aee2d3e797cb2935e2434cd509e`
- Algorithm version: 5
- Configuration fingerprint: `b0dd9da6a87878909c04036f3742f485dd8154599837f90aff18f2e26ed241b0`
- Seeds: 128 documented injected seeds at intelligence [10, 90]
- Utility gap: 0.5

| intelligence | highest-utility count | proportion | Wilson 95% |
| --- | ---: | ---: | --- |
| 10 | 74 | 0.578 | [0.492, 0.660] |
| 90 | 118 | 0.922 | [0.862, 0.957] |

Paired difference (high - low): **0.344** (required >= 0.15): met.

This is an isolated selector measurement, not an encounter win-rate result. Identical seeds, input and configuration reproduce every chosen candidate.
