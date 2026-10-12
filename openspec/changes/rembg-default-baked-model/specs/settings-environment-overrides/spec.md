# Spec Delta

## MODIFIED Requirements

### Requirement: Deployment settings accept typed environment overrides
`server/conf/settings.py` SHALL derive the initial value of every deployment-tunable setting it
declares in the `ART_SD_*`, `ART_REMBG_*`, `ART_TRANSLATE_*`, `ART_SCHEDULER_*`,
`ELOSERN_VUE_CLIENT`, `ELOSERN_MAX_CHARACTERS`, `DEFEAT_ADULT_SCENES`, and `HTTP_USER_AGENT`
groups from a same-named environment variable; except `ART_SD_BASE_URL`, which reads
`SD_WEBUI_BASE_URL` as fixed by the `internal-art-worker` spec; using typed conversion at
settings import. `ART_REMBG_MODEL` SHALL be removed from the settings and environment
inventory, with no replacement model-selection parameter or choice validation.

#### Scenario: Unset variables keep the documented defaults
- **WHEN** the settings module is imported with none of the env-backed variables present in the
  environment
- **THEN** every `ART_SD_*`, `ART_REMBG_*`, `ART_TRANSLATE_*`, `ART_SCHEDULER_*`, `ELOSERN_VUE_CLIENT`, and
  `MAX_NR_CHARACTERS` setting equals its documented default (including
  `ART_SD_PROBE_TIMEOUT_MS=5000`, `ART_SD_PROBE_CACHE_SECONDS=300`,
  `ART_REMBG_ENABLED=False`,
  `ART_REMBG_DOWNLOAD_ENABLED=True`, `ART_REMBG_ALLOWANCE_SECONDS=120`,
  `ART_REMBG_THREADS=0`, `ART_TRANSLATE_ENABLED=False`,
  `ART_TRANSLATE_DOWNLOAD_ENABLED=True`, `ART_TRANSLATE_THREADS=0`,
  `DEFEAT_ADULT_SCENES=True`, `HTTP_USER_AGENT=elosern-mud/1.0`, and `MAX_NR_CHARACTERS=5`), and the server starts

#### Scenario: Valid overrides coerce to typed values
- **WHEN** the settings module is imported with `ART_SD_PROBE_TIMEOUT_MS=2000` and
  `ART_SD_PROBE_CACHE_SECONDS=60` in the environment
- **THEN** the settings are the integers `2000` and `60` respectively

#### Scenario: The removal knobs coerce to their typed values
- **WHEN** the settings module is imported with `ART_REMBG_ENABLED=on`,
  `ART_REMBG_DOWNLOAD_ENABLED=off`, `ART_REMBG_ALLOWANCE_SECONDS=300`, and `ART_REMBG_THREADS=8`
- **THEN** the effective settings are `True`, `False`, `300`, and `8`
- **AND** no model choice is part of this typed override surface

#### Scenario: Out-of-range removal knobs fail settings load
- **WHEN** the settings module is imported with `ART_REMBG_ALLOWANCE_SECONDS=5`, then
  separately with `=2000`, then separately with `ART_REMBG_THREADS=-1`, then separately with
  `ART_REMBG_ENABLED=maybe`
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

#### Scenario: A blank user-agent override falls back to the documented identity
- **WHEN** the settings module is imported with `HTTP_USER_AGENT` present but empty, then
  separately whitespace-only, then separately absent
- **THEN** each import yields the documented default `elosern-mud/1.0`, never an empty value

#### Scenario: A user-agent override is used stripped and verbatim
- **WHEN** the settings module is imported with `HTTP_USER_AGENT` set to a non-blank value
  padded with surrounding spaces
- **THEN** the effective setting is that value stripped of the surrounding whitespace and
  otherwise byte-for-byte unchanged, with no case folding and no character rejection

#### Scenario: Inherited deployment variables cannot perturb a test run
- **WHEN** the test settings module is imported with `ART_SD_PROBE_TIMEOUT_MS=1` and
  `ART_REMBG_ENABLED=true` present in the shell environment
- **THEN** the effective `ART_SD_PROBE_TIMEOUT_MS` for the test session is the documented
  default `5000` and the effective `ART_REMBG_ENABLED` is the documented default `False`

#### Scenario: Test settings force the translation air-gapped track
- **WHEN** the test settings module is imported, with `ART_TRANSLATE_DOWNLOAD_ENABLED=true`
  present in the shell environment in one run and absent in another
- **THEN** the effective `ART_TRANSLATE_DOWNLOAD_ENABLED` for the test session is `False`
  in both runs, overriding the documented code default `True`

