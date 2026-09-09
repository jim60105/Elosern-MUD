## MODIFIED Requirements

### Requirement: Deployment settings accept typed environment overrides
`server/conf/settings.py` SHALL derive the initial value of every deployment-tunable setting it
declares in the `ART_SD_*`, `ART_REMBG_*`, `ART_SCHEDULER_*`, `ELOSERN_VUE_CLIENT`,
`ELOSERN_MAX_CHARACTERS`, and `DEFEAT_ADULT_SCENES` groups from an environment
variable, using typed conversion at settings import. The env-backed set is exactly:
`ART_SD_TIMEOUT_SECONDS`, `ART_SD_STEPS`, `ART_SD_CFG_SCALE`, `ART_SD_SAMPLER`,
`ART_SD_SCHEDULER`, `ART_SD_CHECKPOINT`, `ART_SD_STYLES`, `ART_SD_MODULES`,
`ART_SD_SCENE_WIDTH`, `ART_SD_SCENE_HEIGHT`, `ART_SD_PORTRAIT_WIDTH`, `ART_SD_PORTRAIT_HEIGHT`,
`ART_SD_MAX_RESPONSE_BYTES`, `ART_SD_MAX_IMAGE_DIMENSIONS`, `ART_SD_MAX_IMAGE_PIXELS`,
`ART_SD_PREPIN_SAMPLES_FORMAT`, `ART_SD_OUTPUT_FORMAT`, `ART_SD_OUTPUT_QUALITY`,
`ART_SD_PRESERVE_GENERATION_METADATA`, `ART_SD_PROBE_TIMEOUT_MS`, `ART_SD_PROBE_CACHE_SECONDS`,
`ART_REMBG_ENABLED`, `ART_REMBG_MODEL`, `ART_REMBG_DOWNLOAD_ENABLED`,
`ART_REMBG_ALLOWANCE_SECONDS`, `ART_REMBG_THREADS`,
`ART_SCHEDULER_ENABLED`, `ART_SCHEDULER_INTERVAL_SECONDS`, `ART_SCHEDULER_LIMIT`,
`ELOSERN_VUE_CLIENT`, `ELOSERN_MAX_CHARACTERS`, and `DEFEAT_ADULT_SCENES` — each from a
variable of the same name — plus
`ART_SD_BASE_URL` from
`SD_WEBUI_BASE_URL` as fixed by the `internal-art-worker` spec. No other setting in these groups
SHALL read the environment; `ART_SD_CLIENT`, `ART_REMBG_BACKEND`, `ART_REMBG_MODEL_DIR`, the
derived `ART_SD_OUTPUT_EXTENSION`, and the auth
pair `ART_SD_USERNAME`/`ART_SD_PASSWORD` in particular SHALL NOT (see their own requirements).
(`DEFEAT_ADULT_SCENES` is not an addition of this change: the exact-set statement here repairs
a pre-existing omission — the setting has read its same-named environment variable in
`settings.py`, been popped by `test_settings.py`, and been carried by the AST inventory
contract test since before this change; the specification text simply never listed it.)
Conversion rules: integers for `ART_SD_TIMEOUT_SECONDS`, `ART_SD_STEPS`, the four
`ART_SD_{SCENE,PORTRAIT}_{WIDTH,HEIGHT}` dimensions, `ART_SD_MAX_RESPONSE_BYTES`,
`ART_SD_MAX_IMAGE_DIMENSIONS`, `ART_SD_MAX_IMAGE_PIXELS`, `ART_SCHEDULER_INTERVAL_SECONDS`, and
`ART_SCHEDULER_LIMIT`, each rejecting zero and negatives; an inclusive 1-to-100 integer for
`ART_SD_OUTPUT_QUALITY` (rejecting zero, negatives, and values above 100); an inclusive
1000-to-60000 integer for `ART_SD_PROBE_TIMEOUT_MS`, an inclusive 5-to-3600 integer for
`ART_SD_PROBE_CACHE_SECONDS`, an inclusive 10-to-1800 integer for
`ART_REMBG_ALLOWANCE_SECONDS` (default `120`), an inclusive 0-to-256 integer for
`ART_REMBG_THREADS` (default `0`, meaning the ONNX Runtime default thread count), and an
inclusive 1-to-10 integer for `ELOSERN_MAX_CHARACTERS`
(values below the lower bound or above the upper bound rejected);
a positive float for `ART_SD_CFG_SCALE`; case-insensitive boolean words (`1/true/yes/on` true,
`0/false/no/off` false, nothing else) for `ART_SD_PREPIN_SAMPLES_FORMAT`,
`ART_SD_PRESERVE_GENERATION_METADATA`, `ART_REMBG_ENABLED` (default `false`),
`ART_REMBG_DOWNLOAD_ENABLED` (default `true`), `ART_SCHEDULER_ENABLED`,
`DEFEAT_ADULT_SCENES` (default `true`), and
`ELOSERN_VUE_CLIENT`;
case-insensitive membership in the closed set `png|webp|jpeg|avif` for `ART_SD_OUTPUT_FORMAT`;
case-insensitive membership in the closed set
`bria-rmbg|isnet-anime|isnet-general-use|u2net|u2netp` for `ART_REMBG_MODEL` (default
`bria-rmbg`);
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
- **THEN** every `ART_SD_*`, `ART_REMBG_*`, `ART_SCHEDULER_*`, `ELOSERN_VUE_CLIENT`, and
  `MAX_NR_CHARACTERS` setting equals its documented default (including
  `ART_SD_PROBE_TIMEOUT_MS=5000`, `ART_SD_PROBE_CACHE_SECONDS=300`,
  `ART_REMBG_ENABLED=False`, `ART_REMBG_MODEL="bria-rmbg"`,
  `ART_REMBG_DOWNLOAD_ENABLED=True`, `ART_REMBG_ALLOWANCE_SECONDS=120`,
  `ART_REMBG_THREADS=0`, `DEFEAT_ADULT_SCENES=True`, and `MAX_NR_CHARACTERS=5`), and the server starts

