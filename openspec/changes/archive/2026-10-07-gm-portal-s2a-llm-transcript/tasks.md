## 1. Retained transcript sink

- [x] 1.1 Confirm landed S1 and add transcript write/find/prune plus explicit enabled-status seam; verify temp-directory Unicode JSONL, local-date routing, newest-date/file-order lookup and retention-boundary tests.
- [x] 1.2 Add existing-mechanism environment settings (enabled true, retention 14, integer >=1) and once-per-start prune catalog hook; verify override validation, disabled write/lookup, startup ordering and pruning tests.
- [x] 1.3 Contain serialization, read, prune, permission and stderr failures without gameplay exceptions; verify failure-path tests with injected failures rather than live services.

## 2. Correlated call recording

- [x] 2.1 Add optional call_id/attempt descriptor metadata and generate uuid4 hex at guardrail entry; migrate every descriptor-copying wrapper including option proposals and epochs; verify fake-client/descriptor and wrapper regression tests.
- [x] 2.2 Record full settled real transport exchanges, request/response/raw text/error metadata and exactly one terminal guardrail outcome across ok/degraded/rejected, disabled and unexpected failures; verify recording-transport retry/degrade, accepted, fake-only and raising-fallback tests and unchanged propagated exceptions.
- [x] 2.3 Preserve credentials exclusion and _scrub_key for all recorded error paths and echoed successful/raw response payloads, hostname-only endpoints and no request headers; verify API key, header and URL-userinfo fixtures do not leak into exchanges, outcomes or operational sinks.
- [x] 2.4 Add call_id to llm_call/retry/cached-token events and propagate actual correlation through correspondence/dream failures; verify all terminal and retry records/events share the identifier and no pre-call failure fabricates one.

## 3. Prose rule cutover and handoff

- [x] 3.1 Restore letter cmd_in args/body and dream failure input, bound every facade context value to 200 single-line characters, and update existing caller-binding event assertions; verify focused correspondence/dream/render and AI observability tests.
- [x] 3.2 Amend logging design §3.1, rules list and affected event rows, AGENTS.md prohibition, context/dream-session comments, .env.example and settings-and-environment.md; verify guidance agrees with permitted prose, credential exclusion and unchanged private knowledge boundaries.
- [x] 3.3 Register every new Python test module exactly once in .github/evennia-shards.json; prepare substantive requirement tests and add canonical literal covers_requirement IDs obtained from tools.spec_traceability list when main deltas are synced; verify shard ownership and post-sync traceability without guessed IDs.
- [x] 3.4 Run focused uv-managed tests using the documented --env-file=<file> Evennia guard, observability lint and tools.contract_gate, then openspec validate gm-portal-s2a-llm-transcript --strict; record actual evidence and leave complete outcome/lookup contracts ready for S2b.
