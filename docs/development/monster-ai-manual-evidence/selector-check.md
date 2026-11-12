# Manual selector check (monster-ai-manual-evidence)

- Baseline commit: `113014bf9dae5d5b2e354f4c4afdbe61006454e2`
- Algorithm version: 6
- Configuration fingerprint: `5b46ee570d95fc99507b303509e634f9387830a4a7fa87249d23a1d05bb9fba3`
- Seeds: 128 documented injected seeds at intelligence [10, 90]
- Utility gap: 0.5

| intelligence | highest-utility count | proportion | Wilson 95% |
| --- | ---: | ---: | --- |
| 10 | 74 | 0.578 | [0.492, 0.660] |
| 90 | 118 | 0.922 | [0.862, 0.957] |

Paired difference (high - low): **0.344** (required >= 0.15): met.

This is an isolated selector measurement, not an encounter win-rate result. Identical seeds, input and configuration reproduce every chosen candidate.
