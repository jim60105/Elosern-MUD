# internal-art-worker Specification

## Purpose
TBD - created by archiving change internal-art-worker. Update Purpose after archive.
## Requirements
### Requirement: The internal sd-webui client generates images through txt2img with bounded validation
`world/art/sd_worker.py` SHALL provide an in-process `SDWebUIClient` that generates one image per
art subject by POSTing a `/sdapi/v1/txt2img` request to the settings `ART_SD_BASE_URL` (default
from the `SD_WEBUI_BASE_URL` environment variable, else `http://127.0.0.1:7860`) with a bounded
wall-clock timeout (`ART_SD_TIMEOUT_SECONDS`, default 600) and returning the decoded PNG bytes.
The request SHALL carry the rendered positive prompt, the rendered negative prompt, `steps` and
`cfg_scale` from settings, `width`/`height` derived from the subject's aspect ratio (scene 16:9,
portrait 3:4) from the `ART_SD_*` size settings, and `override_settings.samples_format: "png"`
with `override_settings_restore_afterwards: true`; a non-empty `ART_SD_SAMPLER`,
`ART_SD_SCHEDULER`, or `ART_SD_CHECKPOINT` SHALL pass through as `sampler_name`, `scheduler`, and
`override_settings.sd_model_checkpoint` respectively. The HTTP call SHALL run synchronously on a
background thread (never the reactor thread) and SHALL be the only place the engine opens an
sd-webui connection. The client SHALL accept an injectable transport callable so tests and the
browser harness can substitute a deterministic fake. The default transport SHALL enforce a total
wall-clock deadline over the whole exchange (not just per-socket timeouts), restrict the scheme
to `http`/`https`, and not follow redirects. The client SHALL bound memory use: the response
body SHALL be read under `ART_SD_MAX_RESPONSE_BYTES`, the base64 payload SHALL decode under the
same bound, and the decoded PNG SHALL have an IHDR whose width, height, and total pixels stay
within `ART_SD_MAX_IMAGE_DIMENSIONS` and `ART_SD_MAX_IMAGE_PIXELS`.

#### Scenario: A valid response produces PNG bytes for a scene subject
- **WHEN** `SDWebUIClient.generate()` POSTs a txt2img request for a scene subject and the server
  returns HTTP 200 with a JSON body whose `images[0]` decodes from base64 to PNG-magic bytes
  within the caps
- **THEN** the call returns exactly those decoded bytes and the request body contained the
  rendered scene prompt, the negative prompt, the configured steps/cfg, 16:9 dimensions, and the
  samples-format override

#### Scenario: A valid response produces PNG bytes for a portrait subject
- **WHEN** the same client generates for a portrait subject
- **THEN** the request carries the portrait prompt template's rendered text and 3:4 dimensions

#### Scenario: The request uses the configured generation parameters
- **WHEN** `ART_SD_SAMPLER`, `ART_SD_SCHEDULER`, and `ART_SD_CHECKPOINT` are non-empty
- **THEN** the request body includes those values as `sampler_name`, `scheduler`, and
  `override_settings.sd_model_checkpoint`, and when they are empty the fields are omitted so the
  server's defaults apply

#### Scenario: A generation never blocks the reactor thread
- **WHEN** a txt2img call is in flight against a slow endpoint
- **THEN** the call runs on a background worker thread and the Evennia reactor thread performs no
  blocking I/O

#### Scenario: A dribbling or stalled response is abandoned at the total deadline
- **WHEN** an endpoint sends headers but never completes the body within
  `ART_SD_TIMEOUT_SECONDS`
- **THEN** the client closes the connection at the total wall-clock deadline and the call fails
  with the bounded `sd_timeout` code

#### Scenario: An oversized response is rejected before unbounded allocation
- **WHEN** the response body, base64 payload, or decoded PNG dimensions exceed the configured
  caps
- **THEN** the call fails with `sd_response_too_large` or `sd_image_dimensions_too_large`, no
  unbounded memory is allocated, and nothing is written to the store

### Requirement: Art generation failures degrade to bounded named error codes
`SDWebUIClient.generate()` SHALL map every failure mode to a named error carrying one of the
bounded codes `sd_connection_error`, `sd_timeout`, `sd_http_error`, `sd_malformed_response`,
`sd_no_image`, `sd_decode_error`, `sd_not_png`, `sd_response_too_large`, or
`sd_image_dimensions_too_large`, and SHALL never raise an unbounded or unexpected exception into
the caller. `world/art/worker.py` SHALL catch each named error per subject and settle that record
`failed` with the bounded code, leaving every other claimed job unaffected. Prompt-template
render failures, failure to resolve or construct the `ART_SD_CLIENT` dotted path, and unexpected
internal errors SHALL likewise settle the subject `failed` with the bounded codes
`sd_prompt_error`, `sd_client_config_error`, and `sd_internal_error` respectively, so every
claimed subject reaches a terminal `done`/`failed` state and none stays `in_progress`. An
unreachable, timed-out, or misbehaving sd-webui SHALL therefore never make the deterministic
game unplayable: records remain failed, presenters keep their truthful placeholders, and the
queue retry path (`@art retry`) recovers after the service is restored.

