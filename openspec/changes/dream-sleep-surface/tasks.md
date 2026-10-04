## 1. Implement the bounded behavior

- [x] 1.1 Wire explicit optional choice to real sleep outcomes in text/browser adapters; verify zero-duration, rejection, ordinary sleep and actual interrupted results.
- [x] 1.2 Expose server-authored dream state/remaining count and confirm/draft/awaken actions with text parity; verify forged owner/stale request rejection and sixth cap.
- [x] 1.3 Preserve sleep association and generation-free escape across reconnect/failure; verify tick/gauges/live effects unchanged after departure.
- [x] 1.4 Update both command docs and contract tests, then run changed-path offline sleep→dream→draft/confirm→awaken smoke; verify the complete approved presentation contract.

## 2. Evidence and handoff

- [x] 2.1 Add synthetic behavior tests for every delta scenario and use recorded/FakeLLMClient responses only; verify no permanent test calls live model/image services and any shipped-lore test is a registered data-contract test.
- [x] 2.2 Register each new/moved Evennia test module in exactly one `.github/evennia-shards.json` shard; obtain existing canonical main requirement IDs with `uv run --locked python -m tools.spec_traceability list` and annotate substantive tests. After delta sync makes new main IDs available, obtain them from that same tool rather than guessing; verify traceability and shard contracts.
- [x] 2.3 Update owning developer documentation/changelog and applicable command documentation, extend the observability catalog for new boundary events, and use only `world.observability` with IDs/counts/context and exception chains; verify logging privacy and focused facade assertions.
- [x] 2.4 Run focused tests, the actual changed-path recorded/offline smoke, `uv run --locked python -m tools.contract_gate`, and `openspec validate dream-sleep-surface --strict`; record exercised results and leave broad browser/evidence gates CI-owned.

## Exercised evidence

- Focused Evennia run: 82 tests passed (`test_dream_surface`,
  `test_dream_session`, `test_skip_commands`, `tests.test_command_docs`).
- Browser-adapter/presenter/skip-command focused run: 26 tests passed.
- Focused Vitest dream and waiting surfaces: 8 tests passed.
- Dependency-free Node protocol/echo gate: 479 tests passed.
- The recorded/offline changed-path smoke is
  `DreamSurfaceTests.test_recorded_changed_path_sleep_exchange_draft_confirm_awaken_smoke`:
  accepted sleep, real guarded FakeLLMClient scene/dialogue, draft, explicit
  confirmation and model-free awakening; physical state remains post-sleep.
- `tools.contract_gate` passed (1859 requirements covered; zero traceability,
  observability, test-data or manifest violations; 18 contracts passed).
- `openspec validate dream-sleep-surface --strict` passed.
- Broad managed-browser, aggregate coverage and complete evidence gates remain
  CI-owned. Delta-only requirement annotations remain archive-sync owned.
