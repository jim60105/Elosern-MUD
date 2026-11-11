# Manual selector check (monster-ai-manual-evidence)

- Baseline commit: `7166e6bb5b8716aee3b6cff88c6e1ff5c5ca3995`
- Algorithm version: 5
- Configuration fingerprint: `ef4b4b1463e46c6346330aaae183c463a69071008c1f12509260aaecdb830061`
- Seeds: 128 documented injected seeds at intelligence [10, 90]
- Utility gap: 0.5

| intelligence | highest-utility count | proportion | Wilson 95% |
| --- | ---: | ---: | --- |
| 10 | 74 | 0.578 | [0.492, 0.660] |
| 90 | 118 | 0.922 | [0.862, 0.957] |

Paired difference (high - low): **0.344** (required >= 0.15): met.

This is an isolated selector measurement, not an encounter win-rate result. Identical seeds, input and configuration reproduce every chosen candidate.
