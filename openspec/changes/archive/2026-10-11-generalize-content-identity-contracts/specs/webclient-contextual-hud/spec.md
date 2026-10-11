# Spec Delta

## MODIFIED Requirements

### Requirement: Stage actors present the player and the dialogue host with a speaking state
Each standing portrait on the stage SHALL be rendered by one stage-actor component. The controlled figure and companions in `actor-left` SHALL follow the companion-lineup rule. The dialogue host SHALL render once: when its committed identity joins to a committed party slot or controlled lineup figure, its existing lineup StageActor is the host and no duplicate renders in `actor-right`.

#### Scenario: The host actor presents its catalog entry truthfully
- **WHEN** a non-party host's stage actor renders in `actor-right`
- **THEN** it presents the committed `art` panel's `portrait_catalog` entry named by `dialogue.host.portrait_ref` — the complete image bottom-aligned with contain fit, and a grounded silhouette with host identity and authoritative availability when the entry is a placeholder; when `portrait_ref` is null or names no catalog entry it renders the truthful placeholder: the display name's initial and display name, never a stock or guessed image; and the client constructs no catalog key from host identity or any other field

#### Scenario: Foes follow the same presentation rule
- **WHEN** a foe's stage actor renders
- **THEN** it presents its committed catalog entry under the same complete-image, grounded-silhouette and display-name-placeholder rule

#### Scenario: Speaking follows dispatch state, never prose
- **WHEN** the committed mode is dialogue and the available host renders
- **THEN** stage actors carry a speaking state — the speaker at full brightness, listeners dimmed to 60% through the shared dim token; the host speaks except while an `explore.talk_scripted` or `explore.talk_freeform` action submitted by the player is in flight (from dispatch until its result is handled and declared presentation revision accepted, or until rejection), when the player speaks; the state derives from dispatch state, committed mode and panel availability, never prose

#### Scenario: Companions listen unless they are the host
- **WHEN** a companion's identity does, or does not, match the active host
- **THEN** companions remain listeners unless their identity matches that active host; a speaking companion temporarily receives the highest z without moving, then restores baseline z

#### Scenario: Nothing dims outside dialogue
- **WHEN** the mode is outside dialogue, or its panel is unavailable
- **THEN** the controlled figure remains lit and foes are never dimmed

#### Scenario: The speaking cue is never colour-only or disruptive
- **WHEN** a speaking state is active
- **THEN** the dim is not the only speaking cue — the name plate names the host and each actor exposes its speaking data attribute; actors remain decorative, with no focusable element; motion owns transitions; and no other dialogue behavior changes: the name plate, pagination, choices, focus, keyboard paths and non-party host mode-transition motion retain their contracts

#### Scenario: The host portrait comes from the art catalog
- **WHEN** a non-party host's dialogue panel names ref `"41"` and its catalog entry carries an image and face rectangle
- **THEN** the actor-right host renders that complete image bottom-aligned with contain fit and requests no other image source

#### Scenario: A pending or missing portrait shows the truthful placeholder
- **WHEN** the host's catalog entry is pending, and later a host named `測試人物` has a null ref
- **THEN** the first actor shows its grounded silhouette, identity and pending state; the second shows initial `測`, identity and missing state, with neither inventing an image

#### Scenario: The host speaks and the player is dimmed
- **WHEN** a conversation opens and its greeting commits
- **THEN** the host renders lit with `data-speaking="true"` and the player dimmed with `data-speaking="false"`; a companion host appears only in its raised existing slot

#### Scenario: The player is lit until the reply commits
- **WHEN** the player's scripted pick remains in flight until its reply revision is accepted
- **THEN** the player is lit and the host dim until that revision, then the host is lit and the player dim again

#### Scenario: A rejected choice returns the light to the host
- **WHEN** the player's freeform speech is rejected
- **THEN** rejection handling restores the host's light and the player's dim

#### Scenario: Nothing is dimmed outside dialogue
- **WHEN** mode is exploration and later combat with two active foes
- **THEN** the controlled figure is lit in both and both foes are lit in combat; companions retain their listener dim, and actor-right carries no exploration actor

#### Scenario: A companion host is not duplicated on the opposite anchor
- **WHEN** dialogue host identity joins to a committed party or controlled lineup figure
- **THEN** that identity has exactly one standing figure in actor-left, actor-right has no duplicate host, and the name plate, pagination and focus retain their existing behavior
