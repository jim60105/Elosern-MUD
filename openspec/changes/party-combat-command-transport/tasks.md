# Tasks

Total estimate: **6.5 hours**, including implementation, focused verification, documentation and integration. Direct prerequisites and file/spec conflicts are in proposal.md and the shared batch contract. Each group lands its own tests/docs; the final group checks integration.

## 1. Bounded implementation and evidence (1.25h)

- [ ] 1.1 Implement exact combat.actor_choices/command/exit_prompt/exit_confirm adapters and retire old combat registrations; test all closed payloads, reserved flee and authorized commander/actor separation.

## 2. Bounded implementation and evidence (1.25h)

- [ ] 2.1 Amend dispatcher actor-reference and registry/scale contracts without relaxing authentication; test forged actor/session references, no-puppet, extra fields and exact action allowlist.

## 3. Bounded implementation and evidence (1.25h)

- [ ] 3.1 Implement safe prompt/result variants, active inventory.use rejection and canonical progress-before-result publication; test nonfinal, needs-selection, stale, retry, final and terminal results.

## 4. Bounded implementation and evidence (1h)

- [ ] 4.1 Wire committed-round-only beat publication and requested-actor transport state/reconnect invalidation; test no pending-round beats or replay and unchanged global result-data safety.

## 5. Bounded implementation and evidence (0.75h)

- [ ] 5.1 Update dispatcher/API docs, canonical requirement IDs, adapter fixtures and shard ownership; verify every old producer is accounted for in the client cutover dependencies.

## 6. Integration gate (1h)

- [ ] 6.1 Run focused Python dispatcher/action/publication tests, Node result-envelope cases and tools.contract_gate; run observability lint and focused boundary tests if logging changes.
