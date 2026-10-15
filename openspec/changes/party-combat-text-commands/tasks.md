# Tasks

Total estimate: **7 hours**, including implementation, focused verification, documentation and integration. Prerequisites and file/spec conflicts are in proposal.md and the shared batch contract. Every group lands its own relevant tests/docs; the final group checks integration.

## 1. Bounded implementation and evidence (1.5h)

- [ ] 1.1 Mount actor command/action-list syntax with deterministic token resolution; test actor versus target identity, skill scale and duplicate/unknown/mixed target rejection.

## 2. Bounded implementation and evidence (1.5h)

- [ ] 2.1 Route companion skill/item/tactic confirmation and commander legacy cast/use through the shared facade; test replacing earlier choice, last-auto-round, no cost before complete and local item consumption.

## 3. Bounded implementation and evidence (1h)

- [ ] 3.1 Implement retreat/forfeit token prompts and all allied flee aliases; test explicit cancellation, stale/replayed token and unchanged enemy flee.

## 4. Bounded implementation and evidence (1h)

- [ ] 4.1 Update both command docs and curated command manifest for every key/alias/syntax/context change; test command-doc parity and document no possession requirement.

## 5. Bounded implementation and evidence (1h)

- [ ] 5.1 Exercise a real text command path for multiple actors, skill, item, revision and confirmed exit in isolated encounters; record outputs and reconnect restoration.

## 6. Integration gate (1h)

- [ ] 6.1 Update canonical annotations and shard ownership; run focused command/session/doc tests and tools.contract_gate, plus observability lint if command logging changes.
