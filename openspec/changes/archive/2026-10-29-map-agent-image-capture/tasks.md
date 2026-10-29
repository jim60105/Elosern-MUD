# Tasks

## 1. Locked command and invocation

- [x] 1.1 Consume the completed snapshot and local-entry interfaces, add Playwright/Pillow in the editor project's optional `capture` developer group through uv with its lock, and add the thin skill `capture_map.py` plus reusable `elosern_map_editor.capture` orchestration; verify explicit locked setup/browser installation and codec checks, with runtime `--no-sync` and actionable missing-environment/build/browser errors instead of installation, and document setup in the skill.
  - `capture = ["pillow>=11.0", "playwright==1.62.0"]` in `tools/map-editor/pyproject.toml` (pinned to the browser runtime the repository suites already install, so one Chromium build serves both) with `tools/map-editor/uv.lock` updated by uv; the group is optional, so the editor service and its default test environment still install neither.
  - `_require_runtime` gates on the built page, Pillow, `features.check("webp")` and Playwright with the exact setup command; `capture()` never installs anything and `main()` reports `browser_unavailable`/`runtime_missing`/`codec_missing`/`build_missing` with guidance.
- [x] 1.2 Implement strict argument/identity/path validation and normalized repeatable hide-only layers with every approved default; add discoverable subprocess tests in `tests/test_map_image_capture.py` for all three views, defaults, invalid flags/show/service URL, unknown/cross-view layers, duplicate hides, missing/wrong IDs, finite increasing bounds, positive integer dimensions, format/extension and existing-parent rules, and document the entire argument/layer tables including contents, defaults and units in the skill and relevant existing references.
  - `allow_abbrev=False`, no `--show`, per-view `LAYERS`, deduplicated/sorted hides, four finite bounds with strictly increasing axes, positive integer dimensions, case-insensitive suffix match and an existing parent; only the parent is resolved so replacing a symlink replaces the link.
  - Full tables in `.agents/skills/map-data-authoring/references/verification.md#capturing-an-image-of-a-map` and the summary in `SKILL.md`.

## 2. Render, encode and publish

- [x] 2.1 Load one snapshot, launch a disposable Chromium context at scale factor one, pass structured data to the local entry and await bounded explicit readiness; add real synthetic browser/subprocess tests for correct map orientation, bends, layout/fallback/exterior, two differing regional aspect ratios, interior Y conversion and exact dimensions, plus delayed/missing-font/terrain/layout timeout and no-HTTP/service behavior, and update map-editor developer execution documentation.
  - Viewport at `device_scale_factor=1` and blocked service workers; the payload is one structured argument to `window.renderMapCapture`; the deadline is a `Promise.race` against a 20 s timer, with separate 30 s navigation/action bounds — no fixed sleep.
  - Network denial aborts and records every HTTP(S) request and refuses a WebSocket by never connecting the routed socket to its server; any recorded attempt refuses the capture (`network_attempted`).
  - Orientation, bends, layout/fallback/exterior, regional aspect expansion and Y conversion are asserted by the subprocess cases and by the merged surface browser module; the new browser module adds exact stage pixels, delayed-face readiness and missing-script refusal.
- [x] 2.2 Encode lossless default WebP or explicit PNG from the completed map rectangle, stage in the destination directory and atomically replace only after complete encoding and pre-serialized result data; add independent decoded-pixel/size checks for both formats and fault-injected encoding/write/replace failures preserving an existing image with no partial publication or stale success, and document replacement/format semantics.
  - `[data-capture-stage]` is screenshotted as PNG, its decoded size is checked against the request, then Pillow encodes `WEBP(lossless=True)` or `PNG` from RGB; both formats decode to identical pixels.
  - `_publish` writes an exclusive sibling stage, flushes and `fsync`s it, then `os.replace`s; the destination is never opened for writing; the success JSON is serialized first; the stage is unlinked on every path.
  - Package tests inject `os.replace`, `os.fsync` and `PIL.Image.Image.save` failures and assert the previous image, empty stdout and no stage file.
- [x] 2.3 Emit only the agreed success JSON after publication, isolate stderr diagnostics and nonzero failure handling, and close browser/context/Playwright plus temporary assets on all paths; test every metadata field and expanded frame, semantic-WIP success, all-hidden capture, unavailable partition matrix, malformed sources/layouts, missing runtime assets and render/output failures, observing unchanged source/layout/partition/reference digests and no leaked browser/temp resources; document exit-zero meaning and refusal/cleanup behavior.
  - Exactly one ASCII-safe JSON object on stdout, written only after `os.replace`; `main()` maps `CaptureError` (and any leaked exception as `internal`) to short stderr and a nonzero exit with no success object.
  - Teardown closes page → context → browser → Playwright in a `finally` chain that swallows teardown errors so later closes still run; a recorded fake browser asserts that order on success and refusal.
  - Digests of sources, layouts, partition and reference index are compared before/after success and refusal; no `.tmp` remains.

