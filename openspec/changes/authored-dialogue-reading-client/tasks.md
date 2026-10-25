# Tasks

Read design.md and the named dependency shared contracts first. All boxes are future implementation tasks; this proposal implements nothing. Each unit includes its own tests/documentation and is bounded to 45-120 minutes.

## 1. Pending completion state machine

Shared contract v2 preserves full generated IDs in admission/queue/request/response fields. Test long generated IDs, phase-retired memory and identical completion with no source-specific branch or truncation.

- [ ] 1.1 Implement applyDialogueReading and finishDialogueDelivery with dedup, exact response binding, retry/discard distinctions and no browser persistence. Add tests/stores/dialogue_reading.test.js (new) with synthetic saved/stale/error responses and document bounded memory lifecycle.

## 2. Pure-chain and playback wiring

- [ ] 2.1 Connect formal-only scene-finished events, predecessor-first ack queue and local public successor reveal; keep qualified choices authoritative. Add AppClient tests for pending status, no repeat effects, same-delivery refresh and stale-character replies.

## 3. Browser recovery and ownership

- [ ] 3.1 Add focused retry-without-reread and reload-discard acceptance to test_browser_exploration_dialogue.py, register new methods and existing store wiring in relevant inventories. Verify focused Vitest/browser methods and contract_gate; update player-facing help only for observable saved/pending semantics.

