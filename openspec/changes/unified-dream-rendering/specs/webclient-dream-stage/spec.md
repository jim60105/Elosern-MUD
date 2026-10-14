# Spec Delta

## MODIFIED Requirements

### Requirement: The dream is a full-stage AVG scene over its official artwork

While the committed `dream` panel state is open, the browser SHALL present the dream as one modal dialog covering the stage. The dialog SHALL be named by its visible title 雲上王座之夢 and SHALL contain these regions:
- the server-resolved scene artwork;
- a keepsake card naming the current story direction and the exits;
- a reply bar for free text;
- a message band that presents the narration and the goddess's lines under her name plate.

#### Scenario: Open dream renders the stage regions
- **WHEN** an open dream state with artwork is committed
- **THEN** a modal dialog shows the artwork, the keepsake card with four exit rows, the reply bar and the message band, and contains no `<details>` element

#### Scenario: Artwork fails to load
- **WHEN** the preferred exact dream official image fails
- **THEN** the bundled dream image then distinct town terminal are resolved through the shared scene lifecycle and reached failures remain local, without broken images

#### Scenario: An empty artwork URL is removed
- **WHEN** the optional exact official dream source is undeclared
- **THEN** the required bundled dream image displays without error styling and there is no inherited physical-location background

#### Scenario: A changed artwork URL is attempted afresh
- **WHEN** a relevant dream descriptor revision changes
- **THEN** the shared lifecycle recomputes its ordered attempts and ignores stale callbacks

#### Scenario: The surface stays flat and standard-styled
- **WHEN** the stage is rendered
- **THEN** it uses no nested disclosure widgets and surfaces no command syntax or JSON, and every button outside the 念頭 sheet's inline controls shares the client's standard button styling

#### Scenario: Dream wire ships atomically
- **WHEN** dream schema 3 is emitted
- **THEN** state.scene_art is the canonical descriptor, server read model and active validators/client renderer agree, and raw URL-only scene_art is rejected

#### Scenario: Dream art leaves lifecycle unchanged
- **WHEN** the dream descriptor resolves repeatedly
- **THEN** no physical-room/archetype generation is enqueued and sleep/session/dialogue/authoring state is unchanged

