# Manual selector check (monster-ai-manual-evidence)

- Baseline commit: `afe99b823f5a3de1291a2623ea274f9283f99cf5`
- Algorithm version: 5
- Configuration fingerprint: `70e5f38ddf230967499968edfce2efa54d1bc7b836f68fdf2eac882b809b9de0`
- Seeds: 128 documented injected seeds at intelligence [10, 90]
- Utility gap: 0.5

| intelligence | highest-utility count | proportion | Wilson 95% |
| --- | ---: | ---: | --- |
| 10 | 74 | 0.578 | [0.492, 0.660] |
| 90 | 118 | 0.922 | [0.862, 0.957] |

Paired difference (high - low): **0.344** (required >= 0.15): met.

This is an isolated selector measurement, not an encounter win-rate result. Identical seeds, input and configuration reproduce every chosen candidate.
