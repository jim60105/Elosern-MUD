# place-attendant-hosts Specification

## Purpose
Define the talk-only service host whose service is conversation: an authored place declares
its dialogue capability directly, the seam that binds a host to a dialogue table that exists,
and dialogue alone grants no trade, guild, reception or commission authority.

## Requirements

### Requirement: A place whose service is conversation has a blueprint to host it
A complete hosted place SHALL declare narrative dialogue directly without needing an attendant profession. Dialogue alone SHALL grant no trading, guild, reception or commission authority.

#### Scenario: An attendant place yields a talk-only host
- **WHEN** a place declares only scripted dialogue
- **THEN** one canonical host answers its configured dialogue and carries no other service capability

#### Scenario: An attendant row authoring a trade kwarg is rejected
- **WHEN** a dialogue component authors a shop kwarg
- **THEN** the whole candidate rejects the unknown per-type field

#### Scenario: An attendant place declares no goods
- **WHEN** a dialogue-only place declares goods without merchant
- **THEN** the complete candidate rejects it

#### Scenario: An attendant row authors exactly the dialogue kwarg
- **WHEN** ordinary narrative dialogue is authored
- **THEN** dialogue_key is required while service association and binding are not inferred

#### Scenario: Trade kwargs on an attendant row hit the dead-kwarg rule
- **WHEN** a narrative component carries branch_key
- **THEN** per-type validation rejects the unrelated field

### Requirement: An authored host is bound to a dialogue table that exists
Catalog load SHALL reject a place row whose authored `dialogue_key` resolves to no dialogue
table, naming the place and the unresolvable key. Proving the kwarg was authored is not
enough: a key that resolves to nothing produces a host that greets no one and answers
nothing, which is indistinguishable at runtime from an intentionally silent NPC.

#### Scenario: A place naming an unregistered dialogue table fails load
- **WHEN** a synthetic place row authors a `dialogue_key` that the dialogue registry does not
  carry
- **THEN** catalog load raises the named error identifying the place and the key

#### Scenario: Runtime lookup still degrades rather than raising
- **WHEN** a dialogue lookup is made for a key absent from the registry, outside the place
  registry path
- **THEN** the no-understanding line is returned and no exception escapes

#### Scenario: Runtime lookup behaviour is unchanged by the load-time gate
- **WHEN** a `dialogue_key` reaches the registry from any other route
- **THEN** it still degrades to the no-understanding line rather than raising

