# internal-art-worker Specification

## Purpose
Defines the in-process SDWebUIClient that generates one image per art subject through a bounded /sdapi/v1/txt2img request driven by settings, degrading failures to bounded named error codes that carry the swallowed exception in the log. Requires prompts to be stored in the prompt library and the client to be injectable so tests never open a socket.

## Requirements

### Requirement: The internal sd-webui client generates images through txt2img with bounded validation
`world/art/sd_worker.py` SHALL provide an in-process `SDWebUIClient` that generates one image per art subject by POSTing a `/sdapi/v1/txt2img` request to the settings `ART_SD_BASE_URL` (default from the `SD_WEBUI_BASE_URL` environment variable, else `http://127.0.0.1:7860`) with a bounded wall-clock timeout (`ART_SD_TIMEOUT_SECONDS`, default 600) and returning the decoded PNG bytes.

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

#### Scenario: The request carries the documented payload
- **WHEN** a request body is built
- **THEN** it carries the rendered positive prompt, the rendered negative prompt, `steps` and `cfg_scale` from settings, `width`/`height` derived from the subject's aspect ratio (scene 16:9, portrait 3:4) from the `ART_SD_*` size settings, and `override_settings.samples_format: "png"` with `override_settings_restore_afterwards: true`

#### Scenario: Non-empty sampler, scheduler, and checkpoint pass through
- **WHEN** `ART_SD_SAMPLER`, `ART_SD_SCHEDULER`, or `ART_SD_CHECKPOINT` is non-empty
- **THEN** it passes through as `sampler_name`, `scheduler`, and `override_settings.sd_model_checkpoint` respectively

#### Scenario: The engine's only sd-webui connection point is off-reactor
- **WHEN** the HTTP call runs
- **THEN** it runs synchronously on a background thread (never the reactor thread) and is the only place the engine opens an sd-webui connection

#### Scenario: The transport is injectable
- **WHEN** tests or the browser harness need a deterministic fake
- **THEN** the client accepts an injectable transport callable so they can substitute one

#### Scenario: The default transport enforces deadline, scheme, and redirect rules
- **WHEN** the default transport performs an exchange
- **THEN** it enforces a total wall-clock deadline over the whole exchange (not just per-socket timeouts), restricts the scheme to `http`/`https`, and does not follow redirects

#### Scenario: Memory use is bounded across response decoding
- **WHEN** a response is received and decoded
- **THEN** the response body is read under `ART_SD_MAX_RESPONSE_BYTES`, the base64 payload decodes under the same bound, and the decoded PNG has an IHDR whose width, height, and total pixels stay within `ART_SD_MAX_IMAGE_DIMENSIONS` and `ART_SD_MAX_IMAGE_PIXELS`

### Requirement: Art generation failures degrade to bounded named error codes
`SDWebUIClient.generate()` SHALL map every failure mode to a named error carrying one of the bounded codes `sd_connection_error`, `sd_timeout`, `sd_http_error`, `sd_malformed_response`, `sd_no_image`, `sd_decode_error`, `sd_not_png`, `sd_response_too_large`, or `sd_image_dimensions_too_large`, and SHALL never raise an unbounded or unexpected exception into the caller.

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

#### Scenario: The worker settles each named error per subject
- **WHEN** `world/art/worker.py` observes a named error for one claimed subject
- **THEN** it catches the error per subject and settles that record `failed` with the bounded code, leaving every other claimed job unaffected

#### Scenario: Prompt, client-config, and internal errors carry their own bounded codes
- **WHEN** prompt-template render fails, resolving or constructing the `ART_SD_CLIENT` dotted path fails, or an unexpected internal error occurs
- **THEN** the subject settles `failed` with the bounded codes `sd_prompt_error`, `sd_client_config_error`, and `sd_internal_error` respectively, so every claimed subject reaches a terminal `done`/`failed` state and none stays `in_progress`

#### Scenario: A misbehaving sd-webui never makes the game unplayable
- **WHEN** the sd-webui is unreachable, timed out, or misbehaving
- **THEN** the deterministic game remains playable: records remain failed, presenters keep their truthful placeholders, and the queue retry path (`@art retry`) recovers after the service is restored

