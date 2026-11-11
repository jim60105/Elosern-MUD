# Manual selector check (monster-ai-manual-evidence)

- Baseline commit: `deed3d8259860bc0e77da0655c0393085400f0e1`
- Algorithm version: 5
- Configuration fingerprint: `cd78725a5a37ad80718d6aefebb4e3dc072bf280dcf5f86f80568600f8421a09`
- Seeds: 128 documented injected seeds at intelligence [10, 90]
- Utility gap: 0.5

| intelligence | highest-utility count | proportion | Wilson 95% |
| --- | ---: | ---: | --- |
| 10 | 74 | 0.578 | [0.492, 0.660] |
| 90 | 118 | 0.922 | [0.862, 0.957] |

Paired difference (high - low): **0.344** (required >= 0.15): met.

This is an isolated selector measurement, not an encounter win-rate result. Identical seeds, input and configuration reproduce every chosen candidate.
