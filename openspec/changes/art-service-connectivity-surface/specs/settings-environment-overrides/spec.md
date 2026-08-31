# settings-environment-overrides delta specification

Base: this delta applies on top of the `art-output-format-pipeline` change's
version of the typed-overrides requirement (strictly serial application:
`art-generation-config-parity` and then `art-output-format-pipeline` archive
first). The env-backed set therefore grows from exactly 24 to exactly 26.

## MODIFIED Requirements

### Requirement: Deployment settings accept typed environment overrides
`server/conf/settings.py` SHALL derive the initial value of every deployment-tunable setting it
declares in the `ART_SD_*`, `ART_SCHEDULER_*`, and `ELOSERN_VUE_CLIENT` groups from an environment
variable, using typed conversion at settings import. The env-backed set is exactly:
`ART_SD_TIMEOUT_SECONDS`, `ART_SD_STEPS`, `ART_SD_CFG_SCALE`, `ART_SD_SAMPLER`,
`ART_SD_SCHEDULER`, `ART_SD_CHECKPOINT`, `ART_SD_STYLES`, `ART_SD_MODULES`,
`ART_SD_SCENE_WIDTH`, `ART_SD_SCENE_HEIGHT`, `ART_SD_PORTRAIT_WIDTH`, `ART_SD_PORTRAIT_HEIGHT`,
`ART_SD_MAX_RESPONSE_BYTES`, `ART_SD_MAX_IMAGE_DIMENSIONS`, `ART_SD_MAX_IMAGE_PIXELS`,
`ART_SD_PREPIN_SAMPLES_FORMAT`, `ART_SD_OUTPUT_FORMAT`, `ART_SD_OUTPUT_QUALITY`,
`ART_SD_PRESERVE_GENERATION_METADATA`, `ART_SD_PROBE_TIMEOUT_MS`, `ART_SD_PROBE_CACHE_SECONDS`,
`ART_SCHEDULER_ENABLED`, `ART_SCHEDULER_INTERVAL_SECONDS`, `ART_SCHEDULER_LIMIT`, and
`ELOSERN_VUE_CLIENT` — each from a variable of the same name — plus `ART_SD_BASE_URL` from
`SD_WEBUI_BASE_URL` as fixed by the `internal-art-worker` spec. No other setting in these groups
SHALL read the environment; `ART_SD_CLIENT`, the derived `ART_SD_OUTPUT_EXTENSION`, and the auth
pair `ART_SD_USERNAME`/`ART_SD_PASSWORD` in particular SHALL NOT (see their own requirements).
Conversion rules: integers for `ART_SD_TIMEOUT_SECONDS`, `ART_SD_STEPS`, the four
`ART_SD_{SCENE,PORTRAIT}_{WIDTH,HEIGHT}` dimensions, `ART_SD_MAX_RESPONSE_BYTES`,
`ART_SD_MAX_IMAGE_DIMENSIONS`, `ART_SD_MAX_IMAGE_PIXELS`, `ART_SCHEDULER_INTERVAL_SECONDS`, and
`ART_SCHEDULER_LIMIT`, each rejecting zero and negatives; an inclusive 1-to-100 integer for
`ART_SD_OUTPUT_QUALITY` (rejecting zero, negatives, and values above 100); an inclusive
1000-to-60000 integer for `ART_SD_PROBE_TIMEOUT_MS` and an inclusive 5-to-3600 integer for
`ART_SD_PROBE_CACHE_SECONDS` (values below the lower bound or above the upper bound rejected);
a positive float for `ART_SD_CFG_SCALE`; case-insensitive boolean words (`1/true/yes/on` true,
`0/false/no/off` false, nothing else) for `ART_SD_PREPIN_SAMPLES_FORMAT`,
`ART_SD_PRESERVE_GENERATION_METADATA`, `ART_SCHEDULER_ENABLED`, and `ELOSERN_VUE_CLIENT`;
case-insensitive membership in the closed set `png|webp|jpeg|avif` for `ART_SD_OUTPUT_FORMAT`;
free-text strings for `ART_SD_SAMPLER`, `ART_SD_SCHEDULER`, `ART_SD_CHECKPOINT`,
`ART_SD_STYLES`, and `ART_SD_MODULES`, whose empty value means "the server's default" (for the
two list knobs, "the field is omitted from the request"). The four dimensions SHALL additionally
be positive multiples of 8. A variable that is absent, or present-but-empty for typed, boolean,
choice, and URL knobs, SHALL yield the documented code default; present-but-empty for a
free-text knob SHALL yield the empty "server default" value. For the same-named set, the
`.env.example` entry, the error message, and the setting SHALL be one string.

