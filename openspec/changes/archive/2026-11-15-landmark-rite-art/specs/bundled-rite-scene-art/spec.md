# Spec Delta

## Purpose

Provide finished, locally distributable illustrations for the ten landmark rite scene archetypes that remain available without image generation or an operator artwork mount.

## ADDED Requirements

### Requirement: Each rite archetype has its own finished illustration
The repository SHALL deliver one distinct, finished WebP landscape for each registered rite scene archetype. Each illustration SHALL support full-bleed desktop 16:9 composition, decode within existing image limits and remain available offline without runtime generation.

#### Scenario: Pack decodes and is distinct
- **WHEN** the shipped rite scene files are decoded under the repository's image admission limits
- **THEN** every file decodes, is exactly 16:9 and within the byte bound, and no two files have the same content

### Requirement: Rite scene artwork is distributable with recorded provenance
Every delivered rite illustration SHALL have a source and license record permitting repository distribution, production provenance and a content checksum. Asset acceptance SHALL include human visual inspection; coverage or metadata alone SHALL NOT establish scene appropriateness.

#### Scenario: Provenance matches shipped bytes
- **WHEN** each provenance record is compared with its file
- **THEN** the recorded checksum, byte size and dimensions equal the file's, and the record carries its source, license, production and visual review sections
