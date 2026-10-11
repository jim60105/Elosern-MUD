# Spec Delta

## MODIFIED Requirements

### Requirement: Character and monster portraits are stored with their background removed

`world/art/cutout.py` SHALL provide a background-removal stage that
`world/art/worker.py::_settle_one` applies to the PNG bytes returned by the sd-webui
client, BEFORE `world/art/formats.py::encode(...)`, so the encoded, written, and
published artifact is the transparent-background cutout. The stage SHALL be applied
when, and only when, `ART_REMBG_ENABLED` is true and the claimed record's subject kind
is a member of the module's closed `CUTOUT_SUBJECT_KINDS` allowlist.

#### Scenario: A character portrait is stored transparent
- **WHEN** the stage is enabled with an injected backend, the sd-webui double returns an
  opaque multi-pixel PNG, and a classic `portrait:character:<key>` job generates
  successfully
- **THEN** the record settles `done`, the stored file at
  `portrait/character/<key><extension>` decodes with an alpha channel carrying fully
  transparent pixels, its bytes differ from the same job's disabled-stage output, and the
  backend recorded exactly one call

#### Scenario: A monster portrait is stored transparent
- **WHEN** the stage is enabled, the sd-webui double returns an opaque multi-pixel PNG,
  and a classic `portrait:monster:<visual-key>` job for a registered visual species generates successfully
- **THEN** the record settles `done`, the stored file at
  `portrait/monster/<visual-key><extension>` decodes with an alpha channel carrying fully
  transparent pixels, and its bytes differ from the same job's disabled-stage output

#### Scenario: A gallery portrait job is cut out on the same terms
- **WHEN** the stage is enabled, the sd-webui double returns an opaque multi-pixel PNG,
  and a gallery job for a character subject and a gallery job for a monster subject each
  generate successfully
- **THEN** each appends exactly one card whose stored
  `gallery/<kind-directory>/<subject-key>/<image-id><extension>` file decodes with a
  transparent alpha channel differing from its disabled-stage output, and no classic
  record's committed output was touched

#### Scenario: Scene art never reaches the backend
- **WHEN** the stage is enabled and a `scene:<archetype>` job generates successfully
- **THEN** the injected backend recorded zero calls and the stored scene bytes are
  byte-for-byte equal to the bytes the same job produces with `ART_REMBG_ENABLED` false

#### Scenario: The disabled stage changes nothing
- **WHEN** `ART_REMBG_ENABLED` is false and a character portrait, a monster portrait, a
  gallery portrait job, and a scene job each generate successfully
- **THEN** the injected backend recorded zero calls and every stored artifact is
  byte-for-byte equal to the pre-change pipeline's output

#### Scenario: Every subject kind is classified by the allowlist
- **WHEN** the members of `ArtSubjectKind` are enumerated
- **THEN** each member is either present in `CUTOUT_SUBJECT_KINDS` or asserted absent by
  the contract test, so introducing a new kind fails the suite until it is classified

#### Scenario: One file per output across every consumer
- **WHEN** a portrait is generated, encoded, written, and published with the stage
  applied
- **THEN** the store, media route, presenter, and gallery card all reference exactly one
  file per output, as they did before the stage existed

#### Scenario: The gate covers both publication paths identically
- **WHEN** a portrait job settles through either the classic per-subject identity
  (`portrait/character/<key><extension>`, `portrait/monster/<key><extension>`) or the
  gallery per-image identity (`gallery/<kind-directory>/<subject-key>/<image-id><extension>`)
- **THEN** the gate is the subject kind derived from the claimed record, and a gallery
  portrait receives exactly the same cutout treatment as a classic portrait

#### Scenario: A kind outside the allowlist never touches the backend machinery
- **WHEN** a job for a subject kind outside the allowlist — `ArtSubjectKind.SCENE` in
  particular — settles with the stage enabled
- **THEN** no backend is resolved, no session is built, and no call is made, so the scene
  output stays byte-for-byte identical to the pre-change pipeline

#### Scenario: Disabling the stage leaves the pipeline byte-for-byte unchanged
- **WHEN** `ART_REMBG_ENABLED` is false
- **THEN** no subject of any kind reaches the backend and the entire pipeline is
  byte-for-byte unchanged

#### Scenario: Transparency tests drive an opaque multi-pixel fixture
- **WHEN** a test asserts that a stored portrait is transparent
- **THEN** it drives the sd-webui double with an OPAQUE, multi-pixel PNG fixture — never
  `fake_sd_client.DEFAULT_PNG`, which is a 1x1 already-transparent image and would
  satisfy the assertion with the stage disabled
- **AND** it asserts the stored bytes differ from the same job's disabled-stage output,
  so the transparency demonstrably originates in this stage

#### Scenario: The allowlist contains exactly the two portrait kinds
- **WHEN** the members of the closed `CUTOUT_SUBJECT_KINDS` allowlist are inspected
- **THEN** it contains exactly `ArtSubjectKind.CHARACTER` and `ArtSubjectKind.MONSTER`

#### Scenario: The allowlist is a membership test, never a SCENE negation
- **WHEN** the allowlist gate is implemented and maintained
- **THEN** it is an explicit membership test, never the negation of `ArtSubjectKind.SCENE`,
  so a subject kind added later must be classified deliberately rather than inheriting a
  cutout by default

