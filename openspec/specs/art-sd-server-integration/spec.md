# art-sd-server-integration Specification

## Purpose

Define the in-process sd-webui server integration surface beyond raw generation:
bounded read-only option enumeration for staff diagnostics, secret-file-only
HTTP Basic auth, verbatim pass-through of configured prompt styles and Forge
additional modules, and the defensive parsing of the server-reported generation
seed. All capabilities here are read-only or request-building only; they never
mutate game state.

## Requirements

### Requirement: The sd-webui client enumerates server options through bounded GET calls
`world/art/sd_worker.py` SHALL expose option enumeration for the five sd-webui
option endpoints enumerated below, each issued through the same
deadline-bounded transport as generation, with a per-call timeout cap no
larger than 10 seconds. Each call SHALL require a JSON list of at most 100
items and SHALL raise only the existing named `SDError` codes on transport,
size, or shape violations. Enumeration SHALL NOT mutate any game or art state.

#### Scenario: Samplers are listed from their name field
- **WHEN** the server returns `[{"name": "Euler a"}, {"name": "ER SDE"}]` for
  the samplers endpoint
- **THEN** enumeration returns exactly `["Euler a", "ER SDE"]` and no record,
  queue, or setting is modified

#### Scenario: Scheduler labels win over names
- **WHEN** the server returns `[{"label": "Beta", "name": "_beta"}]` for the
  schedulers endpoint
- **THEN** enumeration returns `["Beta"]`

#### Scenario: A malformed option list is a named error
- **WHEN** an option endpoint returns a JSON object instead of a list, a list
  longer than 100 items, or a non-200 status
- **THEN** enumeration raises the corresponding named `SDError`
  (`sd_malformed_response` or `sd_http_error`) and no list is returned

#### Scenario: The five option endpoints are enumerated
- **WHEN** option enumeration is exercised
- **THEN** it covers exactly `/sdapi/v1/sd-models`, `/sdapi/v1/samplers`,
  `/sdapi/v1/schedulers`, `/sdapi/v1/prompt-styles`, and `/sdapi/v1/sd-modules`

#### Scenario: Enumeration GETs carry no Content-Type header
- **WHEN** an option enumeration request is issued
- **THEN** the GET carries no `Content-Type` header

#### Scenario: Item fields map with verified reference fallbacks
- **WHEN** option items are mapped to display names
- **THEN** the mapping uses model `title` then `model_name`, sampler `name`,
  scheduler `label` then `name`, style `name`, and module `model_name`,
  dropping empty strings

### Requirement: The sd-webui client sends Basic auth only from secret-file credentials
`server/conf/settings.py` SHALL define `ART_SD_USERNAME` and
`ART_SD_PASSWORD` as plain settings with empty-string defaults and SHALL NOT
read any environment variable for either name. Every request the client makes
SHALL carry an `Authorization: Basic` header derived from both settings if and
only if both are non-empty; with either empty no header is sent. The password
value SHALL never appear in any log line, error message, or command output.

#### Scenario: No header without credentials
- **WHEN** a request is made with `ART_SD_USERNAME` or `ART_SD_PASSWORD` empty
- **THEN** the request carries no `Authorization` header

#### Scenario: Both credentials produce the Basic header
- **WHEN** a request is made with username `u` and password `p` configured
- **THEN** the request carries `Authorization: Basic base64("u:p")` and the
  password literal appears in no log record or raised error message

#### Scenario: Auth applies to every client request kind
- **WHEN** the client sends model option endpoint, options endpoint, or
  txt2img requests
- **THEN** each request follows the Basic-auth header rule above

### Requirement: Generation requests carry configured styles and Forge modules verbatim
`ART_SD_STYLES` and `ART_SD_MODULES` SHALL be free-text environment-overridable
settings holding comma-separated name lists; each SHALL be split on commas,
each item stripped, and empty items dropped. When the parsed list is non-empty,
the txt2img request SHALL include the corresponding fields set verbatim to
that list; when empty, each field SHALL be omitted entirely, matching the
sampler/scheduler omission rule. Names SHALL be passed through verbatim
without client-side validation.

#### Scenario: Styles are omitted when unset and included verbatim when set
- **WHEN** `ART_SD_STYLES` is empty, then set to `"style a, style b"`
- **THEN** the request has no `styles` key in the first case and
  `styles: ["style a", "style b"]` in the second

#### Scenario: Modules carry the fixed dtype companion
- **WHEN** `ART_SD_MODULES` is `"te.safetensors,vae.safetensors"`
- **THEN** `override_settings` contains
  `forge_additional_modules: ["te.safetensors", "vae.safetensors"]` and
  `forge_unet_storage_dtype: "Automatic (fp16 LoRA)"`

#### Scenario: Separator-only values are treated as empty
- **WHEN** `ART_SD_STYLES` is `", ,"`
- **THEN** the request contains no `styles` key

#### Scenario: Non-empty lists map to their request fields
- **WHEN** the parsed list for styles or modules is non-empty
- **THEN** styles populate the `styles` key, and modules populate
  `override_settings.forge_additional_modules` together with the fixed
  companion `override_settings.forge_unet_storage_dtype` equal to
  `"Automatic (fp16 LoRA)"`
