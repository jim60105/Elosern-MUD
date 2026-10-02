# llm-client Specification (Delta)

## MODIFIED Requirements

### Requirement: Request headers carry authentication and attribution without leaking the key
The client SHALL build the request headers passed to the transport by first deriving, only when the corresponding profile field is non-empty, an `Authorization` header of the exact form `Bearer <api_key>`, an `X-Title` header carrying `app_title`, and an `HTTP-Referer` header carrying `app_url`, and SHALL always derive a `User-Agent` header carrying the effective `HTTP_USER_AGENT` setting (per the `outbound-http-identity` capability — the shared accessor, never a client-local literal), and then overlaying the profile's frozen `headers` mapping so that an explicitly configured header of the same (exact-case) name wins over the derived one. Credential-bearing standard header names are rejected in the profile mapping upstream, so the `Authorization` escape hatch cannot smuggle a bearer value past the `repr` exclusion. The api key SHALL NOT appear in any log line, any error message or failure representation, or any client/profile debug output produced on any success or failure path.

#### Scenario: Explicit headers win over derived attribution
- **WHEN** a profile sets `app_title = "Elosern"` AND an explicit `headers` mapping entry `X-Title: Other`
- **THEN** the transmitted headers carry `X-Title: Other`

#### Scenario: An explicit User-Agent header wins over the derived one
- **WHEN** a profile's frozen `headers` mapping carries an explicit `User-Agent` entry
- **THEN** the transmitted headers carry exactly the configured value and never a second `User-Agent` entry

#### Scenario: The derived identity ships without an explicit header
- **WHEN** a profile carries no `User-Agent` mapping entry and the client sends a request
- **THEN** the transmitted headers include `User-Agent` equal to the effective `HTTP_USER_AGENT` setting

#### Scenario: A configured key authenticates the request
- **WHEN** a profile carries a non-empty `api_key` and the client sends a request
- **THEN** the request headers include `Authorization: Bearer <api_key>` exactly

#### Scenario: An empty key sends no Authorization header
- **WHEN** a profile's `api_key` is the empty string
- **THEN** the request headers contain no `Authorization` entry

#### Scenario: Attribution headers appear only when configured
- **WHEN** a profile sets `app_title = "Elosern"` and leaves `app_url` empty
- **THEN** the request headers include `X-Title: Elosern` and contain no `HTTP-Referer` entry

#### Scenario: A transport failure never surfaces the key
- **WHEN** a request governed by a profile with a non-empty `api_key` fails with any transport error (connection, HTTP status, malformed body, or timeout)
- **THEN** the failure representation, the safe log line, and every message observable by the calling layer contain no trace of the key

### Requirement: A default profile produces an unchanged wire format
When every optional endpoint-configuration field of the profile holds its omit default (empty string or `None`), the serialized request body SHALL equal the pre-configuration client's byte-for-byte, and the serialized headers SHALL equal the profile's frozen mapping plus exactly one additional derived `User-Agent` header carrying the effective `HTTP_USER_AGENT` setting, so existing local endpoints observe no difference from the endpoint-configuration change other than the declared client identity added by `outbound-http-identity`.

#### Scenario: Byte identity under defaults
- **WHEN** the client serializes a request under a profile with no optional field set
- **THEN** the body JSON contains exactly `model`, `messages`, `temperature`, `max_tokens` (plus `response_format` under the existing opt-in rule) and the headers are the profile's frozen mapping plus the derived `User-Agent` entry and nothing else
