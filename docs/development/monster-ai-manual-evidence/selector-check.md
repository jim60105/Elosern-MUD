# Manual selector check (monster-ai-manual-evidence)

- Baseline commit: `a06f418d4cfda0aa5a222e4727ca7daa6c1fb86f`
- Algorithm version: 5
- Configuration fingerprint: `75b74aa1c9dc69ca58bfc5a63cc3afe1209190f7d0f5c941c71538789eed154c`
- Seeds: 128 documented injected seeds at intelligence [10, 90]
- Utility gap: 0.5

| intelligence | highest-utility count | proportion | Wilson 95% |
| --- | ---: | ---: | --- |
| 10 | 74 | 0.578 | [0.492, 0.660] |
| 90 | 118 | 0.922 | [0.862, 0.957] |

Paired difference (high - low): **0.344** (required >= 0.15): met.

This is an isolated selector measurement, not an encounter win-rate result. Identical seeds, input and configuration reproduce every chosen candidate.
