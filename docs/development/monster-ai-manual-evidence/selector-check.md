# Manual selector check (monster-ai-manual-evidence)

- Baseline commit: `143b28d6f2cb07090f88753eacd4ea0c32e0246c`
- Algorithm version: 5
- Configuration fingerprint: `a29fd4fac5f07d65eb40377ee4dafe400c977738a321e8028852c9169cefe9c4`
- Seeds: 128 documented injected seeds at intelligence [10, 90]
- Utility gap: 0.5

| intelligence | highest-utility count | proportion | Wilson 95% |
| --- | ---: | ---: | --- |
| 10 | 74 | 0.578 | [0.492, 0.660] |
| 90 | 118 | 0.922 | [0.862, 0.957] |

Paired difference (high - low): **0.344** (required >= 0.15): met.

This is an isolated selector measurement, not an encounter win-rate result. Identical seeds, input and configuration reproduce every chosen candidate.
