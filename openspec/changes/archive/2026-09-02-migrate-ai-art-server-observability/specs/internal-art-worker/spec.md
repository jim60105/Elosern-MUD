## ADDED Requirements

### Requirement: Named degradation codes carry the swallowed exception in the log

Where the internal sd-webui client maps a failure to a named error code
(such as `sd_internal_error` or `sd_client_config_error`), the outward code
contract MUST stay unchanged, and the handler MUST emit a facade
`log_error`/`log_warn` event carrying the exception chain and, where
observable, the sd-webui endpoint identity — no failure may be reduced to a
code string alone.

#### Scenario: An internal worker failure is diagnosable beyond its code

- **WHEN** generation raises inside the worker and the record settles as
  `sd_internal_error`
- **THEN** the returned code is unchanged and the log line carries the
  exception type, message, and origin frame in its `tb:` segment