#### Scenario: The translation switch coerces and rejects like every other boolean knob
- **WHEN** the settings module is imported with `ART_TRANSLATE_ENABLED=on` and
  `ART_TRANSLATE_DOWNLOAD_ENABLED=off`, then separately with `ART_TRANSLATE_ENABLED=off` and
  `ART_TRANSLATE_DOWNLOAD_ENABLED=on`, then separately with `ART_TRANSLATE_DOWNLOAD_ENABLED=maybe`
- **THEN** the first two yield `(True, False)` and `(False, True)` respectively, and the third
  raises the named settings error identifying `ART_TRANSLATE_DOWNLOAD_ENABLED`, quoting the raw
  value, and stating the boolean-word rule

#### Scenario: The translation thread cap is bounded at both ends
- **WHEN** the settings module is imported with `ART_TRANSLATE_THREADS=0`, then separately with
  `=256`, then separately with `=-1`, then separately with `=257`
- **THEN** the first two succeed producing `0` and `256`, and the last two each raise the named
  settings error identifying `ART_TRANSLATE_THREADS` and its 0-to-256 rule

#### Scenario: Server-retention defaults and boolean words are typed
- **WHEN** settings are imported with `ART_SD_SERVER_RETAIN_IMAGES` absent, then separately empty, then separately with each case-insensitive true word `1/true/yes/on` and false word `0/false/no/off`
- **THEN** absent and empty yield `True`, all true words yield boolean `True`, and all false words yield boolean `False`

#### Scenario: An invalid server-retention override fails closed
- **WHEN** settings are imported with `ART_SD_SERVER_RETAIN_IMAGES=maybe`
- **THEN** import raises `ImproperlyConfigured` naming `ART_SD_SERVER_RETAIN_IMAGES`, quoting `maybe`, and stating the accepted boolean-word rule, without silently using a default

#### Scenario: Inherited server-retention overrides cannot perturb tests
- **WHEN** the test-settings bootstrap imports production settings with `ART_SD_SERVER_RETAIN_IMAGES=false` or separately `ART_SD_SERVER_RETAIN_IMAGES=maybe` inherited from the shell
- **THEN** the bootstrap removes that variable before production settings import, the effective retention setting is the code default `True`, and the invalid inherited word cannot fail the test session

#### Scenario: The env-backed set is exactly the documented names
- **WHEN** the env-backed set is checked against `server/conf/settings.py`
- **THEN** it is exactly `ART_SD_TIMEOUT_SECONDS`, `ART_SD_STEPS`, `ART_SD_CFG_SCALE`, `ART_SD_SAMPLER`, `ART_SD_SCHEDULER`, `ART_SD_CHECKPOINT`, `ART_SD_STYLES`, `ART_SD_MODULES`, `ART_SD_SCENE_WIDTH`, `ART_SD_SCENE_HEIGHT`, `ART_SD_PORTRAIT_WIDTH`, `ART_SD_PORTRAIT_HEIGHT`, `ART_SD_MAX_RESPONSE_BYTES`, `ART_SD_MAX_IMAGE_DIMENSIONS`, `ART_SD_MAX_IMAGE_PIXELS`, `ART_SD_PREPIN_SAMPLES_FORMAT`, `ART_SD_OUTPUT_FORMAT`, `ART_SD_OUTPUT_QUALITY`, `ART_SD_SERVER_RETAIN_IMAGES`, `ART_SD_PRESERVE_GENERATION_METADATA`, `ART_SD_PROBE_TIMEOUT_MS`, `ART_SD_PROBE_CACHE_SECONDS`, `ART_REMBG_ENABLED`, `ART_REMBG_DOWNLOAD_ENABLED`, `ART_REMBG_ALLOWANCE_SECONDS`, `ART_REMBG_THREADS`, `ART_TRANSLATE_ENABLED`, `ART_TRANSLATE_DOWNLOAD_ENABLED`, `ART_TRANSLATE_THREADS`, `ART_SCHEDULER_ENABLED`, `ART_SCHEDULER_INTERVAL_SECONDS`, `ART_SCHEDULER_LIMIT`, `ELOSERN_VUE_CLIENT`, `ELOSERN_MAX_CHARACTERS`, `DEFEAT_ADULT_SCENES`, and `HTTP_USER_AGENT`; each from a variable of the same name; plus `ART_SD_BASE_URL` from `SD_WEBUI_BASE_URL`
- **AND** no other setting in these groups SHALL read the environment; `ART_SD_CLIENT`, `ART_REMBG_BACKEND`, `ART_REMBG_MODEL_DIR`, `ART_TRANSLATE_BACKEND`, `ART_TRANSLATE_MODEL_DIR`, the derived `ART_SD_OUTPUT_EXTENSION`, and the auth pair `ART_SD_USERNAME`/`ART_SD_PASSWORD` in particular SHALL NOT (see their own requirements)

