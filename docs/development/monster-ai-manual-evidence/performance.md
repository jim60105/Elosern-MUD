# Manual performance scenario (monster-ai-manual-evidence)

- Baseline commit: `143b28d6f2cb07090f88753eacd4ea0c32e0246c`
- Configuration fingerprint: `e40c071ef3a428c419c6ff58c9750c77b93d01d01911b3dc2f3c62f09ac20232`
- Host: `Jim-Fedora` / Linux-7.2.6-200.fc44.x86_64-x86_64-with-glibc2.43 (clock monotonic)
- Envelope: 16 participants, up to 16 owned active skills, candidate budget 256; 5 warm-ups then 50 measurements per mode, one cold call

| mode | cold ms | p50 ms | p95 ms | queries | examined | accepted | omitted | dice isolated |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| legacy | 3.98 | 0.56 | 0.74 | 10 | 0 | 0 | 0 | False |
| utility | 44.53 | 14.79 | 14.96 | 97 | 98 | 98 | 0 | True |

Warm p95 budget 50 ms: met.

| candidates | queries | examined |
| ---: | ---: | ---: |
| 1 | 97 | 42 |
| 8 | 97 | 98 |
| 15 | 97 | 154 |

Query work may scale with the initial participant/owned-skill read but never with per-candidate target-plan enumeration. This is a manual measurement on the recorded host, never a permanent timing assertion.
