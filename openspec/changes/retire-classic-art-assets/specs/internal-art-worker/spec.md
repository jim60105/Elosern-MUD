## ADDED Requirements

### Requirement: Prompt library edits affect subsequent gallery requests only
The positive and negative image-generation prompts SHALL be defined in `prompts/art.yaml` under the keys `art.scene_prompt`, `art.portrait_prompt`, and `art.negative_prompt`, and SHALL be the only source of that prompt text — `world/art/sd_worker.py` SHALL render them through `render_prompt()` like every other generative layer and SHALL NOT embed prompt text as Python constants.

#### Scenario: Scene and portrait prompts render the deterministic description
- **WHEN** the client builds a request for a scene subject and for a portrait subject
- **THEN** each positive prompt equals `render_prompt("art.scene_prompt", description=…)` or
  `render_prompt("art.portrait_prompt", description=…)` with the same deterministic description
  value the queue record carries

#### Scenario: The negative prompt renders without placeholders
- **WHEN** the client builds any request
- **THEN** the request's negative prompt equals `render_prompt("art.negative_prompt")` and the
  prompt library is the only place that text exists

#### Scenario: Editing a prompt template affects new requests only
- **WHEN** an admin edits `art.scene_prompt`, `art.portrait_prompt`, or `art.negative_prompt`
  after a gallery card has been published
- **THEN** the existing card is unchanged; the next explicit gallery request captures the new prompt pair without a completed-record digest-review flag

#### Scenario: The positive templates take the deterministic description
- **WHEN** `art.scene_prompt` and `art.portrait_prompt` are defined
- **THEN** they SHALL be templates accepting a `{description}` placeholder whose value is the deterministic subject description produced by `world/art/subjects.py` (scene sentence or character/monster template)

#### Scenario: The negative prompt carries no placeholders
- **WHEN** `art.negative_prompt` is defined
- **THEN** it SHALL be a plain text block with no placeholders

#### Scenario: Shipped template text follows the authoring skill and stays admin-tunable
- **WHEN** the shipped template text is authored
- **THEN** it follows the image-prompt-builder-nl skill's guidance and remains tunable by admins in the mounted `prompts/` folder without touching code

## REMOVED Requirements

### Requirement: Art generation prompts are stored in the prompt library
**Reason**: Replaced by Prompt library edits affect subsequent gallery requests only; obsolete classic scenarios are removed while applicable gallery guarantees remain testable.

**Migration**: No compatibility reader or data migration. Recreate pre-release development databases. Gallery jobs/cards are the only runtime publication state.