#### Scenario: The exact-set statement's provenance is recorded
- **WHEN** the exact-set statement is read against the change history
- **THEN** `DEFEAT_ADULT_SCENES` is not an addition of this change: the exact-set statement repairs a pre-existing omission; the setting has read its same-named environment variable in `settings.py`, been popped by `test_settings.py`, and been carried by the AST inventory contract test since before this change; the specification text simply never listed it
- **AND** `HTTP_USER_AGENT` IS an addition of this change: the User-Agent is deployment-tunable request identity, neither a credential nor an import-executing dotted path, so the standing never-environment-configurable classes do not reach it

#### Scenario: Integer knobs convert within their declared bounds
- **WHEN** an integer knob is coerced at settings import
- **THEN** `ART_SD_TIMEOUT_SECONDS`, `ART_SD_STEPS`, the four `ART_SD_{SCENE,PORTRAIT}_{WIDTH,HEIGHT}` dimensions, `ART_SD_MAX_RESPONSE_BYTES`, `ART_SD_MAX_IMAGE_DIMENSIONS`, `ART_SD_MAX_IMAGE_PIXELS`, `ART_SCHEDULER_INTERVAL_SECONDS`, and `ART_SCHEDULER_LIMIT` are integers, each rejecting zero and negatives, and `ART_SD_CFG_SCALE` is a positive float
- **AND** `ART_SD_OUTPUT_QUALITY` is an inclusive 1-to-100 integer (rejecting zero, negatives, and values above 100)
- **AND** `ART_SD_PROBE_TIMEOUT_MS` is an inclusive 1000-to-60000 integer and `ART_SD_PROBE_CACHE_SECONDS` an inclusive 5-to-3600 integer
- **AND** `ART_REMBG_ALLOWANCE_SECONDS` is an inclusive 10-to-1800 integer (default `120`)
- **AND** `ART_REMBG_THREADS` is an inclusive 0-to-256 integer (default `0`, meaning the ONNX Runtime default thread count) and `ART_TRANSLATE_THREADS` an inclusive 0-to-256 integer (default `0`, meaning the CTranslate2 default thread count)
- **AND** `ELOSERN_MAX_CHARACTERS` is an inclusive 1-to-10 integer (values below the lower bound or above the upper bound rejected)
- **AND** the four dimensions SHALL additionally be positive multiples of 8
- **AND** `ELOSERN_MAX_CHARACTERS` SHALL be the initial value of Evennia's `MAX_NR_CHARACTERS` setting, defaulting to `5`

#### Scenario: Boolean knobs accept only the documented boolean words
- **WHEN** a boolean knob is coerced at settings import
- **THEN** case-insensitive boolean words (`1/true/yes/on` true, `0/false/no/off` false, nothing else) apply to `ART_SD_PREPIN_SAMPLES_FORMAT`, `ART_SD_SERVER_RETAIN_IMAGES` (default `true`), `ART_SD_PRESERVE_GENERATION_METADATA`, `ART_REMBG_ENABLED` (default `false`), `ART_REMBG_DOWNLOAD_ENABLED` (default `true`), `ART_TRANSLATE_ENABLED` (default `false`), `ART_TRANSLATE_DOWNLOAD_ENABLED` (default `true`), `ART_SCHEDULER_ENABLED`, `DEFEAT_ADULT_SCENES` (default `true`), and `ELOSERN_VUE_CLIENT`

#### Scenario: Choice knobs accept only closed-set membership
- **WHEN** a choice knob is coerced at settings import
- **THEN** `ART_SD_OUTPUT_FORMAT` requires case-insensitive membership in the closed set `png|webp|jpeg|avif`

#### Scenario: Free-text knobs carry their empty and default semantics
- **WHEN** a free-text knob is coerced at settings import
- **THEN** `ART_SD_SAMPLER`, `ART_SD_SCHEDULER`, `ART_SD_CHECKPOINT`, `ART_SD_STYLES`, and `ART_SD_MODULES` take free-text strings whose empty value means "the server's default" (for the two list knobs, "the field is omitted from the request")
- **AND** `HTTP_USER_AGENT` takes a stripped free-text string with documented default `elosern-mud/1.0`, whose absent-or-blank value means that documented default rather than an empty sentinel; the header must never ship empty

