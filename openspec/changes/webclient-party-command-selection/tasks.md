# Tasks

Total estimate: **7 hours**, including implementation, focused verification, documentation and integration. Direct prerequisites and file/spec conflicts are in proposal.md and the shared batch contract. Each group lands its own tests/docs; the final group checks integration.

## 1. Bounded implementation and evidence (1.5h)

- [ ] 1.1 Parameterize the existing UMD menu and frame resolver by actor, implement actor/progress/revisit frames and pending result handling; test selection edits and disabled members.

## 2. Bounded implementation and evidence (1.5h)

- [ ] 2.1 Migrate all skill payload producers to combat.command with current session/round/draft versions; test every TargetSpec, scale and final versus partial results.

## 3. Bounded implementation and evidence (1h)

- [ ] 3.1 Bind SELF stage lighting and cross-side confirmation to commanded actor; test companion SELF, mixed AREA, actor switch while targeting and warning cancellation.

## 4. Bounded implementation and evidence (1h)

- [ ] 4.1 Integrate reconnect, stale replacement, focus restoration and playback lock; test no automatic send or draft erasure on reconnect.

## 5. Bounded implementation and evidence (1h)

- [ ] 5.1 Add stories and focused keyboard/pointer/browser coverage within the existing centered card at both acceptance viewports; update client flow docs and browser shard manifest.

## 6. Integration gate (1h)

- [ ] 6.1 Run focused Node/Vitest and one bounded browser method plus tools.contract_gate; update canonical requirement IDs and preserve all active UI geometry contracts.
