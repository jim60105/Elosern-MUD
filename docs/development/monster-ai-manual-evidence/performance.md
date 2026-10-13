# Manual performance scenario (monster-ai-manual-evidence)

- Baseline commit: `79d24012656fd0eeac00df5e85495d47de4fe65c`
- Configuration fingerprint: `e40c071ef3a428c419c6ff58c9750c77b93d01d01911b3dc2f3c62f09ac20232`
- Host: `Jim-Fedora` / Linux-7.2.6-200.fc44.x86_64-x86_64-with-glibc2.43 (clock monotonic)
- Envelope: 16 participants, up to 16 owned active skills, candidate budget 256; 5 warm-ups then 50 measurements per mode, one cold call

| mode | cold ms | p50 ms | p95 ms | queries | examined | accepted | omitted | dice isolated |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| legacy | 4.10 | 0.60 | 0.77 | 10 | 0 | 0 | 0 | False |
| utility | 45.53 | 15.50 | 15.78 | 97 | 108 | 108 | 0 | True |

Warm p95 budget 50 ms: met.

| examined-proposal budget | queries | examined | accepted | omitted |
| ---: | ---: | ---: | ---: | ---: |
| 16 | 168 | 16 | 16 | 105 |
| 64 | 168 | 64 | 64 | 57 |
| 256 | 168 | 108 | 108 | 0 |

One fixed reference battlefield is probed at three examined-proposal budgets: `examined` counts every proposal the decision examined (accepted candidates, rejections and mandatory-filter exclusions) and `omitted` the proposals the budget left unexamined. Query work may scale with the initial participant/owned-skill read but never with the proposals a decision examined or omitted. This is a manual measurement on the recorded host, never a permanent timing assertion.