#### Scenario: Absent and present-but-empty values resolve to their documented fallbacks
- **WHEN** an env-backed variable is absent, or present but empty
- **THEN** a variable that is absent, or present-but-empty for typed, boolean, choice, and URL knobs, SHALL yield the documented code default
- **AND** present-but-empty for a free-text knob SHALL yield the empty "server default" value, except that present-but-empty (or whitespace-only) for `HTTP_USER_AGENT` SHALL yield its documented default

#### Scenario: The same-named set uses one string everywhere
- **WHEN** the same-named env-backed set is rendered across the configuration surface
- **THEN** the `.env.example` entry, the error message, and the setting SHALL be one string

#### Scenario: The test bootstrap sanitizes the environment and pins the translation track
- **WHEN** the test settings bootstrap `server/conf/test_settings.py` runs
- **THEN** it SHALL remove every env-backed variable name from `os.environ` before importing the production settings, so a test run's effective settings never depend on a developer's or CI runner's inherited shell environment
- **AND** after the settings import, the test settings SHALL additionally pin `ART_TRANSLATE_DOWNLOAD_ENABLED = False`, so every test run sits on the translation air-gapped track regardless of the knob's code default; a test can never trigger a model download even when the shipped backend resolves against an unseeded directory

#### Scenario: The removed model variable is inert
- **WHEN** production settings load with the former `ART_REMBG_MODEL` environment name
  set to a previously accepted model and separately an unknown value
- **THEN** the project defines no corresponding setting and reads no such environment
  name, and neither value causes model-choice validation or changes cutout selection

#### Scenario: The test bootstrap and inventory drop the removed name
- **WHEN** the production environment-reader inventory, test-settings sanitation list,
  and settings test case tables are inspected
- **THEN** `ART_REMBG_MODEL` is absent from their supported knob/default/coercion/rejection
  entries, and the remaining rembg knobs keep their existing types and defaults

### Requirement: The client seam and art store root are never environment-configurable
`ART_SD_CLIENT` SHALL NOT read any environment variable: it is an import-executing dotted path,
and an environment-controlled seam would let any inherited process environment import arbitrary
code at engine startup. `ART_REMBG_BACKEND` and `ART_TRANSLATE_BACKEND` SHALL likewise never
read the environment; the rule is a class rule about import-executing dotted paths, not a list
that stops at two. All of these settings SHALL keep their settings/`secret_settings.py`
override paths.

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

#### Scenario: A hostile translation-seam variable is ignored
- **WHEN** the settings module is imported with `ART_TRANSLATE_BACKEND` set to any value in the
  environment
- **THEN** the effective `ART_TRANSLATE_BACKEND` remains its code default and no environment read
  for that name occurs

#### Scenario: A translation-model-directory variable is ignored
- **WHEN** the settings module is imported with `ART_TRANSLATE_MODEL_DIR` set in the environment
- **THEN** the effective `ART_TRANSLATE_MODEL_DIR` remains the `server/.translate` path under
  `GAME_DIR`

#### Scenario: Persistent-volume settings remain code-only
- **WHEN** settings resolve the art-store and model-directory knobs
- **THEN** `ART_TRANSLATE_MODEL_DIR` SHALL remain code-only under the persistent-volume rule, so a mistyped value cannot silently relocate the translation model artifact off its volume and turn every translation into a bounded unavailable
- **AND** `ART_STORE_ROOT` SHALL likewise remain code-only so a mistyped value cannot silently relocate generated art off the persistent volume
- **AND** `ART_REMBG_MODEL_DIR` SHALL remain code-only so a mistyped environment variable cannot silently relocate the background-removal artifact away from the baked image path or a bare-metal cache; `secret_settings.py` retains the explicit directory override

#### Scenario: Credentials never read the environment except the LLM key
- **WHEN** settings resolve the auth pair and secret surface
- **THEN** `ART_SD_USERNAME`/`ART_SD_PASSWORD` SHALL likewise never read the environment: they are credentials, and `secret_settings.py` remains the only sanctioned location for secrets
- **AND** the single sanctioned exception to the credential rule is `LLM_API_KEY`: it MAY be delivered through the environment (see the LLM knob requirement), and this exception SHALL NOT extend to any other credential; every non-LLM secret retains `secret_settings.py` as its only location

