# outbound-http-identity Specification

## Purpose
The single deployment-tunable identity the server presents on every outbound HTTP request it
makes itself — the prompt-translation model fetch, the sd-webui worker, and the LLM client —
so no transport's implicit default agent (or an empty header) ever reaches an upstream edge,
with one shared accessor and a documented default that a blank override can never defeat.

## Requirements

### Requirement: Every runtime outbound HTTP request carries the configured User-Agent
Every outbound HTTP request the server itself makes at runtime SHALL carry a `User-Agent` header whose value is exactly the effective `HTTP_USER_AGENT` setting, obtained through one shared accessor rather than a per-call-site constant: the prompt-translation model fetch, every sd-webui request (generation POSTs and the bounded GET enumerations), and every LLM chat-completion request.

#### Scenario: The model fetch sends the configured identity
- **WHEN** the translation model download runs with `HTTP_USER_AGENT` at its effective value
- **THEN** the request handed to the transport carries `User-Agent` exactly equal to the setting, and no `Python-urllib/*` default can reach the argos-net.com edge

#### Scenario: The sd-webui transport ships an explicit identity
- **WHEN** any sd-webui request (generation POST, enumeration GET, or connectivity probe) is issued
- **THEN** the captured wire headers include `User-Agent` equal to the setting alongside the existing content-type and Basic-auth headers

#### Scenario: The LLM request carries the identity absent an explicit profile header
- **WHEN** the client sends a chat-completion request under a profile with no explicit `User-Agent` mapping entry
- **THEN** the wire headers include `User-Agent` equal to the setting

#### Scenario: An override changes every request at once
- **WHEN** `HTTP_USER_AGENT` is overridden and one request of each kind is issued, the LLM request under a profile with no explicit `User-Agent` mapping entry
- **THEN** all three carry the overridden value verbatim, byte-for-byte as configured

#### Scenario: No transport implicit default agent and no per-call-site literal

- **WHEN** any governed runtime request is issued
- **THEN** it never reaches the wire with a transport's implicit default agent (urllib's `Python-urllib/*`, http.client's absent header, or Twisted Agent's absent header)
- **AND** no caller module defines its own User-Agent literal

#### Scenario: The LLM header-overlay rule is the one sanctioned deviation

- **WHEN** an LLM profile's frozen `headers` mapping carries an explicit `User-Agent` entry
- **THEN** it replaces the derived one on that transport's requests (see the `llm-client` capability)
- **AND** such a request is exempt from the configured-equality statement

#### Scenario: The header value is read per request

- **WHEN** a settings reload changes `HTTP_USER_AGENT`
- **THEN** the change takes effect on the next request without a restart requirement beyond the standard restart-to-apply rule

#### Scenario: Cutout weight downloads and dev/CI scripts are the documented non-coverage

- **WHEN** the governance scope is checked against `world/art/cutout.py` and developer-/CI-only scripts
- **THEN** `world/art/cutout.py` background-removal weight downloads are not covered — they are issued inside the third-party removal library, which exposes no request-header seam, and monkey-patching that library is explicitly out of scope
- **AND** developer- and CI-only scripts are not the server's outbound runtime traffic and are not governed here

### Requirement: The configured identity falls back to the documented default
When `HTTP_USER_AGENT` is absent, present-but-empty, or whitespace-only, every governed request SHALL carry the documented code default `elosern-mud/1.0`, never an empty header value.

- **WHEN** the settings module is imported with `HTTP_USER_AGENT` absent from the environment
- **THEN** the effective setting equals the documented default `elosern-mud/1.0`

#### Scenario: A blank override degrades to the default, not to an empty header
- **WHEN** `HTTP_USER_AGENT` is present in the environment as the empty string or whitespace only
- **THEN** the effective setting equals the documented default and no governed request can emit an empty `User-Agent`

#### Scenario: The empty-string sentinel of the free-text knobs is unavailable here

- **WHEN** the `HTTP_USER_AGENT` setting is configured
- **THEN** an empty `User-Agent` — the same class of edge-rejection failure this configuration exists to avoid — is never accepted: the empty-string sentinel used by the generation free-text knobs is not available for this setting

#### Scenario: An explicit profile User-Agent wins over the fallback identity

- **WHEN** the LLM transport sends a request under a profile whose frozen `headers` mapping carries an explicit `User-Agent` entry while the setting falls back to the default
- **THEN** the explicit profile-configured `User-Agent` mapping entry continues to win over the fallback identity, preserving the overlay precedence rule
