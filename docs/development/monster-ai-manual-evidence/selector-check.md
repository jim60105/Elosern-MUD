# Manual selector check (monster-ai-manual-evidence)

- Baseline commit: `95cb8f923b478c581a1a5c795ede8b051206c1fc`
- Algorithm version: 5
- Configuration fingerprint: `955832b54374c54e1eb1934a3f72fb0a167c40fe7dbbd13c422115b75805507a`
- Seeds: 128 documented injected seeds at intelligence [10, 90]
- Utility gap: 0.5

| intelligence | highest-utility count | proportion | Wilson 95% |
| --- | ---: | ---: | --- |
| 10 | 74 | 0.578 | [0.492, 0.660] |
| 90 | 118 | 0.922 | [0.862, 0.957] |

Paired difference (high - low): **0.344** (required >= 0.15): met.

This is an isolated selector measurement, not an encounter win-rate result. Identical seeds, input and configuration reproduce every chosen candidate.
