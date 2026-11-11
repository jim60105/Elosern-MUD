# Manual selector check (monster-ai-manual-evidence)

- Baseline commit: `8a6ee19d6824a7d44880e1ea581bde4a6aafb1c1`
- Algorithm version: 5
- Configuration fingerprint: `5828d932852713e93ad6fa61e3ca8ac6b6469dc64889d435d8420780c5985120`
- Seeds: 128 documented injected seeds at intelligence [10, 90]
- Utility gap: 0.5

| intelligence | highest-utility count | proportion | Wilson 95% |
| --- | ---: | ---: | --- |
| 10 | 74 | 0.578 | [0.492, 0.660] |
| 90 | 118 | 0.922 | [0.862, 0.957] |

Paired difference (high - low): **0.344** (required >= 0.15): met.

This is an isolated selector measurement, not an encounter win-rate result. Identical seeds, input and configuration reproduce every chosen candidate.
