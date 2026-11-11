# Manual selector check (monster-ai-manual-evidence)

- Baseline commit: `b088075a92cd000667cdcb6fef99bb6e989dc557`
- Algorithm version: 5
- Configuration fingerprint: `03ad9da4aa620172110103e7a7f097fd77571c0b521ec38d6335105baa40da3c`
- Seeds: 128 documented injected seeds at intelligence [10, 90]
- Utility gap: 0.5

| intelligence | highest-utility count | proportion | Wilson 95% |
| --- | ---: | ---: | --- |
| 10 | 74 | 0.578 | [0.492, 0.660] |
| 90 | 118 | 0.922 | [0.862, 0.957] |

Paired difference (high - low): **0.344** (required >= 0.15): met.

This is an isolated selector measurement, not an encounter win-rate result. Identical seeds, input and configuration reproduce every chosen candidate.
