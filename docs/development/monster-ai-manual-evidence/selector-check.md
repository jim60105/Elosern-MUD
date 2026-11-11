# Manual selector check (monster-ai-manual-evidence)

- Baseline commit: `f5d411ede5c0fe2ac18bb1f0c2b6024e07c5dd26`
- Algorithm version: 5
- Configuration fingerprint: `abb0989cb3679b72ccb2195808ab04e9b863315369316dd68721de9d6f7b54fc`
- Seeds: 128 documented injected seeds at intelligence [10, 90]
- Utility gap: 0.5

| intelligence | highest-utility count | proportion | Wilson 95% |
| --- | ---: | ---: | --- |
| 10 | 74 | 0.578 | [0.492, 0.660] |
| 90 | 118 | 0.922 | [0.862, 0.957] |

Paired difference (high - low): **0.344** (required >= 0.15): met.

This is an isolated selector measurement, not an encounter win-rate result. Identical seeds, input and configuration reproduce every chosen candidate.
