# Manual selector check (monster-ai-manual-evidence)

- Baseline commit: `d91de59c9719089ca80f8d2da80eb0b8a3e1e398`
- Algorithm version: 5
- Configuration fingerprint: `f8858072f828d4a5988f0391333ba07ab2d8ad21a34956e39a29afec50d3f8b2`
- Seeds: 128 documented injected seeds at intelligence [10, 90]
- Utility gap: 0.5

| intelligence | highest-utility count | proportion | Wilson 95% |
| --- | ---: | ---: | --- |
| 10 | 74 | 0.578 | [0.492, 0.660] |
| 90 | 118 | 0.922 | [0.862, 0.957] |

Paired difference (high - low): **0.344** (required >= 0.15): met.

This is an isolated selector measurement, not an encounter win-rate result. Identical seeds, input and configuration reproduce every chosen candidate.
