# settings-environment-overrides Delta Spec

## ADDED Requirements

### Requirement: Deployment settings accept typed environment overrides
`server/conf/settings.py` SHALL derive the initial value of every deployment-tunable setting it
declares in the `ART_SD_*`, `ART_SCHEDULER_*`, and `ELOSERN_VUE_CLIENT` groups from an environment
variable, using typed conversion at settings import. The env-backed set is exactly:
`ART_SD_TIMEOUT_SECONDS`, `ART_SD_STEPS`, `ART_SD_CFG_SCALE`, `ART_SD_SAMPLER`,
`ART_SD_SCHEDULER`, `ART_SD_CHECKPOINT`, `ART_SD_SCENE_WIDTH`, `ART_SD_SCENE_HEIGHT`,
`ART_SD_PORTRAIT_WIDTH`, `ART_SD_PORTRAIT_HEIGHT`, `ART_SD_MAX_RESPONSE_BYTES`,
`ART_SD_MAX_IMAGE_DIMENSIONS`, `ART_SD_MAX_IMAGE_PIXELS`, `ART_SD_PREPIN_SAMPLES_FORMAT`,
`ART_SCHEDULER_ENABLED`, `ART_SCHEDULER_INTERVAL_SECONDS`, `ART_SCHEDULER_LIMIT`, and
`ELOSERN_VUE_CLIENT` — each from a variable of the same name — plus `ART_SD_BASE_URL` from
`SD_WEBUI_BASE_URL` as fixed by the `internal-art-worker` spec. No other setting in these groups
SHALL read the environment; `ART_SD_CLIENT` in particular SHALL NOT (see its own requirement).
Conversion rules: integers for `ART_SD_TIMEOUT_SECONDS`, `ART_SD_STEPS`, the four
`ART_SD_{SCENE,PORTRAIT}_{WIDTH,HEIGHT}` dimensions, `ART_SD_MAX_RESPONSE_BYTES`,
`ART_SD_MAX_IMAGE_DIMENSIONS`, `ART_SD_MAX_IMAGE_PIXELS`, `ART_SCHEDULER_INTERVAL_SECONDS`, and
`ART_SCHEDULER_LIMIT`, each rejecting zero and negatives; a positive float for
`ART_SD_CFG_SCALE`; case-insensitive boolean words (`1/true/yes/on` true, `0/false/no/off`
false, nothing else) for `ART_SD_PREPIN_SAMPLES_FORMAT`, `ART_SCHEDULER_ENABLED`, and
`ELOSERN_VUE_CLIENT`; and free-text strings for `ART_SD_SAMPLER`, `ART_SD_SCHEDULER`, and
`ART_SD_CHECKPOINT`, whose empty value means "the server's default". The four dimensions SHALL
additionally be positive multiples of 8. A variable that is absent, or present-but-empty for
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
  `ART_SCHEDULER_ENABLED=0`, and `ELOSERN_VUE_CLIENT=off` in the environment
- **THEN** the settings are the integer `12`, the float `1.5`, boolean `True`, that exact string,
  boolean `False`, and boolean `False` respectively

#### Scenario: An empty dimension value falls back instead of poisoning the request
- **WHEN** `ART_SD_SCENE_WIDTH` is present but empty in the environment
- **THEN** `ART_SD_SCENE_WIDTH` equals the documented default rather than an empty or zero value

#### Scenario: Inherited deployment variables cannot perturb a test run
- **WHEN** the test settings module is imported with `ART_SD_STEPS=12` present in the shell
  environment
- **THEN** the effective `ART_SD_STEPS` for the test session is the documented default `30`

### Requirement: Invalid environment values fail settings load with a named error
An environment variable that is present but cannot be coerced to its setting's declared type or
bounds — a non-integer `ART_SD_STEPS`, a non-boolean word for a boolean knob, a negative or
zero positive-bound integer, a non-positive `ART_SD_CFG_SCALE`, or a dimension that is not a
positive multiple of 8 — SHALL raise `django.core.exceptions.ImproperlyConfigured` at settings
import, naming the variable, quoting the raw value, and stating the violated rule. The loader
SHALL NOT silently fall back to the default, clamp the value, or defer the failure to first use,
so a mis-set deployment knob is loud at boot instead of silently inert.

