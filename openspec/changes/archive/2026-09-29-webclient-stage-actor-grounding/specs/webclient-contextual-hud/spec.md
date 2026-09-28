## ADDED Requirements

### Requirement: Standing portraits retain contours and truthful grounded fallbacks
Standing portraits SHALL retain their supplied image contours and align their feet or silhouette base with the stage floor. Missing artwork SHALL use a standing silhouette with the subject name and truthful availability state, without inventing generation or a URL. Repeated visual image captions SHALL be suppressed only on the stage; accessible identity and state SHALL remain available.

#### Scenario: Unavailable portrait is not generating
- **WHEN** an actor has missing or failed art
- **THEN** a grounded silhouette states the subject and missing or failed state once, and no generating shimmer runs

#### Scenario: Pending motion respects preference
- **WHEN** pending art renders at full, reduced and off motion
- **THEN** only full motion animates the silhouette; the pending label remains readable at every level

#### Scenario: Compact stage preserves labels
- **WHEN** the player silhouette, vitals and command line render at 1280x720
- **THEN** the silhouette identity and state are not occluded by vitals or the command line and all HUD controls remain reachable

## MODIFIED Requirements

### Requirement: Stage actors present the player and the dialogue host with a speaking state
Each standing portrait on the stage SHALL be rendered by one stage-actor component. The player's stage
actor in `actor-left` SHALL present the current roster character's portrait. The dialogue host's stage
actor in `actor-right` SHALL present the committed `art` panel's `portrait_catalog` entry named by the
committed `dialogue` panel's `host.portrait_ref` — the complete image bottom-aligned
with contain fit, and a grounded silhouette with the host identity and authoritative
availability state when the entry is a placeholder. When `portrait_ref`
is `null` or names no catalog entry, the host's stage actor SHALL render the truthful placeholder: the
host display name's initial and the display name, never a stock or guessed image. The client SHALL
NOT construct a catalog key from the host identity or any other field. Each foe's stage actor in the foe
line-up SHALL present the committed `art` panel's `portrait_catalog` entry named by that participant's
`portrait_ref` in the committed combat panel, under the same rule: the complete entry image, the
grounded silhouette for a placeholder entry, and the truthful placeholder built from the
participant's display name when the reference is `null` or names no entry.

While the committed mode is `dialogue` and the host's stage actor renders, the stage actors SHALL carry
a speaking state. The speaker SHALL
render at full brightness and the other side SHALL render dimmed to 60% brightness, from one shared
dim token. The host SHALL be the speaker, except while a `explore.talk_scripted` or
`explore.talk_freeform` action the player submitted is in flight — from its dispatch until its result
is handled and its declared presentation revision is accepted, or until it is rejected — during which
the player SHALL be the speaker. The speaking state SHALL be derived from the dispatch state, the
committed mode, and the panel's availability only, never from narrative prose. Outside dialogue mode,
and in dialogue mode while the `dialogue` panel is unavailable, no stage actor SHALL be dimmed, and a
foe's stage actor SHALL never be dimmed.
The dim SHALL NOT be the only indication of who is speaking: the name plate names the host, and the
speaking state SHALL be exposed on each stage actor as a data attribute for tests. The stage actors are
decorative art and SHALL carry no focusable element; this requirement covers static states only, and
any transition between them is owned by the motion layer.

#### Scenario: The host portrait comes from the art catalog
- **WHEN** the committed `dialogue` panel names `portrait_ref` `"41"` and the committed `art` panel's catalog entry `"41"` carries an image URL and a face rectangle
- **THEN** the host's stage actor renders that complete image bottom-aligned with contain fit, and no other image source is requested

#### Scenario: A pending or missing portrait shows the truthful placeholder
- **WHEN** the host's catalog entry is a pending placeholder, and later a host with `portrait_ref` `null` named `葛里安·衛登` opens a conversation
- **THEN** the first stage actor shows a grounded silhouette with the host identity and pending state, and the second shows the initial `葛`, identity `葛里安·衛登` and missing state, and neither renders an image

#### Scenario: The host speaks and the player is dimmed
- **WHEN** a conversation opens and the host's greeting commits
- **THEN** the host's stage actor renders at full brightness with `data-speaking="true"`, and the player's stage actor renders at 60% brightness with `data-speaking="false"`

#### Scenario: The player is lit until the reply commits
- **WHEN** the player activates a pick, and the `explore.talk_scripted` request stays in flight until its reply's revision is accepted
- **THEN** from the dispatch until that revision is accepted the player's stage actor is at full brightness and the host's is dimmed, and once the reply commits the host is lit and the player dimmed again

#### Scenario: A rejected choice returns the light to the host
- **WHEN** the player's `explore.talk_freeform` request is rejected
- **THEN** once the rejection is handled the host's stage actor is lit and the player's is dimmed

#### Scenario: Nothing is dimmed outside dialogue
- **WHEN** the committed mode is exploration, and later combat with two active foes
- **THEN** the player's stage actor renders at full brightness in both, `actor-right` carries no stage
  actor in exploration, and in combat both foes' stage actors render at full brightness
