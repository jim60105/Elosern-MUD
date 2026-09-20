## ADDED Requirements

### Requirement: A place whose service is conversation has a blueprint to host it
The profession rulebook SHALL declare an `attendant` profession carrying exactly one
place-bound `scripted_dialogue` component. A place registry row MAY name it, and doing so
SHALL yield one service host that carries the row's authored name, title, race, subrace and
sex, and a dialogue table — and no trade, guild or commission capability. Authoring the row
SHALL require exactly the identity kwargs the component declares (`dialogue_key`); a
`shop_key` or `branch_key` on an attendant row SHALL be rejected as a kwarg no component
consumes, by the same dead-kwarg rule every other profession already obeys.

#### Scenario: An attendant place yields a talk-only host
- **WHEN** a synthetic place row naming the attendant profession is synchronized
- **THEN** one host exists at that place carrying a scripted-dialogue component bound to the
  authored dialogue key, and carrying no merchant, guild-staff, guild-examiner or
  quest-issuer component

#### Scenario: An attendant row authoring a trade kwarg is rejected
- **WHEN** a synthetic place row names the attendant profession and authors a `shop_key`
- **THEN** catalog load raises the named error identifying the place and the kwarg no
  component consumes

#### Scenario: An attendant place declares no goods
- **WHEN** a synthetic place row names the attendant profession and declares assortments
- **THEN** load raises naming the place, because assortments require a shop identity

### Requirement: An authored host is bound to a dialogue table that exists
Catalog load SHALL reject a place row whose authored `dialogue_key` resolves to no dialogue
table, naming the place and the unresolvable key. Proving the kwarg was authored is not
enough: a key that resolves to nothing produces a host that greets no one and answers
nothing, which is indistinguishable at runtime from an intentionally silent NPC. Runtime
lookup behaviour is unchanged — a `dialogue_key` reaching the registry from any other route
still degrades to the no-understanding line rather than raising.

#### Scenario: A place naming an unregistered dialogue table fails load
- **WHEN** a synthetic place row authors a `dialogue_key` that the dialogue registry does not
  carry
- **THEN** catalog load raises the named error identifying the place and the key

#### Scenario: Runtime lookup still degrades rather than raising
- **WHEN** a dialogue lookup is made for a key absent from the registry, outside the place
  registry path
- **THEN** the no-understanding line is returned and no exception escapes

### Requirement: Adding the blueprint changes no shipped host
Introducing the attendant profession SHALL NOT alter any shipped place row, service host,
interior or dialogue answer. The shipped roster SHALL derive exactly the hosts it derived
before, with the same professions, components and authored identity.

#### Scenario: The shipped roster is unchanged by the new blueprint
- **WHEN** the service-host roster is derived after the attendant profession is added
- **THEN** every row's profession, service anchor and authored identity equal what they were
  before, and no row names the attendant profession
