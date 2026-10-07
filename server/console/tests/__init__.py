"""S6 acceptance map using proposed captions, not guessed canonical IDs.

Protected deterministic console boundary: ConsoleApiTests, WriterContractTests
and retained StateApi/ReadOnlyContract suites.
Tick-conditioned recoverable intervention: PolicyTests and SnapshotClockTests.
Gameplay-thread serialized console execution: OwnerHandoffTests and PolicyTests.
Complete validated domain verb batch: OwnerIdentityTests and all four owner suites.
Inventory wallet and trait operations: RulesConsoleTests.
Full GM clock settlement: RulesConsoleTests and PolicyTests.
Map lifecycle verbs with consequences: MapConsoleTests.
Quest lifecycle repair and issuance: QuestConsoleTests.
Append-only memory interventions: MemoryConsoleTests.
Transactional universal Evennia raw editing: RawTests and ConsoleApiTests.
Shared console transport results and errors: ConsoleApiTests and GM api.test.js.
Contextual portal controls and confirmation: GM console/npc-tabs/router/shell
Vitest suites, import-boundary tests and the component showcase gate.
Console operational evidence and operator guidance: PolicyTests, ConsoleApiTests
and the reviewed AGENTS/operator/save documentation.
Complete S6 acceptance and repository contracts: these suites plus exact shard
ownership, frozen game-client, lint, traceability and contract gates.

Literal covers_requirement annotations for new captions belong to the owning
archive/sync workflow once tools.spec_traceability list reports canonical IDs.
Existing main-spec annotations remain substantive; pre-sync green does not
claim canonical S6 main-spec coverage.
"""
