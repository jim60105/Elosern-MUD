# Spec Delta

## MODIFIED Requirements

### Requirement: Every registered scene has complete required bundled artwork
Every registered normal archetype plus dream_throne SHALL have a required bundled official WebP and an authored terminal reference. The terminal SHALL be city_street or forest_path. Future archetypes SHALL add their declaration and real artwork together.

#### Scenario: Complete collection is valid
- **WHEN** the contract enumerates the scene registry and explicit dream type
- **THEN** every required image decodes within resource limits and every terminal points to a required image

#### Scenario: Broken coverage names its source
- **WHEN** a required image is absent or corrupt, a declaration is missing, or a terminal references an unregistered key
- **THEN** the contract fails naming the affected scene key; runtime still degrades without blocking gameplay
