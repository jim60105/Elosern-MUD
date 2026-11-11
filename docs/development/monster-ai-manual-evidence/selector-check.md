# Manual selector check (monster-ai-manual-evidence)

- Baseline commit: `ae9185c95610f3b6f793bf9105a7b65c2e182d68`
- Algorithm version: 5
- Configuration fingerprint: `2a04e1bc0d7c054ecd16a46ea8721acf3aeb9cae60563b4470792a9ece508325`
- Seeds: 128 documented injected seeds at intelligence [10, 90]
- Utility gap: 0.5

| intelligence | highest-utility count | proportion | Wilson 95% |
| --- | ---: | ---: | --- |
| 10 | 74 | 0.578 | [0.492, 0.660] |
| 90 | 118 | 0.922 | [0.862, 0.957] |

Paired difference (high - low): **0.344** (required >= 0.15): met.

This is an isolated selector measurement, not an encounter win-rate result. Identical seeds, input and configuration reproduce every chosen candidate.