## 3. Complete workflow and final acceptance

- [x] 3.1 Complete skill/reference examples for every view, regional bounds, multiple hidden layers and PNG; include source-document ID lookup, explicit partition regeneration-or-hide, actual read of `image_path`, explicit PNG rerun if WebP is unreadable, overview-then-region guidance and the separation of compressed bytes from model token accounting. Verify the examples by executing them against available maps, and review full parameter/layer coverage without permanent help-text/copy snapshots.
  - Executed the continent, settlement, interior, regional, multi-hide and PNG examples against this checkout under `unshare -rn`; every one produced an image and the two formats were actually opened by the agent's image reader.
  - No test pins help text or copy; only behavior is asserted.
- [x] 3.2 Register all new managed browser methods in `.github/browser-shards.json` and any Evennia-owned modules in their exact shard; associate each new requirement with matching discoverable assertions using CLI-generated canonical IDs from an equivalent merged spec tree and record any meaningful provisional active associations/reasons. Verify post-sync coverage has no uncovered requirement and never rely on package-only pytest discovery or fabricated IDs.
  - `web.tests.browser.test_map_image_capture.MapImageCaptureBrowserTest` added to shard 1 `files_a`; `tests.test_evennia_test_optimization_contract` passes with no unowned or stale method.
  - No `covers_requirement` annotation was added: the capability's canonical IDs only exist after the archive sync. The provisional association table below records the intended mapping for that step.
- [x] 3.3 Run the focused command test module and one affected managed browser class, then launch the real command with no editor service for representative repository continent/settlement/interior maps and actually read resulting WebP and PNG files. Record commands, actual tool-read support, map-only composition, readable Traditional Chinese labels, geography/topology, cleanup and unchanged digests in `docs/development/map-editor.md`; use synthetic fresh-partition evidence if the repository artifact is stale, never regenerate automatically or claim inspection from subprocess success.
  - Focused module 21 tests; managed browser class 6 tests; editor package capture tests 24.
  - Real runs used `unshare -rn` (empty network namespace), so the host's editor service was unreachable; all three views rendered in WebP and PNG and were opened and inspected. The image reader decoded both `image/webp` and `image/png`, so no PNG rerun was needed for compatibility. Every per-view layer was hidden in its own real run; each reported the same camera bounds.
  - The repository partition artifact was current in this checkout (`diagnostics: []` and no refusal), so no stale-hide path was needed for the real maps; the stale/malformed/missing matrix is established with synthetic workspaces.
  - `content/` and `world/` are unmodified (`git status`), and no stage or temporary file remained.
- [x] 3.4 Finish with `openspec validate map-agent-image-capture --strict` and `uv run --locked python -m tools.contract_gate` from root, confirm the prerequisite's shared-editor interaction smoke evidence remains applicable, and report only exercised results. Full managed browser suites and complete traceability evidence stay CI-owned; no player command documentation changes are needed.
  - `openspec validate map-agent-image-capture --strict` → valid; `tools.contract_gate` → all six gates passed (ADDED `map-image-capture` spec is not in `openspec/specs` yet, so traceability has no new uncovered requirement).
  - No frontend code changed: the shared surface and the interactive host are untouched, so §10.4's `MapSurfaceEditorSmokeBrowserTest` evidence still applies.

## Provisional requirement association (for the archive sync)

Canonical IDs (`map-image-capture::<slug>`) do not exist until the archive syncs
this delta into `openspec/specs/map-image-capture/spec.md`. While active, only
these nearest-current associations are meaningful; no `covers_requirement`
annotation was added, because a fabricated identifier would fail
`tools.spec_traceability check`.

