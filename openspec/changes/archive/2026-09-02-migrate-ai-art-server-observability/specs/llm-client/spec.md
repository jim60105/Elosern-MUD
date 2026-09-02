## ADDED Requirements

### Requirement: LLM calls and transport failures emit observability events

Each guarded LLM call SHALL emit exactly one `llm_call` info event through
the `world.observability` facade at the guardrail boundary, with `layer`,
`profile`, `ms`, `result` (`ok`|`degraded`|`rejected`), and — when not ok —
a `reason` code. Every transport failure SHALL additionally emit
`llm_transport_error` (warn) from the client with `endpoint` and the
exception chain in context. Event emission MUST NOT change safe failure
signaling, retry, or degradation semantics.

#### Scenario: A degraded guarded call is fully reconstructable from two lines

- **WHEN** a guarded call fails at transport and the guardrail degrades
- **THEN** one `llm_transport_error` event identifies endpoint and exception
  and one `llm_call` event records `result=degraded` with layer and profile

#### Scenario: A successful call leaves exactly one boundary event

- **WHEN** a guarded call returns schema-valid output
- **THEN** exactly one `llm_call` event with `result=ok` and elapsed `ms` is
  logged, with no transport-error event
