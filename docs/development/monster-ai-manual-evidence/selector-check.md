# Manual selector check (monster-ai-manual-evidence)

- Baseline commit: `a67fdee7bd0b5ecae61ce40098d816e5526b15ba`
- Algorithm version: 5
- Configuration fingerprint: `3ee653b92c6865128e8e6a3d3bbfb7ea486286aafdc9c0d9c607392a22f3323d`
- Seeds: 128 documented injected seeds at intelligence [10, 90]
- Utility gap: 0.5

| intelligence | highest-utility count | proportion | Wilson 95% |
| --- | ---: | ---: | --- |
| 10 | 74 | 0.578 | [0.492, 0.660] |
| 90 | 118 | 0.922 | [0.862, 0.957] |

Paired difference (high - low): **0.344** (required >= 0.15): met.

This is an isolated selector measurement, not an encounter win-rate result. Identical seeds, input and configuration reproduce every chosen candidate.
