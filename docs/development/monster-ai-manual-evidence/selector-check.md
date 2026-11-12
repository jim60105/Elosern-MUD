# Manual selector check (monster-ai-manual-evidence)

- Baseline commit: `18141b8a4fde04548737370ec3ccbb21a422a524`
- Algorithm version: 5
- Configuration fingerprint: `7c1cafd74c86871c493ac3951a0468191378bcdc37d3c18c3bc5ba719e6eddb1`
- Seeds: 128 documented injected seeds at intelligence [10, 90]
- Utility gap: 0.5

| intelligence | highest-utility count | proportion | Wilson 95% |
| --- | ---: | ---: | --- |
| 10 | 74 | 0.578 | [0.492, 0.660] |
| 90 | 118 | 0.922 | [0.862, 0.957] |

Paired difference (high - low): **0.344** (required >= 0.15): met.

This is an isolated selector measurement, not an encounter win-rate result. Identical seeds, input and configuration reproduce every chosen candidate.