#### Scenario: Valid overrides coerce to typed values
- **WHEN** the settings module is imported with `ART_SD_PROBE_TIMEOUT_MS=2000` and
  `ART_SD_PROBE_CACHE_SECONDS=60` in the environment
- **THEN** the settings are the integers `2000` and `60` respectively

#### Scenario: The removal knobs coerce to their typed values
- **WHEN** the settings module is imported with `ART_REMBG_ENABLED=on`,
  `ART_REMBG_MODEL=ISNET-ANIME`, `ART_REMBG_DOWNLOAD_ENABLED=off`,
  `ART_REMBG_ALLOWANCE_SECONDS=300`, and `ART_REMBG_THREADS=8`
- **THEN** the effective settings are `True`, the canonical lowercase `"isnet-anime"`,
  `False`, `300`, and `8`

#### Scenario: Out-of-range removal knobs fail settings load
- **WHEN** the settings module is imported with `ART_REMBG_ALLOWANCE_SECONDS=5`, then
  separately with `=2000`, then separately with `ART_REMBG_THREADS=-1`, then separately with
  `ART_REMBG_MODEL=segment-anything`, then separately with `ART_REMBG_ENABLED=maybe`
- **THEN** each import raises the named settings error identifying the variable, quoting the
  raw value, and stating the violated rule, and no value falls back silently

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
- **WHEN** the test settings module is imported with `ART_SD_PROBE_TIMEOUT_MS=1` and
  `ART_REMBG_ENABLED=true` present in the shell environment
- **THEN** the effective `ART_SD_PROBE_TIMEOUT_MS` for the test session is the documented
  default `5000` and the effective `ART_REMBG_ENABLED` is the documented default `False`

### Requirement: The client seam and art store root are never environment-configurable
`ART_SD_CLIENT` SHALL NOT read any environment variable: it is an import-executing dotted path,
and an environment-controlled seam would let any inherited process environment import arbitrary
code at engine startup. `ART_REMBG_BACKEND` SHALL likewise never read the environment, for the
identical reason: it is the second import-executing dotted-path seam in the art pipeline.
`ART_STORE_ROOT` SHALL likewise remain code-only so a mistyped value
cannot silently relocate generated art off the persistent volume, and `ART_REMBG_MODEL_DIR`
SHALL remain code-only under the same rule so a mistyped value cannot silently relocate the
~1 GB background-removal model artifact off its persistent volume. The auth pair
`ART_SD_USERNAME`/`ART_SD_PASSWORD` SHALL likewise never read the environment: they are
credentials, and `secret_settings.py` remains the only sanctioned location for secrets. All
of them SHALL keep their settings/`secret_settings.py` override paths. The single sanctioned
exception to the credential rule is `LLM_API_KEY`: it MAY be delivered through the environment
(see the LLM knob requirement), and this exception SHALL NOT extend to any other credential —
every non-LLM secret retains `secret_settings.py` as its only location.

#### Scenario: A hostile client-seam variable is ignored
- **WHEN** the settings module is imported with `ART_SD_CLIENT` set to any value in the environment
- **THEN** the effective `ART_SD_CLIENT` remains `world.art.sd_worker.SDWebUIClient` and no
  environment read for that name occurs

#### Scenario: A hostile removal-seam variable is ignored
- **WHEN** the settings module is imported with `ART_REMBG_BACKEND` set to any value in the
  environment
- **THEN** the effective `ART_REMBG_BACKEND` remains `world.art.cutout.RembgCutoutBackend` and
  no environment read for that name occurs

#### Scenario: An art-store variable is ignored
- **WHEN** the settings module is imported with `ART_STORE_ROOT` set in the environment
- **THEN** the effective `ART_STORE_ROOT` remains the `server/.art` path under `GAME_DIR`

#### Scenario: A model-directory variable is ignored
- **WHEN** the settings module is imported with `ART_REMBG_MODEL_DIR` set in the environment
- **THEN** the effective `ART_REMBG_MODEL_DIR` remains the `server/.rembg` path under `GAME_DIR`

#### Scenario: Credential variables are ignored
- **WHEN** the settings module is imported with `ART_SD_USERNAME` or `ART_SD_PASSWORD` set in the
  environment
- **THEN** the effective settings remain the empty-string defaults and no environment read for
  those names occurs

#### Scenario: The LLM key is the one credential knob that reads the environment
- **WHEN** the settings module is imported with `LLM_API_KEY=sk-test`
- **THEN** the resolved profile default map carries `api_key="sk-test"` for every layer, and
  no other credential variable is consulted from the environment
