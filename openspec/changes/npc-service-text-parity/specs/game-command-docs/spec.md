# Spec Delta

## ADDED Requirements

### Requirement: Text service discovery and explicit provider targeting match contextual services
Text NPC inspection and services discovery SHALL expose the same service identities, availability reasons and empty/error distinction as the browser. Provider commands SHALL document and validate explicit targets without substitution, retaining existing implicit ambiguity behavior when no target is supplied.

#### Scenario: Discover with inspection and command
- **WHEN** a text player uses 看 <NPC> or services <npc> (alias 服務)
- **THEN** the selected visible NPC's canonical service labels/keys/reasons and route guidance are printed without mutation

#### Scenario: Targeted suffix
- **WHEN** a provider command ends with @#<positive dbid>
- **THEN** only that current visible provider is considered; stale/wrong capability rejects with no fallback

#### Scenario: No explicit provider
- **WHEN** an existing implicit command sees multiple local providers
- **THEN** its established ambiguity error remains

#### Scenario: References agree
- **WHEN** provider command syntax or alias changes
- **THEN** both command docs and tests/test_command_docs.py manifest change in the same implementation slice
