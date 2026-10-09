## REMOVED Requirements

### Requirement: The quest browser exposes the tracking toggle
**Reason**: The quest drawer is redesigned as a two-level tabbed master/detail surface. Tracking now renders in the detail action bar, and only for in-progress rows. Completed rows no longer show a disabled tracking control with a reason.
**Migration**: Covered by `webclient-quest-drawer` → "The detail action bar mirrors server descriptors". Re-point this requirement's test annotations there.

### Requirement: The quest drawer separates the player's quest book from the guild counter
**Reason**: The book and the counter are now first-level tabs of one drawer instead of two stacked sections, so the "both render together" contract no longer holds.
**Migration**: Covered by `webclient-quest-drawer` → "The quest drawer is a two-level icon-tabbed surface", "The guild counter tab presents counter business only", and "The quest drawer degrades honestly". Re-point annotations accordingly.

### Requirement: Counter-only quest actions appear on a book row only when the counter offers them
**Reason**: Counter actions move from book rows to the selected quest's detail action bar. The `quest_id` merge rule is unchanged.
**Migration**: Covered by `webclient-quest-drawer` → "The detail action bar mirrors server descriptors". Re-point annotations there.

### Requirement: The quest book discloses each quest's commissioner and settlement
**Reason**: Commissioner, settlement, and reward disclosure move into the quest detail of the redesigned drawer.
**Migration**: Covered by `webclient-quest-drawer` → "Selecting a quest shows its full detail beside the list". Re-point annotations there.