The test settings bootstrap `server/conf/test_settings.py` SHALL remove every env-backed
variable name from `os.environ` before importing the production settings, so a test run's
effective settings never depend on a developer's or CI runner's inherited shell environment.

#### Scenario: Unset variables keep the documented defaults
- **WHEN** the settings module is imported with none of the env-backed variables present in the
  environment
- **THEN** every `ART_SD_*`, `ART_SCHEDULER_*`, and `ELOSERN_VUE_CLIENT` setting equals its
  documented default (including `ART_SD_PROBE_TIMEOUT_MS=5000` and
  `ART_SD_PROBE_CACHE_SECONDS=300`), and the server starts

#### Scenario: Valid overrides coerce to typed values
- **WHEN** the settings module is imported with `ART_SD_PROBE_TIMEOUT_MS=2000` and
  `ART_SD_PROBE_CACHE_SECONDS=60` in the environment
- **THEN** the settings are the integers `2000` and `60` respectively

#### Scenario: Probe bounds are inclusive at both ends
- **WHEN** the settings module is imported with `ART_SD_PROBE_TIMEOUT_MS=1000`, then separately
  with `=60000`, and `ART_SD_PROBE_CACHE_SECONDS` with `=5`, then separately with `=3600`
- **THEN** all four imports succeed producing the given values

#### Scenario: An empty dimension value falls back instead of poisoning the request
- **WHEN** `ART_SD_SCENE_WIDTH` is present but empty in the environment
- **THEN** `ART_SD_SCENE_WIDTH` equals the documented default rather than an empty or zero value

#### Scenario: Inherited deployment variables cannot perturb a test run
- **WHEN** the test settings module is imported with `ART_SD_PROBE_TIMEOUT_MS=1` present in the
  shell environment
- **THEN** the effective `ART_SD_PROBE_TIMEOUT_MS` for the test session is the documented default
  `5000`

### Requirement: Invalid environment values fail settings load with a named error
An environment variable that is present but cannot be coerced to its setting's declared type or
bounds — a non-integer `ART_SD_STEPS`, a non-boolean word for a boolean knob, a negative or
zero positive-bound integer, an `ART_SD_OUTPUT_QUALITY` above 100, an `ART_SD_PROBE_TIMEOUT_MS`
below 1000 or above 60000, an `ART_SD_PROBE_CACHE_SECONDS` below 5 or above 3600, a non-positive
`ART_SD_CFG_SCALE`, a dimension that is not a positive multiple of 8, or an
`ART_SD_OUTPUT_FORMAT` outside the closed `png|webp|jpeg|avif` set — SHALL raise
`django.core.exceptions.ImproperlyConfigured` at settings import, naming the variable, quoting
the raw value, and stating the violated rule. The loader SHALL NOT silently fall back to the
default, clamp the value, or defer the failure to first use, so a mis-set deployment knob is
loud at boot instead of silently inert.

#### Scenario: A non-numeric knob value names the variable and value
- **WHEN** the settings module is imported with `ART_SD_STEPS=twelve`
- **THEN** the import raises `ImproperlyConfigured` whose message names `ART_SD_STEPS`, quotes
  `twelve`, and states the integer expectation, and no partially configured settings module is
  usable

#### Scenario: A probe timeout below the floor is rejected
- **WHEN** the settings module is imported with `ART_SD_PROBE_TIMEOUT_MS=500`
- **THEN** the import fails naming `ART_SD_PROBE_TIMEOUT_MS`, quoting `500`, and stating the
  1000-to-60000 rule, and no value falls back silently

#### Scenario: An out-of-range cache lifetime is rejected
- **WHEN** the settings module is imported with `ART_SD_PROBE_CACHE_SECONDS=2`
- **THEN** the import fails naming `ART_SD_PROBE_CACHE_SECONDS` and the 5-to-3600 rule

#### Scenario: A format outside the closed set is rejected
- **WHEN** the settings module is imported with `ART_SD_OUTPUT_FORMAT=heic`
- **THEN** the import fails naming `ART_SD_OUTPUT_FORMAT`, quoting `heic`, and stating the
  accepted set, and no value falls back silently

#### Scenario: A dimension that is not a multiple of 8 is rejected
- **WHEN** the settings module is imported with `ART_SD_PORTRAIT_WIDTH=777`
- **THEN** the import fails naming `ART_SD_PORTRAIT_WIDTH` and the multiple-of-8 rule

#### Scenario: A boolean word outside the word list is rejected
- **WHEN** the settings module is imported with `ART_SCHEDULER_ENABLED=maybe`
- **THEN** the import fails naming `ART_SCHEDULER_ENABLED` and the accepted word list, and the
  value is not interpreted as truthy
