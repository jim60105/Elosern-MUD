# Manual selector check (monster-ai-manual-evidence)

- Baseline commit: `85b5a4efe7c8b34c71f94615eb9ec66b5f59dd74`
- Algorithm version: 5
- Configuration fingerprint: `8307fec88f5b243bb6ef90c24733da006873946e9f4632a2f6be36c6fae89fe6`
- Seeds: 128 documented injected seeds at intelligence [10, 90]
- Utility gap: 0.5

| intelligence | highest-utility count | proportion | Wilson 95% |
| --- | ---: | ---: | --- |
| 10 | 74 | 0.578 | [0.492, 0.660] |
| 90 | 118 | 0.922 | [0.862, 0.957] |

Paired difference (high - low): **0.344** (required >= 0.15): met.

This is an isolated selector measurement, not an encounter win-rate result. Identical seeds, input and configuration reproduce every chosen candidate.
