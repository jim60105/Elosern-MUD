# settings-environment-overrides delta specification

## MODIFIED Requirements

### Requirement: Deployment settings accept typed environment overrides
`server/conf/settings.py` SHALL derive the initial value of every deployment-tunable setting it
declares in the `ART_SD_*`, `ART_SCHEDULER_*`, and `ELOSERN_VUE_CLIENT` groups from an environment
variable, using typed conversion at settings import. The env-backed set is exactly:
`ART_SD_TIMEOUT_SECONDS`, `ART_SD_STEPS`, `ART_SD_CFG_SCALE`, `ART_SD_SAMPLER`,
`ART_SD_SCHEDULER`, `ART_SD_CHECKPOINT`, `ART_SD_STYLES`, `ART_SD_MODULES`,
`ART_SD_SCENE_WIDTH`, `ART_SD_SCENE_HEIGHT`, `ART_SD_PORTRAIT_WIDTH`, `ART_SD_PORTRAIT_HEIGHT`,
`ART_SD_MAX_RESPONSE_BYTES`, `ART_SD_MAX_IMAGE_DIMENSIONS`, `ART_SD_MAX_IMAGE_PIXELS`,
`ART_SD_PREPIN_SAMPLES_FORMAT`, `ART_SCHEDULER_ENABLED`, `ART_SCHEDULER_INTERVAL_SECONDS`,
`ART_SCHEDULER_LIMIT`, and `ELOSERN_VUE_CLIENT` — each from a variable of the same name — plus
`ART_SD_BASE_URL` from `SD_WEBUI_BASE_URL` as fixed by the `internal-art-worker` spec. No other
setting in these groups SHALL read the environment; `ART_SD_CLIENT` and the auth pair
`ART_SD_USERNAME`/`ART_SD_PASSWORD` in particular SHALL NOT (see their own requirements).
Conversion rules: integers for `ART_SD_TIMEOUT_SECONDS`, `ART_SD_STEPS`, the four
`ART_SD_{SCENE,PORTRAIT}_{WIDTH,HEIGHT}` dimensions, `ART_SD_MAX_RESPONSE_BYTES`,
`ART_SD_MAX_IMAGE_DIMENSIONS`, `ART_SD_MAX_IMAGE_PIXELS`, `ART_SCHEDULER_INTERVAL_SECONDS`, and
`ART_SCHEDULER_LIMIT`, each rejecting zero and negatives; a positive float for
`ART_SD_CFG_SCALE`; case-insensitive boolean words (`1/true/yes/on` true, `0/false/no/off`
false, nothing else) for `ART_SD_PREPIN_SAMPLES_FORMAT`, `ART_SCHEDULER_ENABLED`, and
`ELOSERN_VUE_CLIENT`; and free-text strings for `ART_SD_SAMPLER`, `ART_SD_SCHEDULER`,
`ART_SD_CHECKPOINT`, `ART_SD_STYLES`, and `ART_SD_MODULES`, whose empty value means "the server's
default" (for the two list knobs, "the field is omitted from the request"). The four dimensions
SHALL additionally be positive multiples of 8. A variable that is absent, or present-but-empty for
typed, boolean, and URL knobs, SHALL yield the documented code default; present-but-empty for a
free-text knob SHALL yield the empty "server default" value. For the same-named set, the
`.env.example` entry, the error message, and the setting SHALL be one string.

The test settings bootstrap `server/conf/test_settings.py` SHALL remove every env-backed
variable name from `os.environ` before importing the production settings, so a test run's
effective settings never depend on a developer's or CI runner's inherited shell environment.

#### Scenario: Unset variables keep the documented defaults
- **WHEN** the settings module is imported with none of the env-backed variables present in the
  environment
- **THEN** every `ART_SD_*`, `ART_SCHEDULER_*`, and `ELOSERN_VUE_CLIENT` setting equals its
  documented default and the server starts

#### Scenario: Valid overrides coerce to typed values
- **WHEN** the settings module is imported with `ART_SD_STEPS=12`, `ART_SD_CFG_SCALE=1.5`,
  `ART_SD_PREPIN_SAMPLES_FORMAT=True`, `ART_SD_CHECKPOINT=anima/animaika_v43.safetensors`,
  `ART_SD_STYLES=cinematic, portrait`, `ART_SCHEDULER_ENABLED=0`, and `ELOSERN_VUE_CLIENT=off`
  in the environment
- **THEN** the settings are the integer `12`, the float `1.5`, boolean `True`, that exact string,
  the exact string `"cinematic, portrait"`, boolean `False`, and boolean `False` respectively

#### Scenario: An empty dimension value falls back instead of poisoning the request
- **WHEN** `ART_SD_SCENE_WIDTH` is present but empty in the environment
- **THEN** `ART_SD_SCENE_WIDTH` equals the documented default rather than an empty or zero value

#### Scenario: Inherited deployment variables cannot perturb a test run
- **WHEN** the test settings module is imported with `ART_SD_STYLES=x` present in the shell
  environment
- **THEN** the effective `ART_SD_STYLES` for the test session is the documented default empty
  string

### Requirement: The client seam and art store root are never environment-configurable
`ART_SD_CLIENT` SHALL NOT read any environment variable: it is an import-executing dotted path,
and an environment-controlled seam would let any inherited process environment import arbitrary
code at engine startup. `ART_STORE_ROOT` SHALL likewise remain code-only so a mistyped value
cannot silently relocate generated art off the persistent volume. The auth pair
`ART_SD_USERNAME`/`ART_SD_PASSWORD` SHALL likewise never read the environment: they are
credentials, and `secret_settings.py` remains the only sanctioned location for secrets. All
three SHALL keep their settings/`secret_settings.py` override paths.

#### Scenario: A hostile client-seam variable is ignored
- **WHEN** the settings module is imported with `ART_SD_CLIENT` set to any value in the environment
- **THEN** the effective `ART_SD_CLIENT` remains `world.art.sd_worker.SDWebUIClient` and no
  environment read for that name occurs

#### Scenario: An art-store variable is ignored
- **WHEN** the settings module is imported with `ART_STORE_ROOT` set in the environment
- **THEN** the effective `ART_STORE_ROOT` remains the `server/.art` path under `GAME_DIR`

#### Scenario: Credential variables are ignored
- **WHEN** the settings module is imported with `ART_SD_USERNAME` or `ART_SD_PASSWORD` set in the
  environment
- **THEN** the effective settings remain the empty-string defaults and no environment read for
  those names occurs
