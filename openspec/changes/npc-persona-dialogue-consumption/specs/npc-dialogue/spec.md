## MODIFIED Requirements

### Requirement: NPC dialogue degrades to greeting or silence offline

When the `npc_dialogue` layer is disabled, unreachable, or retry-exhausted, `generate_npc_reply` SHALL resolve to `None`, and the caller SHALL render that as the NPC's authored greeting when one is available, or as silence when it is not; the game SHALL remain fully playable with the LLM entirely offline, and no dialogue call SHALL change state or open a network connection. The authored greeting SHALL be the NPC's dialogue-table greeting when its table authors one, and otherwise the greeting authored by the NPC profile named in its persona provenance; a runtime card edit SHALL NOT change which line is presented.

#### Scenario: Offline dialogue falls back to the authored greeting
- **WHEN** the LLM is offline and the NPC has an authored greeting
- **THEN** the player receives the authored greeting with no state change and no network request

#### Scenario: Offline dialogue with no greeting is silence
- **WHEN** the LLM is offline and the NPC has neither a table greeting nor a profile greeting
- **THEN** the NPC stays silent and no state changes

#### Scenario: A profiled companion speaks its own offline greeting
- **WHEN** the LLM is offline and a free-form NPC without a scripted table carries profile provenance whose profile authors a greeting
- **THEN** the player receives that profile greeting verbatim, distinct from another profiled NPC's greeting, with no state change
