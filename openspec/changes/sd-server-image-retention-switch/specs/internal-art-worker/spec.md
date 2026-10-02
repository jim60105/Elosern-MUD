## ADDED Requirements

### Requirement: Server-side generated-image retention is request-scoped and configurable

The txt2img client SHALL respect `ART_SD_SERVER_RETAIN_IMAGES`, defaulting to `True`. When it is `False`, each `/sdapi/v1/txt2img` request SHALL include the top-level boolean fields `do_not_save_samples: true` and `do_not_save_grid: true`, requesting that sd-webui save neither generated samples nor grids in its own outputs directory. When it is `True`, both fields SHALL be omitted entirely, preserving the server's existing behavior and defaults. The fields SHALL NOT be placed in `override_settings`, and configuring retention SHALL NOT issue `/sdapi/v1/options` mutations. The engine's returned-image validation, local output processing, and art-store persistence SHALL remain unchanged in either mode.

#### Scenario: Default retention leaves the request fields absent
- **WHEN** a txt2img request is built with the default `ART_SD_SERVER_RETAIN_IMAGES=True`
- **THEN** neither `do_not_save_samples` nor `do_not_save_grid` appears anywhere in the request, and all existing generation parameters remain unchanged

#### Scenario: Disabled retention suppresses server samples and grids per request
- **WHEN** a txt2img request is built with `ART_SD_SERVER_RETAIN_IMAGES=False`
- **THEN** its top-level `do_not_save_samples` and `do_not_save_grid` fields are both boolean `true`, neither appears in `override_settings`, and no retention-related server-options mutation is issued

#### Scenario: Disabled server retention does not disable the engine's art store
- **WHEN** a successful generation returns valid image bytes with server retention disabled
- **THEN** the engine processes and stores those bytes through the same existing art-store path as with retention enabled
