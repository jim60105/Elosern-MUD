# Manual selector check (monster-ai-manual-evidence)

- Baseline commit: `0970ab84a61732037cdce478c05854c66e81057c`
- Algorithm version: 5
- Configuration fingerprint: `23e711e9bb93a0c9c0e0b66a72f5c17bb4c9bb78c6693b540b34ad54b7da37ba`
- Seeds: 128 documented injected seeds at intelligence [10, 90]
- Utility gap: 0.5

| intelligence | highest-utility count | proportion | Wilson 95% |
| --- | ---: | ---: | --- |
| 10 | 74 | 0.578 | [0.492, 0.660] |
| 90 | 118 | 0.922 | [0.862, 0.957] |

Paired difference (high - low): **0.344** (required >= 0.15): met.

This is an isolated selector measurement, not an encounter win-rate result. Identical seeds, input and configuration reproduce every chosen candidate.