### Requirement: Environment inventory and configuration guide are version-controlled and exact
The repository SHALL track `.env.example` as the exact inventory of environment variables
this project reads: every active (uncommented) entry SHALL be a variable that
`server/conf/settings.py` or a documented external reader (Evennia's launcher, compose.yaml
interpolation) actually reads, and no variable the runtime ignores SHALL be presented as an
entry.

#### Scenario: No dead variables are advertised
- **WHEN** the active entries of `.env.example` are parsed and each key is checked against the
  environment reads extracted from the `server/conf/settings.py` syntax tree, the inert
  knob module's generated-name definition, and an explicit key-to-reader allow-list for
  external readers (launcher, compose.yaml, harness, tooling)
- **THEN** every key resolves to a real reader or a generated knob name (not a comment or
  docstring mention) and the check reports any key that has no reader

#### Scenario: Table-generated knobs match the inert definition exactly
- **WHEN** the inventory check compares the active global `LLM_*` entries of `.env.example`
  against the knob module's generated global names
- **THEN** the two sets are exactly equal, and no LLM knob needs an external-reader
  allow-list entry

#### Scenario: The api-key exception is documented with its risks
- **WHEN** `docs/development/settings-and-environment.md` is inspected
- **THEN** the `LLM_API_KEY` row/table names it as a scoped exception to the credential rule
  with its leak vectors and both mitigations, and the `ART_SD_USERNAME`/`ART_SD_PASSWORD`
  rows keep the prohibition unchanged

#### Scenario: The guide and its sidebar entry exist
- **WHEN** the documentation tree is inspected
- **THEN** `docs/development/settings-and-environment.md` exists, names every environment-overridable
  setting with its type, default, and validation rule, and `docs/_sidebar.md` links the page

#### Scenario: Knob-table reads are contract-checked against the inert definition
- **WHEN** the inventory check runs against environment reads generated by the LLM knob table
- **THEN** they SHALL be contract-checked against the inert knob module's pure `llm_env_names()` definition; exact set equality between the global `LLM_*` entries of `.env.example` and the function's global names, plus equality of `settings.LLM_ENV_NAMES` and the function; in addition to literal syntax-tree extraction for every other reader
- **AND** per-layer `LLM_<LAYER>_<SUFFIX>` names SHALL be documented through the global entries plus their documented suffix grammar rather than enumerated in `.env.example`

#### Scenario: The developer guide is the documentation of record
- **WHEN** the repository documentation is inspected
- **THEN** the repository SHALL provide a Docsify developer guide at `docs/development/settings-and-environment.md`, linked from `docs/_sidebar.md`, documenting the three configuration layers, their precedence, the full variable inventory with types and defaults, what must stay in `secret_settings.py`, the bare-metal export recipe, the restart-to-apply rule, and the procedure for making a future setting env-overridable
- **AND** the `ART_SD_*` table in `docs/gm/prompts.md` SHALL reference that guide

#### Scenario: The guide states the LLM_API_KEY exception with its risks
- **WHEN** the developer guide's credential section is inspected
- **THEN** the guide SHALL state the scoped `LLM_API_KEY` credential exception: its environment-delivery leak vectors (process listings via `/proc/<pid>/environ`, `podman compose config`, `docker inspect`) and its mitigations (compose `env_file:` instead of inline `environment:` entries; keeping the key out of the compose file and the rendered `compose config` output, while noting the key still lands in the container's process environment; or declining the exception and keeping the key in `secret_settings.py`, which keeps it out of the environment entirely)
- **AND** the guide SHALL keep every other credential under the standing prohibition

#### Scenario: The model-choice configuration and licence escape hatch are removed
- **WHEN** `.env.example`, the developer settings guide, and the GM prompt settings table
  are inspected
- **THEN** none advertises `ART_REMBG_MODEL` as a setting, supported environment variable,
  or example, and no ISNet replacement/requeue procedure is offered
- **AND** the remaining rembg knobs retain their documented types and defaults

#### Scenario: Model delivery documentation matches container and bare-metal behavior
- **WHEN** the rembg operator documentation and settings comments are inspected
- **THEN** they describe the sole default BRIA RMBG-2.0 weight and applicable publisher
  and operator licence responsibilities, build-time download and approximately 1.02 GB
  image payload, offline use of a transferred complete image without a rembg volume,
  and default-weight pre-seeding for bare-metal or custom model directories
- **AND** they state that `ART_REMBG_DOWNLOAD_ENABLED` governs missing-artifact runtime
  acquisition only, and a custom mount that masks the baked path must supply the weight
- **AND** translation-model acquisition retains its existing independent policy without
  claiming that rembg still requires a first-use container download