#### Scenario: An unreachable server settles a bounded failure
- **WHEN** the configured base URL is unreachable
- **THEN** the subject's record becomes `failed` with error code `sd_connection_error` and no
  exception propagates to the drain caller

#### Scenario: A timed-out generation settles a bounded failure
- **WHEN** the endpoint does not respond within `ART_SD_TIMEOUT_SECONDS`
- **THEN** the record becomes `failed` with `sd_timeout` and the lease reclaim bound honors the
  worst-case batch duration

#### Scenario: A malformed response settles a bounded failure
- **WHEN** the endpoint returns non-JSON, an empty `images` array, undecodable base64, or bytes
  without the PNG magic
- **THEN** the record becomes `failed` with the matching bounded code (`sd_malformed_response`,
  `sd_no_image`, `sd_decode_error`, or `sd_not_png`) and nothing is written to the store

#### Scenario: A broken admin prompt settles a bounded failure
- **WHEN** the prompt library cannot render `art.scene_prompt`, `art.portrait_prompt`, or
  `art.negative_prompt` for a claimed subject
- **THEN** the subject settles `failed` with `sd_prompt_error`, the rest of the batch proceeds,
  and no subject is left `in_progress`

#### Scenario: A bad client configuration settles a bounded failure
- **WHEN** the `ART_SD_CLIENT` dotted path cannot be resolved or the client cannot be
  constructed
- **THEN** the claimed subjects settle `failed` with `sd_client_config_error` and no job is left
  `in_progress`

#### Scenario: One bad subject does not fail the batch
- **WHEN** one subject in a claimed batch raises a named `SDError`
- **THEN** that subject settles `failed` with its bounded code while the remaining subjects
  generate and settle independently

### Requirement: Art generation prompts are stored in the prompt library
The positive and negative image-generation prompts SHALL be defined in `prompts/art.yaml` under
the keys `art.scene_prompt`, `art.portrait_prompt`, and `art.negative_prompt`, and SHALL be the
only source of that prompt text — `world/art/sd_worker.py` SHALL render them through
`render_prompt()` like every other generative layer and SHALL NOT embed prompt text as Python
constants. `art.scene_prompt` and `art.portrait_prompt` SHALL be templates accepting a
`{description}` placeholder whose value is the deterministic subject description produced by
`world/art/subjects.py` (scene sentence or character/monster template); `art.negative_prompt`
SHALL be a plain text block with no placeholders. The shipped template text SHALL be authored per
the image-prompt-builder-nl skill's guidance and SHALL be tunable by admins in the mounted
`prompts/` folder without touching code.

#### Scenario: Scene and portrait prompts render the deterministic description
- **WHEN** the client builds a request for a scene subject and for a portrait subject
- **THEN** each positive prompt equals `render_prompt("art.scene_prompt", description=…)` or
  `render_prompt("art.portrait_prompt", description=…)` with the same deterministic description
  value the queue record carries

#### Scenario: The negative prompt renders without placeholders
- **WHEN** the client builds any request
- **THEN** the request's negative prompt equals `render_prompt("art.negative_prompt")` and the
  prompt library is the only place that text exists

#### Scenario: Editing a prompt template surfaces through the record digest, never silently
- **WHEN** an admin edits `art.scene_prompt`, `art.portrait_prompt`, or `art.negative_prompt`
  and a `done` subject is re-ensured
- **THEN** the record's rendered-prompt digest changes, the `hash_changed` staff-review flag is
  set, the completed image is left untouched, and `@art requeue` regenerates it with the prior
  valid output retained

### Requirement: The client is injectable and tests never open a socket
`world/art/sd_worker.py` SHALL expose the client class through the settings `ART_SD_CLIENT` dotted
path (default `world.art.sd_worker.SDWebUIClient`), and `world/art/fake_sd_client.py` SHALL
provide a deterministic `FakeSDWebUIClient` with the same interface that replays fixed PNG
fixtures and scripted transport failures without any network access. Tests and the browser
harness SHALL inject the fake through `ART_SD_CLIENT` or an equivalent transport override, so no
unit, integration, or browser test ever opens a socket to an image service.

#### Scenario: The fake client replays a fixed PNG
- **WHEN** a test configures `ART_SD_CLIENT` to the fake and a job runs
- **THEN** the record becomes `done` with the fake's deterministic PNG bytes under the store root
  and no socket was opened

#### Scenario: The fake client scripts transport failures
- **WHEN** a test scripts a connection error, timeout, HTTP error, or malformed response on the
  fake
- **THEN** the record settles `failed` with the matching bounded code and no network connection
  was attempted

### Requirement: Named degradation codes carry the swallowed exception in the log

Where the internal sd-webui client maps a failure to a named error code
(such as `sd_internal_error` or `sd_client_config_error`), the outward code
contract MUST stay unchanged, and the handler MUST emit a facade
`log_error`/`log_warn` event carrying the exception chain and, where
observable, the sd-webui endpoint identity — no failure may be reduced to a
code string alone.

#### Scenario: An internal worker failure is diagnosable beyond its code

- **WHEN** generation raises inside the worker and the record settles as
  `sd_internal_error`
- **THEN** the returned code is unchanged and the log line carries the
  exception type, message, and origin frame in its `tb:` segment
