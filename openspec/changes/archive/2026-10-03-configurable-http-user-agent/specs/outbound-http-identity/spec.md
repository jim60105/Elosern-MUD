# outbound-http-identity Specification (Delta)

## ADDED Requirements

### Requirement: Every runtime outbound HTTP request carries the configured User-Agent
Every outbound HTTP request the server itself makes at runtime SHALL carry a `User-Agent` header whose value is exactly the effective `HTTP_USER_AGENT` setting, obtained through one shared accessor rather than a per-call-site constant: the prompt-translation model fetch, every sd-webui request (generation POSTs and the bounded GET enumerations), and every LLM chat-completion request. No runtime request SHALL reach the wire with a transport's implicit default agent (urllib's `Python-urllib/*`, http.client's absent header, or Twisted Agent's absent header), and no caller module SHALL define its own User-Agent literal. The one sanctioned deviation from exact equality is the LLM transport's pre-existing header-overlay rule: a profile whose frozen `headers` mapping carries an explicit `User-Agent` entry replaces the derived one on that transport's requests (see the `llm-client` capability), and such a request is exempt from the configured-equality statement above. The header value SHALL be read per request, so a settings reload that changes `HTTP_USER_AGENT` takes effect on the next request without a restart requirement beyond the standard restart-to-apply rule. The one documented non-coverage is `world/art/cutout.py`: its background-removal weight downloads are issued inside the third-party removal library, which exposes no request-header seam, and monkey-patching that library is explicitly out of scope; developer- and CI-only scripts are not the server's outbound runtime traffic and are not governed here.

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

### Requirement: The configured identity falls back to the documented default
When `HTTP_USER_AGENT` is absent, present-but-empty, or whitespace-only, every governed request SHALL carry the documented code default `elosern-mud/1.0`, never an empty header value: an empty `User-Agent` is the same class of edge-rejection failure this configuration exists to avoid, so the empty-string sentinel used by the generation free-text knobs SHALL NOT be available here.
(On the LLM transport, an explicit profile-configured `User-Agent` mapping entry continues to win over this fallback identity, preserving the overlay precedence rule.)

- **WHEN** the settings module is imported with `HTTP_USER_AGENT` absent from the environment
- **THEN** the effective setting equals the documented default `elosern-mud/1.0`

#### Scenario: A blank override degrades to the default, not to an empty header
- **WHEN** `HTTP_USER_AGENT` is present in the environment as the empty string or whitespace only
- **THEN** the effective setting equals the documented default and no governed request can emit an empty `User-Agent`
