## ADDED Requirements

### Requirement: A site's living individuals are the quest layer's binding source and no quest may create or recover a site
The site owner SHALL expose a read that answers, for one authored site key, which of that site's own living
individuals currently stand and what the site's durable lifecycle state is. The read SHALL be pure: it
SHALL create, populate, recover, move, delete, or modify nothing, it SHALL emit no lifecycle decision event
(it decides nothing), and repeating it SHALL leave every surface equal. It SHALL answer for a world that is
not provisioned, for an unknown site key, for a never-populated site, and for a cleared site, without
treating any of those as a recovery opportunity. A quest clear-out SHALL take its bound set from that read
alone: neither acceptance nor the board SHALL populate, recover, or spawn an individual for a quest, and a
site's first population and its recovery SHALL remain the site owner's clock-settled lifecycle decisions.
Binding a quest to a site's individuals SHALL NOT change the site's ownership markers, its durable state,
or the number of individuals it owns.

#### Scenario: The read answers with the site's own living individuals
- **WHEN** a populated site's read is taken
- **THEN** it returns exactly the living individuals carrying that site's ownership marker, and no ambient, quest-owned, other-site-owned, or dead individual

#### Scenario: A cleared site offers no targets and stays cleared
- **WHEN** a cleared site's read is taken
- **THEN** it returns no living individual, and the site's durable state, its cleared-at tick, and every individual it owns are unchanged

#### Scenario: A never-populated site is not populated by the read
- **WHEN** a site the world has not yet populated is read
- **THEN** it returns no living individual and creates none, and the site remains in its unpopulated state until the world clock's settlement populates it

#### Scenario: A quest binding changes no site surface
- **WHEN** a quest binds a site's living individuals as its targets
- **THEN** each individual keeps its site ownership marker, the site's durable state is unchanged, and no individual is created or removed

#### Scenario: Reading twice changes nothing
- **WHEN** the read is taken twice in one process for the same site
- **THEN** both answers are equal and no persistent surface differs between them
