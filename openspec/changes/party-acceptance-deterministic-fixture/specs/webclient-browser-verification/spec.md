## ADDED Requirements

### Requirement: Party management acceptance has an explicit deterministic named fixture
The isolated synthetic browser runtime SHALL offer an opt-in pre-session party-management fixture with effective co-located companions 艾拉 and 卡恩, actor-owned usable heal and hostile-opening skills on 艾拉, useful inventory/equipment, healable targets, an open merchant, a finishable hostile encounter and a traversable exit. Existing fixture modes SHALL retain their behavior when this option is absent.

#### Scenario: Named members are real authorized actors
- **WHEN** a fresh managed runtime starts with the dedicated fixture and no incompatible composition flags
- **THEN** 艾拉 and 卡恩 have distinct stable fixture identities, effective membership and co-location with the commander and owner's body, and real item/skill preview consumers authorize 艾拉's own heal, consumable and hostile opening using her owned skills, inventory, prerequisites and resources

#### Scenario: The named journey has executable physical prerequisites
- **WHEN** the fixture's merchant, bags, equipment, target and exit are inspected through real consumers
- **THEN** the party can buy three potions for 艾拉 and transfer some to 卡恩, visibly re-equip 艾拉, heal a wounded target, open and finish the seeded encounter, and traverse the real exit while possessed with the owner's body and 卡恩 able to follow

#### Scenario: Initialization policy is explicit and bounded
- **WHEN** acceptance uses the dedicated fixture
- **THEN** its design explicitly authorizes deterministic fixture initialization before login, all manual post-login state interventions still use existing protected GM domain verbs with snapshot protection, and raw repair or shell state patches remain prohibited

#### Scenario: Dedicated composition does not silently replace existing modes
- **WHEN** the new option is absent or is supplied with incompatible party/service composition flags
- **THEN** existing modes are unchanged in the absent case, and incompatible dedicated combinations reject with a setup diagnostic before fixture mutation rather than substituting a generic or positional companion
