# Manual performance scenario (monster-ai-manual-evidence)

- Baseline commit: `4bbe4f0c9372b745b68de43c1b2ba8a552ab8ba4`
- Configuration fingerprint: `497df2c1a7427a646c531d98a89daf2273dad1abf2767b70fd25d1a4300a0e0f`
- Host: `Jim-Fedora` / Linux-7.2.6-200.fc44.x86_64-x86_64-with-glibc2.43 (clock monotonic)
- Envelope: 16 participants, up to 16 owned active skills, candidate budget 256; 5 warm-ups then 50 measurements per mode, one cold call

| mode | cold ms | p50 ms | p95 ms | queries | examined | accepted | omitted | dice isolated |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| legacy | 3.96 | 0.59 | 0.77 | 10 | 0 | 0 | 0 | False |
| utility | 46.00 | 16.36 | 16.84 | 97 | 108 | 108 | 0 | True |

Warm p95 budget 50 ms: met.

| examined-proposal budget | queries | examined | accepted | omitted |
| ---: | ---: | ---: | ---: | ---: |
| 16 | 200 | 16 | 16 | 105 |
| 64 | 200 | 64 | 64 | 57 |
| 256 | 200 | 108 | 108 | 0 |

One fixed reference battlefield is probed at three examined-proposal budgets: `examined` counts every proposal the decision examined (accepted candidates, rejections and mandatory-filter exclusions) and `omitted` the proposals the budget left unexamined. Query work may scale with the initial participant/owned-skill read but never with the proposals a decision examined or omitted. This is a manual measurement on the recorded host, never a permanent timing assertion.
