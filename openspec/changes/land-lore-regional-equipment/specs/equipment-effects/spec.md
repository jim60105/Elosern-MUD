## ADDED Requirements

### Requirement: A new equipment roster states its own tradeability
Every roster this capability adds SHALL state whether its members are stocked by a shop, and that statement SHALL follow the roster's lore provenance rather than a default. Registration and tradeability SHALL be independent: a fully bound, budget-checked equipment item that no shop offers SHALL be a valid shipped state, and the absence of a shop listing SHALL NOT be treated as an incomplete binding by any test or loader.

#### Scenario: The regional roster ships unstocked and complete
- **WHEN** the twelve regional equipment items are inspected after this change
- **THEN** each has a registry presentation identity, an existing price-table key, and a budget-checked rulebook entry, and none appears in any shop's offered keys

#### Scenario: An unstocked binding is not reported as incomplete
- **WHEN** the equipment-effect rulebook is loaded with the regional roster present and unstocked
- **THEN** the load succeeds with no unbound key and no orphaned entry, and the general store's existing offers are unchanged
