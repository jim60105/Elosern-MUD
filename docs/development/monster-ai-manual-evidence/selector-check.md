# Manual selector check (monster-ai-manual-evidence)

- Baseline commit: `0b0455b0ed68f61175a167f7b806f8cbbee0b4e1`
- Algorithm version: 5
- Configuration fingerprint: `237f9a85bb52bd4c1a2c6369252afbfbd57eee69ead10ebb6a0d7da6583b0f3c`
- Seeds: 128 documented injected seeds at intelligence [10, 90]
- Utility gap: 0.5

| intelligence | highest-utility count | proportion | Wilson 95% |
| --- | ---: | ---: | --- |
| 10 | 74 | 0.578 | [0.492, 0.660] |
| 90 | 118 | 0.922 | [0.862, 0.957] |

Paired difference (high - low): **0.344** (required >= 0.15): met.

This is an isolated selector measurement, not an encounter win-rate result. Identical seeds, input and configuration reproduce every chosen candidate.
