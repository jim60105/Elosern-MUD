# Manual selector check (monster-ai-manual-evidence)

- Baseline commit: `fb4eafeaa431473f3f23f854c8591831266657bd`
- Algorithm version: 5
- Configuration fingerprint: `3030d4a397f1bfd4ee264c129cf8bf133925982db8b005e881639e8f964a3f27`
- Seeds: 128 documented injected seeds at intelligence [10, 90]
- Utility gap: 0.5

| intelligence | highest-utility count | proportion | Wilson 95% |
| --- | ---: | ---: | --- |
| 10 | 74 | 0.578 | [0.492, 0.660] |
| 90 | 118 | 0.922 | [0.862, 0.957] |

Paired difference (high - low): **0.344** (required >= 0.15): met.

This is an isolated selector measurement, not an encounter win-rate result. Identical seeds, input and configuration reproduce every chosen candidate.
