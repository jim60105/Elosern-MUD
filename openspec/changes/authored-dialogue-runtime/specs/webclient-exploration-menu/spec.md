# Spec Delta

## MODIFIED Requirements

### Requirement: explore.talk_scripted invokes the deterministic dialogue API with keyword buttons
The scripted-talk action SHALL accept the closed authored topic/context/selection payload or the native generated keyword payload, selected by server source type. It SHALL re-resolve current presence and eligibility and invoke the same deterministic selection/service seam as text. Stale, unknown and mismatched source payloads SHALL reject without mutation.

#### Scenario: Scripted keyword buttons match authored behavior
- **WHEN** an actor submits the source-correct topic payload for a present authored host or native keyword payload for a generated host
- **THEN** the player receives the authored response exactly as `talk` would produce it

#### Scenario: An unregistered keyword rejects without writing
- **WHEN** an actor submits an unknown topic_id or source-inappropriate keyword_id
- **THEN** the adapter rejects with a stable reason, no response is fabricated, and no state is written

#### Scenario: A no-longer-present NPC rejects before any dialogue API
- **WHEN** an actor submits `explore.talk_scripted` for an NPC that was present at render but has since left the room
- **THEN** the adapter re-resolves the NPC from the actor's current location, rejects with a stable reason before calling the dialogue API, and no memory or component state changes

#### Scenario: A scripted reply opens the dialogue session
- **WHEN** an actor submits a valid `explore.talk_scripted` for a present host
- **THEN** the character's dialogue session names that NPC with the complete attributed scene or native generated line,
  recorded before the adapter's response is delivered

#### Scenario: Target resolution never trusts stale or remote references
- **WHEN** the `explore.talk_scripted` adapter re-resolves the NPC
- **THEN** it resolves only from the actor's current location's present contents — never a stored, remote, or ambiguous reference

#### Scenario: Scripted answers run the same seam as the talk command
- **WHEN** the adapter calls the dialogue response API
- **THEN** it uses the same deterministic seam the `talk` command uses, so an authored `ScriptedDialogue` host answers through stable topic selection with the same state effects as the command path
- **AND** the adapter obtains the actor from the authenticated session

#### Scenario: A successful exchange is recorded through the session seam
- **WHEN** `explore.talk_scripted` succeeds
- **THEN** the adapter records the exchange through the deterministic dialogue-session seam (the character-held session helper owned by `world.rules.dialogue`), does not invent a response, and does not assign dialogue or component state directly

#### Scenario: Any invalid scripted talk rejects without writing state
- **WHEN** the NPC is missing, no-longer-present, a non-host, the keyword is unregistered, or the NPC is present-but-unreachable
- **THEN** the adapter rejects with a stable code and message and does not write state
