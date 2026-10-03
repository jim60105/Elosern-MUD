## MODIFIED Requirements

### Requirement: Panels render the honest v1 hybrid under the banner
While possessing, the wallet, quest/objectives, guild-rank, and status panels SHALL keep rendering
A's persisted state (A owns those fields; NPCs own none of them), except that `status.actor.identity`
SHALL address the controlled session actor B as the existing bounded string identity, so it joins
the integer identities in `party.slots` after decimal-string normalization. Status name, resources,
conditions, full title, location, disguise and combat fields SHALL retain their existing owner-keyed
hybrid contract. The inventory/equipment panels SHALL render from the possessed NPC's own attributes
through the existing `toggle_equipment`/item-key surface — the banner requirement is what makes the
A-keyed panels honest rather than laundering A's purse through B's hands. No panel gains
possession-specific fields; every panel keeps its existing schema.

#### Scenario: A's wallet shows while possessing
- **WHEN** a snapshot arrives mid-possession
- **THEN** the wallet panel carries A's copper total and the banner is simultaneously available

#### Scenario: Inventory shows the possessed NPC's pack
- **WHEN** the client requests inventory presentation mid-possession
- **THEN** the rows come from the possessed NPC's own inventory keys, not A's

#### Scenario: The status identity addresses the controlled figure
- **WHEN** the player A possesses companion B
- **THEN** `status.actor.identity` is B's decimal database identity as a string while the status name, resources and conditions remain A's persisted state