#### Scenario: A non-numeric knob value names the variable and value
- **WHEN** the settings module is imported with `ART_SD_STEPS=twelve`
- **THEN** the import raises `ImproperlyConfigured` whose message names `ART_SD_STEPS`, quotes
  `twelve`, and states the integer expectation, and no partially configured settings module is
  usable

#### Scenario: A dimension that is not a multiple of 8 is rejected
- **WHEN** the settings module is imported with `ART_SD_PORTRAIT_WIDTH=777`
- **THEN** the import fails naming `ART_SD_PORTRAIT_WIDTH` and the multiple-of-8 rule

#### Scenario: A boolean word outside the word list is rejected
- **WHEN** the settings module is imported with `ART_SCHEDULER_ENABLED=maybe`
- **THEN** the import fails naming `ART_SCHEDULER_ENABLED` and the accepted word list, and the
  value is not interpreted as truthy

### Requirement: Configuration layers follow default, environment, secret precedence
The effective value of an environment-overridable setting SHALL be resolved in the order
code default < same-named environment variable < `server/conf/secret_settings.py`: the environment
assignment SHALL happen in `settings.py` above the existing `secret_settings` import, and a
setting defined in `secret_settings.py` SHALL therefore override the environment value without
any change to the import structure. Secrets (`SECRET_KEY` and equivalents) SHALL NOT be moved to
the environment: `secret_settings.py` remains their only sanctioned location.

#### Scenario: An environment value overrides the code default
- **WHEN** `ART_SD_TIMEOUT_SECONDS=120` is present and no `secret_settings` module defines it
- **THEN** the effective setting is the integer `120`

#### Scenario: A secret-settings value overrides the environment
- **WHEN** `ART_SD_TIMEOUT_SECONDS=120` is present and a `server.conf.secret_settings` module that
  defines `ART_SD_TIMEOUT_SECONDS = 90` is imported over it
- **THEN** the effective setting is `90` and no environment value reached it

### Requirement: The client seam and art store root are never environment-configurable
`ART_SD_CLIENT` SHALL NOT read any environment variable: it is an import-executing dotted path,
and an environment-controlled seam would let any inherited process environment import arbitrary
code at engine startup. `ART_STORE_ROOT` SHALL likewise remain code-only so a mistyped value
cannot silently relocate generated art off the persistent volume. Both SHALL keep their
settings/`secret_settings.py` override paths.

#### Scenario: A hostile client-seam variable is ignored
- **WHEN** the settings module is imported with `ART_SD_CLIENT` set to any value in the environment
- **THEN** the effective `ART_SD_CLIENT` remains `world.art.sd_worker.SDWebUIClient` and no
  environment read for that name occurs

#### Scenario: An art-store variable is ignored
- **WHEN** the settings module is imported with `ART_STORE_ROOT` set in the environment
- **THEN** the effective `ART_STORE_ROOT` remains the `server/.art` path under `GAME_DIR`

### Requirement: Environment inventory and configuration guide are version-controlled and exact
The repository SHALL track `.env.example` as the exact inventory of environment variables this
project reads: every active (uncommented) entry SHALL be a variable that `server/conf/settings.py`
or a documented external reader (Evennia's launcher, compose.yaml interpolation) actually reads,
and no variable the runtime ignores SHALL be presented as an entry. The repository SHALL provide a
Docsify developer guide at `docs/development/settings-and-environment.md`, linked from
`docs/_sidebar.md`, documenting the three configuration layers, their precedence, the full
variable inventory with types and defaults, what must stay in `secret_settings.py`, the
bare-metal export recipe, the restart-to-apply rule, and the procedure for making a future
setting env-overridable; the `ART_SD_*` table in `docs/gm/prompts.md` SHALL reference that guide.

#### Scenario: No dead variables are advertised
- **WHEN** the active entries of `.env.example` are parsed and each key is checked against the
  environment reads extracted from the `server/conf/settings.py` syntax tree and an explicit
  key-to-reader allow-list for external readers (launcher, compose.yaml, harness, tooling)
- **THEN** every key resolves to a real reader call-site (not a comment or docstring mention)
  and the check reports any key that has no reader

#### Scenario: The guide and its sidebar entry exist
- **WHEN** the documentation tree is inspected
- **THEN** `docs/development/settings-and-environment.md` exists, names every environment-overridable
  setting with its type, default, and validation rule, and `docs/_sidebar.md` links the page
