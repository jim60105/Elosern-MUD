## MODIFIED Requirements

### Requirement: NPC dialogue degrades to greeting or silence offline

When the `npc_dialogue` layer is disabled, unreachable, or retry-exhausted, `generate_npc_reply` SHALL resolve to `None`, and the caller SHALL render that as the NPC's authored greeting when one is available, or as silence when it is not; the game SHALL remain fully playable with the LLM entirely offline, and no dialogue call SHALL change state or open a network connection. The authored greeting SHALL be resolved in order: the greeting stored in the NPC's own bounded per-instance offline-greeting field (seeded at build, author-editable, and overriding every authored default when set), then the NPC's dialogue-table greeting when its table authors one, then the greeting authored by the NPC profile named in its persona provenance; a runtime card edit SHALL NOT change the table or profile default, and the instance field speaks exactly its stored text.

#### Scenario: Offline dialogue falls back to the authored greeting
- **WHEN** the LLM is offline and the NPC has an authored greeting
- **THEN** the player receives the authored greeting with no state change and no network request

#### Scenario: Offline dialogue with no greeting is silence
- **WHEN** the LLM is offline and the NPC has no table greeting, no offline-greeting field text, and no profile greeting
- **THEN** the NPC stays silent and no state changes

#### Scenario: An NPC with an offline-greeting field speaks it offline
- **WHEN** the LLM is offline and a free-form NPC without a scripted table carries a non-empty offline-greeting field
- **THEN** the player receives that field's greeting verbatim, distinct from another such NPC's greeting, with no state change and without resolving any profile

#### Scenario: A profiled host speaks its profile greeting offline
- **WHEN** the LLM is offline, an NPC has no table greeting and an empty offline-greeting field, and its persona provenance names a profile that authors a greeting
- **THEN** the player receives that profile greeting verbatim with no state change
