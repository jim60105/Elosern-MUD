# Tasks

## 1. Closed implementation units

- [ ] 1.1 Install independent generation extra and implement single background job admission/status/cancel; test event-loop responsiveness, second-job rejection and failed/cancelled prior-artifact preservation.
- [ ] 1.2 Integrate world-data/handoff exclusion with the existing service state machine and existing guarded atomic artifact writer; test every relevant command route and external-turn publication refusal.
- [ ] 1.3 Invalidate captured output on real source changes and recheck before publication; test an external replace during generation prevents current publication and unchanged successful input publishes atomically.
- [ ] 1.4 Implement explicit regeneration/freshness/revision UI with old-output labels and browse/inspect controls; test no pointer-triggered regeneration and all terminal states.
- [ ] 1.5 Extend specialist mapping, register discoverable service/browser evidence and CI ownership, document job semantics and run focused and contract gates.

## Workflow follow-up

- This proposal is ready for review only. Implementation requires a new explicit apply assignment.
- Before eventual archive, obtain canonical requirement IDs from the effective merged specs and attach substantive discoverable tests; no uncovered-requirement waiver or new copied-data pin is permitted.
