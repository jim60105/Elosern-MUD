# bundled-sacred-scene-art Specification

## Purpose
Provide finished, locally distributable scene-specific illustrations that remain available without image generation or an operator artwork mount.

## Requirements

### Requirement: Each supported pack scene has its own finished illustration
The repository SHALL deliver one distinct, finished WebP landscape for each of cave_interior, shrine_interior, dream_throne. Each illustration SHALL depict the named scene, support full-bleed desktop 16:9 composition, decode within existing image limits and remain available offline without runtime generation.

#### Scenario: cave_interior has appropriate real art
- **WHEN** the cave_interior static image is requested with external services unavailable
- **THEN** the actual image decodes, depicts that scene with an open foreground for stage figures, and contains no placeholder graphic, town/forest reuse, interface, watermark or readable lettering

#### Scenario: shrine_interior has appropriate real art
- **WHEN** the shrine_interior static image is requested with external services unavailable
- **THEN** the actual image decodes, depicts that scene with an open foreground for stage figures, and contains no placeholder graphic, town/forest reuse, interface, watermark or readable lettering

#### Scenario: dream_throne has appropriate real art
- **WHEN** the dream_throne static image is requested with external services unavailable
- **THEN** the actual image decodes, depicts that scene with an open foreground for stage figures, and contains no placeholder graphic, town/forest reuse, interface, watermark or readable lettering

### Requirement: Scene artwork is distributable with recorded provenance
Every delivered scene illustration SHALL have a source and license record permitting repository distribution, production provenance and a content checksum. Asset acceptance SHALL include human visual inspection; coverage or metadata alone SHALL NOT establish scene appropriateness.

#### Scenario: Provenance matches shipped bytes
- **WHEN** a reviewer checks the delivered pack
- **THEN** each file has lawful distribution terms, its actual production method/input and checksum recorded, and visual review confirms distinct scene identity and usable landscape composition

#### Scenario: Real serving works offline
- **WHEN** the pack is requested through the running application static media boundary
- **THEN** each asset returns image bytes that the browser decodes while generation and operator roots are absent
