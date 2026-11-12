# Manual performance scenario (monster-ai-manual-evidence)

- Baseline commit: `113014bf9dae5d5b2e354f4c4afdbe61006454e2`
- Configuration fingerprint: `6c8e5bdab452aa2b15963a91978e145bec3c6642b49e2b3da46f2b8f3c58f921`
- Host: `Jim-Fedora` / Linux-7.2.15-200.fc44.x86_64-x86_64-with-glibc2.43 (clock monotonic)
- Envelope: 16 participants, up to 16 owned active skills, candidate budget 256; 5 warm-ups then 50 measurements per mode, one cold call

| mode | cold ms | p50 ms | p95 ms | queries | examined | accepted | omitted | dice isolated |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| reflex | 3.96 | 0.60 | 0.77 | 10 | 0 | 0 | 0 | False |
| deliberation | 46.81 | 16.86 | 17.18 | 97 | 108 | 108 | 0 | True |

Warm p95 budget 50 ms: met.

| examined-proposal budget | queries | examined | accepted | omitted |
| ---: | ---: | ---: | ---: | ---: |
| 16 | 200 | 16 | 16 | 105 |
| 64 | 200 | 64 | 64 | 57 |
| 256 | 200 | 108 | 108 | 0 |

One fixed reference battlefield is probed at three examined-proposal budgets: `examined` counts every proposal the decision examined (accepted candidates, rejections and mandatory-filter exclusions) and `omitted` the proposals the budget left unexamined. Query work may scale with the initial participant/owned-skill read but never with the proposals a decision examined or omitted. This is a manual measurement on the recorded host, never a permanent timing assertion.
