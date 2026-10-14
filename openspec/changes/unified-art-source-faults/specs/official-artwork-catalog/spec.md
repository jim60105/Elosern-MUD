# Spec Delta

## MODIFIED Requirements

### Requirement: A missing or empty official root is a valid no-art configuration
An absent default optional root or healthy empty root SHALL remain valid offline configuration. Startup SHALL proceed without acquiring artwork. Explicitly configured unavailable roots and unreadable roots SHALL retain bounded availability-failure facts in the snapshot even when the admitted index is empty; absence without explicit bindings SHALL not create a fault.

#### Scenario: Startup with no artwork directory
- **WHEN** the server starts with the absent default optional root and no explicit artwork binding
- **THEN** startup completes with an empty index, one bounded catalog event reports normal absence, and no network or extraction occurs

#### Scenario: Ordinary gameplay never acquires artwork
- **WHEN** a player resolves any portrait while the catalog holds zero entries
- **THEN** resolution uses only the loaded snapshot and the existing chain, with no filesystem acquisition attempt

#### Scenario: Configured missing root remains a failure fact
- **WHEN** an explicitly configured official root is missing
- **THEN** startup succeeds but its snapshot and boundary diagnostic retain configured-root unavailability

### Requirement: The optional per-content manifest follows the seed-metadata convention
A content directory MAY carry a `manifest.json` declaring a `default` filename, a `face_rect`, and a `stage` placement, following the existing seed-metadata convention. When no valid explicit default is declared, the content's default image SHALL be the first valid image in deterministic filename order. An invalid or unreadable manifest SHALL emit bounded diagnostics and preserve source-scoped metadata/default faults while using safe deterministic selection and geometry; valid images SHALL still load.

#### Scenario: No manifest uses deterministic filename order
- **WHEN** a preset content directory holds three valid images and no manifest
- **THEN** its default image is the first filename in deterministic order

#### Scenario: An invalid manifest degrades without blocking images
- **WHEN** a manifest names a nonexistent default and malformed selected-source geometry
- **THEN** bounded diagnostics and attributable default/metadata facts remain before safe substitution; fitted geometry and valid images stay available

#### Scenario: A face rectangle invalid for one image is ignored for rendering
- **WHEN** a manifest declares a rectangle that fails validation against one of the images it would apply to
- **THEN** that rectangle is ignored and the fitted default rectangle is reported for that image, with a bounded diagnostic

#### Scenario: Absent-manifest behaviour uses fitted defaults
- **WHEN** a manifest is absent or rejected
- **THEN** fitted per-image geometry is used; genuine absence is normal and rejected applicable metadata retains its fault

#### Scenario: Image dimensions are decoded locally, never declared
- **WHEN** a manifest is authored for a content directory
- **THEN** image dimensions are decoded locally and are not required in the manifest

#### Scenario: No package-level metadata is required or honored
- **WHEN** artwork is admitted under the manifest convention
- **THEN** no mandatory top-level manifest, package ID, release number, declared checksum, or schema matrix is required or honored

#### Scenario: A missing manifest is normal
- **WHEN** a content directory carries no manifest
- **THEN** that is normal and emits no diagnostic

