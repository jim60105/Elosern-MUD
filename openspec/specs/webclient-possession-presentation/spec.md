## Purpose
Honest-hybrid v1 presentation for companion possession: the actor re-points through the established epoch transition; a persistent banner names the hybrid; panels keep showing A's character-keyed state and B's own inventory/equipment truthfully; the dispatcher refuses possession-incompatible actions with fixed zero-write rejections.

## Requirements

### Requirement: Possession re-points the session actor through the epoch transition
On a successful `explore.possess` dispatch the server SHALL re-point the session's actor marker
(`session.ndb.elosern_actor_id`) to the possessed NPC and drive the established
retire/epoch-bump/`send_unpuppet_transition` sequence, so every subsequent snapshot, panel push,
and action admission is keyed to the possessed NPC's session identity, and in-flight results for
the previous actor can never land on the new one. Handback re-points back to A through the same
sequence.

#### Scenario: Snapshots after entry are keyed to the possessed NPC
- **WHEN** possession completes on a connected session
- **THEN** the next full snapshot resolves its actor from the possessed NPC and the presentation
  epoch differs from the pre-possession epoch

#### Scenario: Handback re-points home
- **WHEN** `explore.possess_release` completes
- **THEN** the actor marker names A again and one epoch transition separates the two keyings

### Requirement: Every snapshot while possessing carries the possession banner
The presentation layer SHALL expose a possession banner payload (schema-version 1: exactly
`schema_version`, `available`, `host_name`, `since_tick`) that is `available` true with the
possessed NPC's canonical display name and entry tick while the session actor is a possessed NPC,
and the shared unavailable form otherwise; its fixed presentation line is 「你透過{host}的雙眼行動」
with `{host}` substituted. The Vue shell SHALL render it persistently (not a transient toast)
while available.

#### Scenario: The banner names the possessed companion
- **WHEN** a connected client receives a snapshot while possessing a companion
- **THEN** the banner payload is available carrying the companion's display name and the shell
  renders the fixed line persistently

#### Scenario: Release clears the banner
- **WHEN** possession releases
- **THEN** the banner uses the shared unavailable form and the shell removes the line

#### Scenario: Client mirrors validate in lockstep
- **WHEN** the server registry defines the banner payload
- **THEN** the UMD/Vue client mirrors validate the payload in lockstep with the server registry

### Requirement: Panels render the honest v1 hybrid under the banner
While possessing, the wallet, quest/objectives, guild-rank, and status panels SHALL keep rendering
A's persisted state (A owns those fields; NPCs own none of them), except that `status.actor.identity`
SHALL address the controlled session actor B as the existing bounded string identity, so it joins
the integer identities in `party.slots` after decimal-string normalization.

#### Scenario: A's wallet shows while possessing
- **WHEN** a snapshot arrives mid-possession
- **THEN** the wallet panel carries A's copper total and the banner is simultaneously available

#### Scenario: Inventory shows the possessed NPC's pack
- **WHEN** the client requests inventory presentation mid-possession
- **THEN** the party window's bag rows come from the session's viewed member's own inventory keys (A by default), exactly as without possession, and the wallet shown is A's purse

#### Scenario: Inventory uses the existing item-key surface
- **WHEN** the inventory/equipment panels render while possessing
- **THEN** `party_inventory` renders the viewed member's own attributes through the existing `toggle_equipment`/item-key surface, identical to the non-possessed payload

#### Scenario: The status identity addresses the controlled figure
- **WHEN** the player A possesses companion B
- **THEN** `status.actor.identity` is B's decimal database identity as a string while the status name, resources and conditions remain A's persisted state

#### Scenario: Status fields keep the hybrid contract
- **WHEN** panels render mid-possession
- **THEN** status name, resources, conditions, full title, location, disguise and combat fields retain their existing owner-keyed hybrid contract

