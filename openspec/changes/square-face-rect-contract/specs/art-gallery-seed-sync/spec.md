# art-gallery-seed-sync — delta for square-face-rect-contract

## MODIFIED Requirements

### Requirement: An optional per-subject manifest declares the default and the face rectangle
A subject's seed folder MAY contain a `manifest.json` declaring a `default` filename and a
`face_rect`. When present and valid, the named file's card SHALL become the subject's default and the
declared rectangle SHALL be validated by the standard face-rect rules and applied to that subject's
seed cards. The standard rules include the pixel-square contract, and the manifest's rect is applied
across every eligible image of the subject, so before either manifest field is honored the sync
SHALL decode the pixel sizes of the subject's eligible images and require the declared rectangle to
be pixel-square for every one of them (an undecodable or missing size degrades the manifest the same
way an invalid rect does — a rectangle square on two different aspect ratios only coincidentally
exists). When the manifest is absent, unreadable, or invalid, the first file by sorted name SHALL
be the default candidate and seed cards SHALL each take the fitted default square for that card's
own decoded `image_size`, with one bounded diagnostic for an invalid manifest. A manifest default
SHALL apply only when the subject has no `default_image_id` yet, so a player's chosen default is
never overwritten by a later restart.

#### Scenario: A manifest selects the default and the rectangle
- **WHEN** a subject's seed folder declares a valid manifest naming one of its files and a rectangle that is pixel-square for every eligible image of that subject
- **THEN** that file's card becomes the subject's default and the seed cards carry the declared rectangle

#### Scenario: No manifest falls back to sorted order and the shared rectangle
- **WHEN** a subject's seed folder has no manifest
- **THEN** the first file by sorted name is the default candidate and each seed card carries the shared default rectangle as fitted to that card's own image (the fitted default square computed from its decoded pixel size)

#### Scenario: A rectangle square for only some of the subject's images degrades whole
- **WHEN** a manifest declares a rectangle that is pixel-square for one eligible image but not for another of the same subject's eligible images
- **THEN** one bounded invalid-rect diagnostic is logged, neither the manifest default nor the rectangle is honored, the sorted-name rule applies, cards take their fitted defaults, and synchronization continues

#### Scenario: An invalid manifest degrades with one diagnostic
- **WHEN** a manifest is unreadable, is not an object, names a missing file, or declares an invalid or non-square rectangle
- **THEN** one bounded diagnostic is logged, the sorted-name and fitted-default rules apply, and synchronization continues

#### Scenario: A player's chosen default survives a restart
- **WHEN** a subject already has an explicitly chosen default and its manifest names a different file
- **THEN** the chosen default is preserved across the synchronization
