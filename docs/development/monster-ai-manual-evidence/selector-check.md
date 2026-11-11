# Manual selector check (monster-ai-manual-evidence)

- Baseline commit: `ed1d2a995dcb9e038238397adf35ea8a92bfd121`
- Algorithm version: 5
- Configuration fingerprint: `d65909aa07359fd79c449b260a1604ef4a097ff81412ed1f743758b8e62d3931`
- Seeds: 128 documented injected seeds at intelligence [10, 90]
- Utility gap: 0.5

| intelligence | highest-utility count | proportion | Wilson 95% |
| --- | ---: | ---: | --- |
| 10 | 74 | 0.578 | [0.492, 0.660] |
| 90 | 118 | 0.922 | [0.862, 0.957] |

Paired difference (high - low): **0.344** (required >= 0.15): met.

This is an isolated selector measurement, not an encounter win-rate result. Identical seeds, input and configuration reproduce every chosen candidate.