#### Scenario: The banner keeps A-keyed panels honest
- **WHEN** A-keyed panels render while possessing
- **THEN** the banner requirement is what makes them honest rather than laundering A's purse through B's hands

#### Scenario: Panel schemas unchanged
- **WHEN** possession presentation is delivered
- **THEN** no panel gains possession-specific fields and every panel keeps its existing schema

### Requirement: The possession controls complete the action round-trip
`explore.possess` SHALL resolve through the deterministic entry gates of
`world/rules/possession.py`, surfacing each gate reason as outcome `rejected` with the gate's
stable code and fixed line, and `explore.possess_release` SHALL call the rules release; success
results SHALL be followed by the full presentation update that carries the re-pointed actor and
banner.

#### Scenario: A gated possess attempt round-trips the gate
- **WHEN** a client dispatches `explore.possess` for a companion failing the co-location gate
- **THEN** the result is rejected with the gate's code and line and no state changes

#### Scenario: Success pushes the new keying
- **WHEN** a possess dispatch succeeds
- **THEN** the client receives the action result followed by a snapshot carrying the banner and
  the possessed actor's panels

#### Scenario: Possession controls never suggested
- **WHEN** suggestion candidates are computed
- **THEN** `explore.possess`/`explore.possess_release` never appear (their absence from `SUGGESTIBLE_ACTION_IDS` is the mechanism; no new filter)

### Requirement: The dispatcher preserves talk and engage refusals during possession
While the session actor is a possessed NPC, dispatches of `explore.talk_scripted`, `explore.talk_freeform`, and `explore.engage` SHALL be rejected by the adapters with outcome `rejected`, the corresponding stable `possessed_talk` or `possessed_engage` code and fixed Traditional Chinese message, before any service-scoped state read or dialogue/combat mutation. `shop.buy` and `shop.sell` SHALL instead follow normal party-scoped trade rules.

#### Scenario: Talk and engage attempts move nothing
- **WHEN** a possessing client dispatches scripted talk, freeform talk, or combat engage against a normally eligible local target
- **THEN** the result is rejected with the corresponding `possessed_talk` or `possessed_engage` code and fixed line, and dialogue sessions, combat sessions, affinity and all other canonical state remain unchanged

#### Scenario: The refusal still respects the epoch guard
- **WHEN** a possession-refused result races an epoch bump
- **THEN** the stale refused result is suppressed exactly like any other completion

#### Scenario: Action result contract unchanged
- **WHEN** a possession refusal is returned
- **THEN** the `ui_action_result` contract (request id, epoch guard) is unchanged

#### Scenario: Guild navigation and service content are absent
- **WHEN** a possessing client renders a room containing a guild host
- **THEN** no guild navigation opener or guild service section is rendered, no guild action is dispatched, and no synthetic possession-refusal message is displayed for the omitted surface

### Requirement: Shop access does not delegate other NPC services during possession
While possessing a companion, guild register/board/quests/turnin/merit, guild exam, church join/pray/offer/redeem/merit, talk and freeform talk, combat engage, and quest-issuer commissions SHALL retain their existing unavailable or refused behavior. Guild and church commands SHALL remain absent from the possessed cmdset. Their actions SHALL NOT gain commander delegation or new possession-specific handling.

#### Scenario: Guild and church stay outside the possessed command surface
- **WHEN** the active command set is built for a possessed companion
- **THEN** guild and church commands remain absent, including the guild examination command, while shop commands remain available

#### Scenario: Hidden services cannot act as the commander
- **WHEN** a possessing client attempts an existing guild or church action, or a quest-issuer commission interaction
- **THEN** existing admission or domain authorization prevents the service and changes no registration, guild/church merit, wallet, offering, quest, reward, or exam state; the companion is never substituted with the commander to enable it

#### Scenario: Conversation opening stays refused
- **WHEN** a possessing client attempts `explore.talk_open` against a normally eligible host
- **THEN** the existing `possessed_talk` refusal remains, no dialogue opens, and no quest-issuer commission is made available through it
