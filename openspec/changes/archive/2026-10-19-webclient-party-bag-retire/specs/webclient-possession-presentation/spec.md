# Spec Delta

## MODIFIED Requirements

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
