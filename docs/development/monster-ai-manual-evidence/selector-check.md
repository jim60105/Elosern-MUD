# Manual selector check (monster-ai-manual-evidence)

- Baseline commit: `78b2c12237c83ffcd229155f053caee4dcf35725`
- Algorithm version: 5
- Configuration fingerprint: `c4d4e06bbfab806742fc083296a11ef8109c85d15c894ca043d76ef76a000f85`
- Seeds: 128 documented injected seeds at intelligence [10, 90]
- Utility gap: 0.5

| intelligence | highest-utility count | proportion | Wilson 95% |
| --- | ---: | ---: | --- |
| 10 | 74 | 0.578 | [0.492, 0.660] |
| 90 | 118 | 0.922 | [0.862, 0.957] |

Paired difference (high - low): **0.344** (required >= 0.15): met.

This is an isolated selector measurement, not an encounter win-rate result. Identical seeds, input and configuration reproduce every chosen candidate.
