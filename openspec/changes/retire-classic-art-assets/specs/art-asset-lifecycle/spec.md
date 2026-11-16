## REMOVED Requirements

### Requirement: world/art/service.py is the sole writer of asset and queue records
**Reason**: Active lifecycle guarantees move to art-gallery-autogen; the obsolete asset lifecycle capability is retired.

**Migration**: No compatibility reader or data migration. Recreate pre-release development databases. Gallery jobs/cards are the only runtime publication state.

### Requirement: Startup recovery rescans explicit unique portrait policies
**Reason**: Active lifecycle guarantees move to art-gallery-autogen; the obsolete asset lifecycle capability is retired.

**Migration**: No compatibility reader or data migration. Recreate pre-release development databases. Gallery jobs/cards are the only runtime publication state.

### Requirement: Successful player creation and validated import schedule an eligible unique portrait through transaction.on_commit
**Reason**: Active lifecycle guarantees move to art-gallery-autogen; the obsolete asset lifecycle capability is retired.

**Migration**: No compatibility reader or data migration. Recreate pre-release development databases. Gallery jobs/cards are the only runtime publication state.

### Requirement: Every player-activation path finalizes the portrait lifecycle
**Reason**: Active lifecycle guarantees move to art-gallery-autogen; the obsolete asset lifecycle capability is retired.

**Migration**: No compatibility reader or data migration. Recreate pre-release development databases. Gallery jobs/cards are the only runtime publication state.

### Requirement: Validated named-NPC spawn schedules its portrait ensure after the spawn transaction commits
**Reason**: Active lifecycle guarantees move to art-gallery-autogen; the obsolete asset lifecycle capability is retired.

**Migration**: No compatibility reader or data migration. Recreate pre-release development databases. Gallery jobs/cards are the only runtime publication state.

### Requirement: Successful room entry ensures the scene asset for a validated archetype
**Reason**: Active lifecycle guarantees move to art-gallery-autogen; the obsolete asset lifecycle capability is retired.

**Migration**: No compatibility reader or data migration. Recreate pre-release development databases. Gallery jobs/cards are the only runtime publication state.

### Requirement: Queue failure never rolls back gameplay
**Reason**: Active lifecycle guarantees move to art-gallery-autogen; the obsolete asset lifecycle capability is retired.

**Migration**: No compatibility reader or data migration. Recreate pre-release development databases. Gallery jobs/cards are the only runtime publication state.

### Requirement: Portrait-character enqueue validates canonical age attributes immediately before enqueue
**Reason**: Active lifecycle guarantees move to art-gallery-autogen; the obsolete asset lifecycle capability is retired.

**Migration**: No compatibility reader or data migration. Recreate pre-release development databases. Gallery jobs/cards are the only runtime publication state.

### Requirement: The age check runs on every lifecycle path and rejects deterministically without a persisted marker
**Reason**: Active lifecycle guarantees move to art-gallery-autogen; the obsolete asset lifecycle capability is retired.

**Migration**: No compatibility reader or data migration. Recreate pre-release development databases. Gallery jobs/cards are the only runtime publication state.

### Requirement: Rejected prompt content never reaches the presenter or browser
**Reason**: Active lifecycle guarantees move to art-gallery-autogen; the obsolete asset lifecycle capability is retired.

**Migration**: No compatibility reader or data migration. Recreate pre-release development databases. Gallery jobs/cards are the only runtime publication state.

### Requirement: Startup converts classic scene outputs into scene gallery cards
**Reason**: Classic scene conversion is retired.

**Migration**: No compatibility reader or data migration. Recreate pre-release development databases. Gallery jobs/cards are the only runtime publication state.

### Requirement: Startup synchronization requests gallery art for every registered scene and species
**Reason**: Active lifecycle guarantees move to art-gallery-autogen; the obsolete asset lifecycle capability is retired.

**Migration**: No compatibility reader or data migration. Recreate pre-release development databases. Gallery jobs/cards are the only runtime publication state.