### Requirement: Art generation prompts are stored in the prompt library
The positive and negative image-generation prompts SHALL be defined in `prompts/art.yaml` under the keys `art.scene_prompt`, `art.portrait_prompt`, and `art.negative_prompt`, and SHALL be the only source of that prompt text — `world/art/sd_worker.py` SHALL render them through `render_prompt()` like every other generative layer and SHALL NOT embed prompt text as Python constants.

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

#### Scenario: The positive templates take the deterministic description
- **WHEN** `art.scene_prompt` and `art.portrait_prompt` are defined
- **THEN** they SHALL be templates accepting a `{description}` placeholder whose value is the deterministic subject description produced by `world/art/subjects.py` (scene sentence or character/monster template)

#### Scenario: The negative prompt carries no placeholders
- **WHEN** `art.negative_prompt` is defined
- **THEN** it SHALL be a plain text block with no placeholders

#### Scenario: Shipped template text follows the authoring skill and stays admin-tunable
- **WHEN** the shipped template text is authored
- **THEN** it follows the image-prompt-builder-nl skill's guidance and remains tunable by admins in the mounted `prompts/` folder without touching code

### Requirement: The client is injectable and tests never open a socket
`world/art/sd_worker.py` SHALL expose the client class through the settings `ART_SD_CLIENT` dotted path (default `world.art.sd_worker.SDWebUIClient`).

#### Scenario: The fake client replays a fixed PNG
- **WHEN** a test configures `ART_SD_CLIENT` to the fake and a job runs
- **THEN** the record becomes `done` with the fake's deterministic PNG bytes under the store root
  and no socket was opened

#### Scenario: The fake client scripts transport failures
- **WHEN** a test scripts a connection error, timeout, HTTP error, or malformed response on the
  fake
- **THEN** the record settles `failed` with the matching bounded code and no network connection
  was attempted

#### Scenario: A deterministic fake ships for networkless testing
- **WHEN** `world/art/fake_sd_client.py` is inspected
- **THEN** it provides a deterministic `FakeSDWebUIClient` with the same interface that replays fixed PNG fixtures and scripted transport failures without any network access

#### Scenario: No test ever opens a socket to an image service
- **WHEN** unit, integration, or browser tests run
- **THEN** tests and the browser harness inject the fake through `ART_SD_CLIENT` or an equivalent transport override, so no unit, integration, or browser test ever opens a socket to an image service

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

### Requirement: Portrait prompts compose a full-body figure on a backdrop the cutout stage can key
`art.portrait_prompt` SHALL compose a FULL-BODY character illustration — the whole figure from head to feet inside the frame — and SHALL NOT ask for a half-body, bust, or close-up crop. It SHALL ask for a flat, uniform, light backdrop, carrying at minimum the `simple background` and `white background` tags, and SHALL NOT ask for a painted, blurred, out-of-focus, textured, or scenic background.

#### Scenario: The shipped portrait prompt asks for a full body on a flat backdrop
- **WHEN** the shipped `art.portrait_prompt` is rendered for a portrait subject
- **THEN** the positive prompt asks for a full-body figure with head and feet in frame, carries the `simple background` and `white background` tags, and asks for no painted, blurred, out-of-focus, or scenic backdrop

#### Scenario: The negative prompt agrees with the positive composition
- **WHEN** the shipped `art.negative_prompt` is rendered
- **THEN** it carries background negatives (detailed or scenic background, gradient background) and crop negatives (close-up, cropped legs or feet) consistent with the portrait composition

#### Scenario: Scenes keep their painted background
- **WHEN** the shipped `art.scene_prompt` is rendered for a scene subject
- **THEN** it still composes foreground, midground, and background planes and carries no white-backdrop instruction

#### Scenario: The composition does not depend on the cutout setting
- **WHEN** a portrait request is built with `ART_REMBG_ENABLED` true and again with it false
- **THEN** the rendered positive and negative prompts are byte-identical in both runs

