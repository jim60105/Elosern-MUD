# Spec Delta

## Purpose

Produce one offline authoring-map image through a validated command with lossless output, machine-readable camera metadata and failure-safe resource and file ownership.

## ADDED Requirements

### Requirement: Capture invocation selects exactly one validated map view
The capture command SHALL validate one explicit view, applicable map identity, finite increasing bounds, positive integer pixel dimensions, view-scoped hidden layers and a matching supported output path before producing an image.

#### Scenario: Required identity and defaults
- **WHEN** capture_map.py runs from the source workspace with --view continent and --output overview.webp
- **THEN** it selects that workspace's continent, defaults to 1280 by 960, lossless webp and all applicable layers visible, fits the full map, and treats output as relative to the working directory

#### Scenario: Other map views
- **WHEN** --view settlement or --view interior is supplied
- **THEN** --map must resolve an existing document ID of that view; continent rejects --map and absent, unknown or wrong-view IDs fail

#### Scenario: Dimensions and bounds rejection
- **WHEN** bounds contain non-finite values or non-increasing axes, or width/height are noninteger or nonpositive
- **THEN** the invocation fails without publishing an image

#### Scenario: Hide-only layer vocabulary
- **WHEN** repeated --hide arguments name applicable layers, including repeated names
- **THEN** names are deduplicated and normalized; unknown/cross-view layers fail, all-hidden is accepted, and --show or any unknown flag is rejected

#### Scenario: Supported path and format
- **WHEN** format is webp or png with a matching filename extension and an existing output parent
- **THEN** the path is accepted; unsupported formats, mismatched extensions, missing parent, quality sliders, AVIF/JPEG or service URL flags are rejected without automatic setup

### Requirement: Capture publishes exact lossless images atomically
Capture SHALL encode a lossless WebP or PNG at the requested dimensions with device scale factor one and replace the destination only after complete successful encoding.

#### Scenario: Both lossless formats
- **WHEN** the same synthetic surface is captured as default WebP and explicit PNG
- **THEN** decoded images have the requested width/height and lossless pixels, and the command never silently switches formats

#### Scenario: Preserve an existing output on failure
- **WHEN** rendering, encoding, writing or final replacement fails with a previous destination image present
- **THEN** the previous image remains undamaged, no partial result is published, no success object identifies that old image as new output, and temporary output files are removed

### Requirement: Successful capture reports one structured result
Capture SHALL emit exactly one success JSON object on stdout only after image publication, reporting absolute image location, selected view and the actual expanded camera in the input coordinate frame.

#### Scenario: Result schema
- **WHEN** any supported view succeeds
- **THEN** stdout contains image_path, view, map_id, format, width, height, bounds, units, axes, hidden_layers and diagnostics; image_path is absolute, map_id is null for continent, bounds is [MIN_X,MIN_Y,MAX_X,MAX_Y], and no timestamps or session IDs are added

#### Scenario: Coordinate and diagnostic metadata
- **WHEN** continent, settlement and interior succeed with semantic diagnostics or repeated hides
- **THEN** units are respectively km, m and layout; axes identify east/north geography or right/down layout; bounds reflect aspect expansion, hidden_layers are normalized/deduplicated, diagnostics remain structured, and exit zero claims image production only

### Requirement: One shot capture closes resources and isolates failures
Capture SHALL use a disposable offline browser with bounded explicit readiness and close browser resources and temporary assets on success or failure, returning nonzero with stderr diagnostics and no success JSON on failure.

#### Scenario: Runtime failures
- **WHEN** arguments, sources, map identity, partition, dependencies, built assets, browser availability, readiness timeout, encoding or output publication prevent completion
- **THEN** a short actionable stderr message accompanies a nonzero exit, stdout has no success object, and missing dependencies are never installed automatically

#### Scenario: No service or browser session dependency
- **WHEN** the real one-shot command runs with no editor service, operator-browser access, runtime pnpm, HTTP server or external network assets
- **THEN** it produces one selected map image via local built assets and structured data, cleans up its own resources, leaves source/layout/partition/reference bytes untouched, and neither watches nor generates source/artifacts

#### Scenario: Bounded render readiness
- **WHEN** local fonts, terrain image or layout completion is delayed or fails
- **THEN** capture waits for explicit successful readiness within a bound, never a fixed sleep, and timeout follows the same nonpublishing cleanup path
