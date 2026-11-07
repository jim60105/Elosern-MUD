## MODIFIED Requirements

### Requirement: Configuration layers follow default, environment, secret precedence
The effective value of an environment-overridable setting SHALL be resolved in the order
code default < same-named environment variable < `server/conf/secret_settings.py`: the
environment assignment SHALL happen in `settings.py` above the existing `secret_settings`
import, and a setting defined in `secret_settings.py` SHALL therefore override the
environment value without any change to the import structure.

#### Scenario: An environment value overrides the code default
- **WHEN** `ART_SD_TIMEOUT_SECONDS=120` is present and no `secret_settings` module defines it
- **THEN** the effective setting is the integer `120`

#### Scenario: A secret-settings value overrides the environment
- **WHEN** `ART_SD_TIMEOUT_SECONDS=120` is present and a `server.conf.secret_settings` module that
  defines `ART_SD_TIMEOUT_SECONDS = 90` is imported over it
- **THEN** the effective setting is `90` and no environment value reached it

#### Scenario: Secret settings replace only the layers they name
- **WHEN** `LLM_MODEL=llama3.2` and `LLM_NARRATOR_MAX_TOKENS=400` are present and
  `secret_settings.py` defines an `LLM_PROFILES` map whose sole entry is a complete
  `character_creation` profile
- **THEN** the `narrator` profile's `max_tokens` is `400` and every layer absent
  from the secret map keeps its environment-resolved values, while `character_creation`
  equals the secret entry

#### Scenario: The LLM family resolves two-tier and merges secrets per layer
- **WHEN** the LLM profile family is resolved
- **THEN** the environment level is two-tier (code default < global `LLM_<SUFFIX>` variable < per-layer `LLM_<LAYER>_<SUFFIX>` variable) and the secret level merges **per layer**
- **AND** settings resolution SHALL snapshot the fully environment-resolved raw profile map before the `secret_settings` import, and a `secret_settings.py` `LLM_PROFILES` map SHALL replace wholesale only the layers it names, every other layer keeping its environment-resolved entry

#### Scenario: Secrets stay out of the environment
- **WHEN** the configuration surface is inspected
- **THEN** Secrets (`SECRET_KEY` and equivalents) SHALL NOT be moved to the environment: `secret_settings.py` remains their only sanctioned location, subject only to the scoped `LLM_API_KEY` exception introduced by the endpoint-wire configuration