#### Scenario: The negative prompt cannot disagree with the portrait composition
- **WHEN** `art.negative_prompt` is defined alongside `art.portrait_prompt`
- **THEN** it carries the matching background and crop negatives so the two templates cannot disagree

#### Scenario: The composition is a pipeline contract
- **WHEN** the portrait-backdrop constraint is justified
- **THEN** it is a pipeline contract, not a taste preference: `art-portrait-cutout` runs its matting stage on exactly the subject kinds `art.portrait_prompt` serves, and a painted or blurred backdrop is the hardest input that stage can be handed

#### Scenario: The constraint holds regardless of the cutout setting
- **WHEN** a deployment does or does not set `ART_REMBG_ENABLED`
- **THEN** the constraint SHALL hold either way, so enabling the stage never requires a prompt edit and disabling it never leaves a prompt that only made sense with the stage on

#### Scenario: Scene prompts are exempt from the backdrop rule
- **WHEN** `art.scene_prompt` is considered
- **THEN** it SHALL be exempt: scene subjects are outside the cutout allowlist and SHALL keep composing their painted foreground, midground, and background planes

#### Scenario: The backdrop instruction MAY ride as trailing tags
- **WHEN** the portrait prompt is composed, given that the generation model accepts natural-language English together with danbooru-style tags
- **THEN** the backdrop instruction MAY ride as trailing tags beside the prose rather than being spelled out as a sentence

#### Scenario: Admin edits are the admin's decision, surfaced through the digest
- **WHEN** an admin edits the templates in the mounted `prompts/` folder
- **THEN** both templates remain admin-tunable; this requirement constrains what the SHIPPED text composes, and an admin edit that violates it is the admin's decision, surfaced through the existing rendered-prompt digest

### Requirement: Server-side generated-image retention is request-scoped and configurable
The txt2img client SHALL respect `ART_SD_SERVER_RETAIN_IMAGES`, defaulting to `True`. Each `/sdapi/v1/txt2img` request SHALL include the top-level boolean `save_images` with the setting's value, explicitly controlling the API's server-side saving gate rather than relying on its default of `false`.

#### Scenario: Enabled retention explicitly requests server saving
- **WHEN** a txt2img request is built with the default `ART_SD_SERVER_RETAIN_IMAGES=True`
- **THEN** its top-level `save_images` field is boolean `true`, neither `do_not_save_samples` nor `do_not_save_grid` appears anywhere in the request, and all existing generation parameters remain unchanged

#### Scenario: Disabled retention suppresses server samples and grids per request
- **WHEN** a txt2img request is built with `ART_SD_SERVER_RETAIN_IMAGES=False`
- **THEN** its top-level `save_images` field is boolean `false`, its top-level `do_not_save_samples` and `do_not_save_grid` fields are both boolean `true`, none appears in `override_settings`, and no retention-related server-options mutation is issued

#### Scenario: Disabled server retention does not disable the engine's art store
- **WHEN** a successful generation returns valid image bytes with server retention disabled
- **THEN** the engine processes and stores those bytes through the same existing art-store path as with retention enabled

#### Scenario: Disabled retention requests per-request suppression fields
- **WHEN** `ART_SD_SERVER_RETAIN_IMAGES` is `False`
- **THEN** the request SHALL also include the top-level boolean fields `do_not_save_samples: true` and `do_not_save_grid: true`, requesting that sd-webui save neither generated samples nor grids in its own outputs directory

#### Scenario: Enabled retention omits the suppression fields
- **WHEN** `ART_SD_SERVER_RETAIN_IMAGES` is `True`
- **THEN** both suppression fields SHALL be omitted entirely, enabling saving subject to the server's existing sample/grid output settings

#### Scenario: Retention is never an options mutation
- **WHEN** retention is configured
- **THEN** the fields SHALL NOT be placed in `override_settings`, and configuring retention SHALL NOT issue `/sdapi/v1/options` mutations

#### Scenario: Engine-side handling is mode-independent
- **WHEN** either retention mode is active
- **THEN** the engine's returned-image validation, local output processing, and art-store persistence SHALL remain unchanged

