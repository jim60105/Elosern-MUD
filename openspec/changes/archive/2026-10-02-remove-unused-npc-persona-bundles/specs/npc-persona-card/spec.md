## MODIFIED Requirements

### Requirement: NPC persona metadata is a separate record
The effective card SHALL be stored only at the NPC's persona record. A separate NPC persona metadata record SHALL hold the card format version, the content-generation marker, a monotonic positive `persona_version`, and initialization provenance. Provenance SHALL be one of the closed kinds `profile`, `companion`, `import`, or `generated_quest`, carrying identifiers only and never prose. The retired `offline_bundle` kind SHALL be rejected before initialization/update writes; persisted metadata of that kind SHALL be unavailable under the existing read validation without repair, compatibility translation, or replacement characterization. Metadata SHALL never be stored inside the persona record and SHALL never be rendered into any prompt or look output.

#### Scenario: Metadata stays out of the persona record
- **WHEN** an NPC card is initialized from a profile
- **THEN** the persona record contains exactly the seven card fields, and the metadata record carries the format, generation, `persona_version` 1, and `{"kind": "profile", "profile": <key>}`

#### Scenario: Unknown provenance is rejected
- **WHEN** initialization is requested with a provenance kind outside the closed set or with a prose value
- **THEN** it is rejected before any write

#### Scenario: Retired bundle provenance fails closed
- **WHEN** initialization supplies `{"kind": "offline_bundle", "pool": "civilian", "bundle": "old_bundle"}` or an editor reads metadata carrying that retired kind
- **THEN** initialization rejects without persistence and the read returns unavailable without repairing, reselecting, rewriting or exposing the card
