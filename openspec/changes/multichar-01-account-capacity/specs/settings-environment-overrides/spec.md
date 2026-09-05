# Delta spec: settings-environment-overrides (multichar-01-account-capacity)

Adds `ELOSERN_MAX_CHARACTERS` to the env-backed set and its conversion rule. The requirement is
reproduced in full because the env-backed set is an exhaustive enumeration.

## MODIFIED Requirements

### Requirement: Deployment settings accept typed environment overrides
`server/conf/settings.py` SHALL derive the initial value of every deployment-tunable setting it
declares in the `ART_SD_*`, `ART_SCHEDULER_*`, `ELOSERN_VUE_CLIENT`, and
`ELOSERN_MAX_CHARACTERS` groups from an environment
variable, using typed conversion at settings import. The env-backed set is exactly:
`ART_SD_TIMEOUT_SECONDS`, `ART_SD_STEPS`, `ART_SD_CFG_SCALE`, `ART_SD_SAMPLER`,
`ART_SD_SCHEDULER`, `ART_SD_CHECKPOINT`, `ART_SD_STYLES`, `ART_SD_MODULES`,
`ART_SD_SCENE_WIDTH`, `ART_SD_SCENE_HEIGHT`, `ART_SD_PORTRAIT_WIDTH`, `ART_SD_PORTRAIT_HEIGHT`,
`ART_SD_MAX_RESPONSE_BYTES`, `ART_SD_MAX_IMAGE_DIMENSIONS`, `ART_SD_MAX_IMAGE_PIXELS`,
`ART_SD_PREPIN_SAMPLES_FORMAT`, `ART_SD_OUTPUT_FORMAT`, `ART_SD_OUTPUT_QUALITY`,
`ART_SD_PRESERVE_GENERATION_METADATA`, `ART_SD_PROBE_TIMEOUT_MS`, `ART_SD_PROBE_CACHE_SECONDS`,
`ART_SCHEDULER_ENABLED`, `ART_SCHEDULER_INTERVAL_SECONDS`, `ART_SCHEDULER_LIMIT`,
`ELOSERN_VUE_CLIENT`, and `ELOSERN_MAX_CHARACTERS` — each from a variable of the same name — plus
`ART_SD_BASE_URL` from
`SD_WEBUI_BASE_URL` as fixed by the `internal-art-worker` spec. No other setting in these groups
SHALL read the environment; `ART_SD_CLIENT`, the derived `ART_SD_OUTPUT_EXTENSION`, and the auth
pair `ART_SD_USERNAME`/`ART_SD_PASSWORD` in particular SHALL NOT (see their own requirements).
Conversion rules: integers for `ART_SD_TIMEOUT_SECONDS`, `ART_SD_STEPS`, the four
`ART_SD_{SCENE,PORTRAIT}_{WIDTH,HEIGHT}` dimensions, `ART_SD_MAX_RESPONSE_BYTES`,
`ART_SD_MAX_IMAGE_DIMENSIONS`, `ART_SD_MAX_IMAGE_PIXELS`, `ART_SCHEDULER_INTERVAL_SECONDS`, and
`ART_SCHEDULER_LIMIT`, each rejecting zero and negatives; an inclusive 1-to-100 integer for
`ART_SD_OUTPUT_QUALITY` (rejecting zero, negatives, and values above 100); an inclusive
1000-to-60000 integer for `ART_SD_PROBE_TIMEOUT_MS`, an inclusive 5-to-3600 integer for
`ART_SD_PROBE_CACHE_SECONDS`, and an inclusive 1-to-10 integer for `ELOSERN_MAX_CHARACTERS`
(values below the lower bound or above the upper bound rejected);
a positive float for `ART_SD_CFG_SCALE`; case-insensitive boolean words (`1/true/yes/on` true,
`0/false/no/off` false, nothing else) for `ART_SD_PREPIN_SAMPLES_FORMAT`,
`ART_SD_PRESERVE_GENERATION_METADATA`, `ART_SCHEDULER_ENABLED`, and `ELOSERN_VUE_CLIENT`;
case-insensitive membership in the closed set `png|webp|jpeg|avif` for `ART_SD_OUTPUT_FORMAT`;
free-text strings for `ART_SD_SAMPLER`, `ART_SD_SCHEDULER`, `ART_SD_CHECKPOINT`,
`ART_SD_STYLES`, and `ART_SD_MODULES`, whose empty value means "the server's default" (for the
two list knobs, "the field is omitted from the request"). The four dimensions SHALL additionally
be positive multiples of 8. `ELOSERN_MAX_CHARACTERS` SHALL be the initial value of Evennia's
`MAX_NR_CHARACTERS` setting, defaulting to `5`. A variable that is absent, or present-but-empty
for typed, boolean,
choice, and URL knobs, SHALL yield the documented code default; present-but-empty for a
free-text knob SHALL yield the empty "server default" value. For the same-named set, the
`.env.example` entry, the error message, and the setting SHALL be one string.

The test settings bootstrap `server/conf/test_settings.py` SHALL remove every env-backed
variable name from `os.environ` before importing the production settings, so a test run's
effective settings never depend on a developer's or CI runner's inherited shell environment.

#### Scenario: Unset variables keep the documented defaults
- **WHEN** the settings module is imported with none of the env-backed variables present in the
  environment
- **THEN** every `ART_SD_*`, `ART_SCHEDULER_*`, `ELOSERN_VUE_CLIENT`, and `MAX_NR_CHARACTERS`
  setting equals its documented default (including `ART_SD_PROBE_TIMEOUT_MS=5000`,
  `ART_SD_PROBE_CACHE_SECONDS=300`, and `MAX_NR_CHARACTERS=5`), and the server starts

#### Scenario: Valid overrides coerce to typed values
- **WHEN** the settings module is imported with `ART_SD_PROBE_TIMEOUT_MS=2000` and
  `ART_SD_PROBE_CACHE_SECONDS=60` in the environment
- **THEN** the settings are the integers `2000` and `60` respectively

#### Scenario: Probe bounds are inclusive at both ends
- **WHEN** the settings module is imported with `ART_SD_PROBE_TIMEOUT_MS=1000`, then separately
  with `=60000`, and `ART_SD_PROBE_CACHE_SECONDS` with `=5`, then separately with `=3600`
- **THEN** all four imports succeed producing the given values

#### Scenario: The character cap bounds are inclusive at both ends
- **WHEN** the settings module is imported with `ELOSERN_MAX_CHARACTERS=1`, then separately with
  `=10`
- **THEN** both imports succeed and `MAX_NR_CHARACTERS` equals `1` and `10` respectively

#### Scenario: An out-of-range character cap fails settings load
- **WHEN** the settings module is imported with `ELOSERN_MAX_CHARACTERS=0`, then separately with
  `=11`, then separately with a non-integer value
- **THEN** each import raises the named settings error identifying `ELOSERN_MAX_CHARACTERS` and
  its 1-to-10 rule, and the server does not start with a silently substituted value

#### Scenario: An empty dimension value falls back instead of poisoning the request
- **WHEN** `ART_SD_SCENE_WIDTH` is present but empty in the environment
- **THEN** `ART_SD_SCENE_WIDTH` equals the documented default rather than an empty or zero value

#### Scenario: Inherited deployment variables cannot perturb a test run
- **WHEN** the test settings module is imported with `ART_SD_PROBE_TIMEOUT_MS=1` present in the
  shell environment
- **THEN** the effective `ART_SD_PROBE_TIMEOUT_MS` for the test session is the documented default
  `5000`
