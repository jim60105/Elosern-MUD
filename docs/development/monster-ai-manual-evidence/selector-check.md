# Manual selector check (monster-ai-manual-evidence)

- Baseline commit: `b456b01aec47e6f19567d4f3e9f1d17e98ac136c`
- Algorithm version: 5
- Configuration fingerprint: `bd82767e08a1857878c6f2802a81a5cd9ff5b88f42b90a2dca76a2cbdbb66ed5`
- Seeds: 128 documented injected seeds at intelligence [10, 90]
- Utility gap: 0.5

| intelligence | highest-utility count | proportion | Wilson 95% |
| --- | ---: | ---: | --- |
| 10 | 74 | 0.578 | [0.492, 0.660] |
| 90 | 118 | 0.922 | [0.862, 0.957] |

Paired difference (high - low): **0.344** (required >= 0.15): met.

This is an isolated selector measurement, not an encounter win-rate result. Identical seeds, input and configuration reproduce every chosen candidate.
