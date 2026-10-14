# bundled-terminal-scene-art Specification

## Purpose
Provide complete lawful forest and town artwork as built-in scene members and terminal image resources without depending on sample-art licensing assumptions.

## Requirements

### Requirement: Forest and town terminals have their own real distributable art
The repository SHALL deliver distinct finished forest_path and city_street WebP landscapes with lawful distribution records, actual production provenance and checksums. Both SHALL decode within current image resource limits and be available without operator art or runtime generation.

#### Scenario: Terminals display their actual scenes
- **WHEN** the two actual static resources are decoded in the browser
- **THEN** forest depicts a forest path and city depicts a town street with usable full-bleed composition, not placeholders or identical renamed bytes

#### Scenario: Rights are established before use
- **WHEN** existing sample bytes have no established redistribution permission
- **THEN** complete lawful originals are produced within this artwork change, rather than transferring uncertain reproduction work to catalog
