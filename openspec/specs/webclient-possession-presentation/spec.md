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
- **THEN** the rows come from the possessed NPC's own inventory keys, not A's

#### Scenario: Inventory uses the existing item-key surface
- **WHEN** the inventory/equipment panels render while possessing
- **THEN** they render from the possessed NPC's own attributes through the existing `toggle_equipment`/item-key surface

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

### Requirement: The dispatcher refuses possession-incompatible actions with fixed zero-write results
While the session actor is a possessed NPC, dispatches of `shop.buy`, `shop.sell`,
`explore.talk_scripted`, `explore.talk_freeform`, and `explore.engage` SHALL be rejected by the
adapters with outcome `rejected`, stable codes `possessed_shop`, `possessed_talk`, and
`possessed_engage`, and the fixed Traditional Chinese messages, BEFORE any validator-scoped
state read, wallet movement, dialogue session, or combat session change.

#### Scenario: A purchase attempt moves nothing
- **WHEN** a possessing client dispatches `shop.buy` at a fully priced vendor
- **THEN** the result is rejected with `possessed_shop`, the fixed line, and wallet, inventory,
  and shop stock are byte-identical

#### Scenario: The refusal still respects the epoch guard
- **WHEN** a possession-refused result races an epoch bump
- **THEN** the stale refused result is suppressed exactly like any other completion

#### Scenario: Action result contract unchanged
- **WHEN** a possession refusal is returned
- **THEN** the `ui_action_result` contract (request id, epoch guard) is unchanged

#### Scenario: Guild navigation opener refuses too
- **WHEN** a possessing client opens a `guild` navigation opener
- **THEN** it behaves exactly as the shop refusal path (no state) while possessed

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
