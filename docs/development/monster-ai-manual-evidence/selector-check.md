# Manual selector check (monster-ai-manual-evidence)

- Baseline commit: `55aad3ec1c59fdd86340b50104a973b565c91b73`
- Algorithm version: 5
- Configuration fingerprint: `3c18cea173ab18d4ffeca113d9aa73ef8523519e13abf99075cbc4d3382b719f`
- Seeds: 128 documented injected seeds at intelligence [10, 90]
- Utility gap: 0.5

| intelligence | highest-utility count | proportion | Wilson 95% |
| --- | ---: | ---: | --- |
| 10 | 74 | 0.578 | [0.492, 0.660] |
| 90 | 118 | 0.922 | [0.862, 0.957] |

Paired difference (high - low): **0.344** (required >= 0.15): met.

This is an isolated selector measurement, not an encounter win-rate result. Identical seeds, input and configuration reproduce every chosen candidate.