| Delta requirement (scenario) | Planned discoverable evidence | Nearest current requirement / reason |
| --- | --- | --- |
| Capture invocation selects exactly one validated map view (identity/defaults, other views, bounds/dimensions, hide vocabulary, path/format) | `tests/test_map_image_capture.py::CaptureInvocationTests::test_continent_defaults_publish_one_lossless_image_with_camera_metadata`, `::test_settlement_and_interior_report_their_own_frames`, `::test_every_layer_can_be_hidden_and_the_camera_does_not_move`, `::test_repeated_hides_are_deduplicated_and_sorted`, `::CaptureRefusalTests::test_bad_flags_and_identity_publish_nothing`, `::test_layers_are_view_scoped`, `::test_bounds_and_dimensions_are_validated_before_rendering`, `::test_output_paths_are_validated_before_rendering`, `::test_map_identity_refusals_name_the_problem` | `map-capture-snapshots::capture-snapshots-are-confined-and-read-only` — it owns the loader's identity/view refusal that this command surfaces; the CLI layer above it is new. |
| Capture publishes exact lossless images atomically (both formats, preserve an existing output on failure) | `::test_both_formats_decode_to_the_same_lossless_pixels`, `::test_replacing_an_existing_image_is_atomic_and_reports_the_new_one`, `::CaptureRefusalTests::test_a_failed_render_preserves_an_existing_image`, `::test_a_refusal_after_a_success_still_reports_no_output`, `tools/map-editor/tests/test_capture.py` staging/encoder fault injections | No current owner: both the encoder and the atomic replacement are introduced here. |
| Successful capture reports one structured result (schema, coordinate/diagnostic metadata) | `::test_continent_defaults_publish_one_lossless_image_with_camera_metadata`, `::test_settlement_and_interior_report_their_own_frames`, `::test_explicit_regions_expand_to_each_output_aspect_ratio`, `::test_a_non_ascii_destination_survives_an_ascii_stdout` | `map-offline-rendering::capture-cameras-preserve-coordinate-frames-and-requested-extent` — the entry owns the frames; the command owns their machine-readable reporting. |
| One-shot capture closes resources and isolates failures (runtime failures, no service/browser dependency, bounded readiness) | `::CaptureReadOnlyTests::test_sources_layouts_partition_and_index_are_never_modified`, `::test_partition_refusals_explain_regenerate_or_hide`, `::test_structural_source_errors_refuse_the_capture`, `::test_the_command_needs_no_node_runtime_and_no_editor_service`; `web/tests/browser/test_map_image_capture.py::MapImageCaptureBrowserTest` (loader payload from `file://`, delayed face, missing script, publication/refusal with unchanged digests); `tools/map-editor/tests/test_capture.py` deadline/network/teardown probes | `map-offline-rendering::offline-map-rendering-is-isolated-and-map-only` — it owns the page's isolation; browser lifetime and cleanup are new here. |

## Review dispositions

- **Blocking, adopted:** WebSocket traffic was recorded but not denied, because
  `context.route` only intercepts HTTP(S) and `page.on("websocket")` is
  observational. Added `context.route_web_socket` with a handler that never
  connects the routed socket to its server; the attempt is recorded and the
  capture is refused. Closing the socket inside the handler deadlocked the sync
  dispatcher (found by a faulthandler probe), so the handler only records. A
  real WebSocket page is now a probe test.
- **Material, adopted:** with `ensure_ascii=False`, a non-UTF-8 stdout could
  fail *after* the destination was replaced. The success document is now
  ASCII-safe JSON; a regression test runs the command with
  `PYTHONIOENCODING=ascii` and a non-ASCII destination.
- **Material, adopted:** a genuine Pillow decode/encode failure escaped as a
  traceback because `main()` only caught `CaptureError`. `_encode_image` now
  translates `OSError`/`ValueError` into `encode_failed`, `main()` has a final
  catch-all (`internal`) so no path can print a traceback or leave a success
  object, and an injected `PIL.Image.Image.save` failure asserts nonzero exit,
  empty stdout and an untouched existing image.
- **Material, adopted:** the delayed-font browser test's Python-side elapsed
  time could be inflated by the synchronous route callback, so it could pass
  without proving readiness ordering. It now also asserts the browser's own
  `document.fonts.status` recorded immediately after the render promise
  settled.
- **Material, adopted (second review):** the ASCII-stdout regression ran the
  command with `-I`, which ignores `PYTHONIOENCODING`, so it did not exercise
  the condition it claimed. That one case now runs without `-I` (the
  environment is still scrubbed) so the ASCII stream encoding really applies.
- **Material, adopted (second review):** a failure writing the success object
  after `os.replace` (a closed pipe) exited through the generic handler while
  the image was already published, and `_report` itself could raise if stderr
  failed. Output delivery now raises `report_failed` naming the published
  image, `_report` is best-effort, and the skill/developer docs no longer
  claim that *every* failure preserves the previous file: they say replacement
  is the last filesystem step and state the published-then-unreported case.
- **Checked and sound (duck):** atomic staging/replacement and stage cleanup;
  teardown order and independent closes; readiness race (timer cleared, late
  rejection observed, no screenshot after a deadline); strict validation,
  suffix rules and parent resolution without following the final component;
  lossless claims (device scale factor 1, decoded-size check, `lossless=True`,
  lossless PNG); skill/reference defaults, units, layers, partition guidance
  and read-image workflow; shard registration; WebSocket interception without
  `connect_to_server` (no server connection, no dispatcher deadlock).
