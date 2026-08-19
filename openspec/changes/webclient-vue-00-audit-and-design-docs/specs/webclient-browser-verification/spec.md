## ADDED Requirements

### Requirement: The implementation-bound public contract is frozen before the shell is swapped
Before the WebClient's GoldenLayout/jQuery shell is replaced, the implementation-bound client
contract SHALL be enumerated and frozen: the `window.Elosern.*` public façades, the keyboard /
plugin key-event path, the DOM identifiers the managed browser tests target, and the versioned
layout-persistence keys. The freeze SHALL be a committed, reviewed deliverable that is the binding
input to the browser-bridge change, and every identifier the browser tests currently target SHALL be
either preserved unchanged or re-mapped to a stable `data-testid` hook per that frozen list.

#### Scenario: A frozen contract list exists before wiring
- **WHEN** the Phase-0 contract audit is complete
- **THEN** a committed list names each implementation-bound contract (façade, key path, targeted DOM id, persistence key) classified as preserve-via-bridge or delta, and is declared the input to the browser-bridge change

#### Scenario: Browser-test targets are preserved or re-mapped per the list
- **WHEN** the GoldenLayout/jQuery shell is later replaced by the Vue app
- **THEN** every identifier the managed Playwright suite currently targets is either preserved unchanged or re-mapped to a stable `data-testid`, per the frozen list
