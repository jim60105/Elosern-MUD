# Delta: onboarding-guide

## REMOVED Requirements

### Requirement: New players arrive at the capital's South Gate

**Reason**: The onboarding subsystem is retired wholesale; characters now stay in 虛境 (Limbo) at birth and leave through the one-way city gate. Per-city arrival relocation was the tutorial's first beat and cannot survive race-based starting cities.
**Migration**: retired with the onboarding subsystem; 虛境 threshold + one-way gate flow replaces it.

### Requirement: The arrival scene plays as the first guided beat

**Reason**: The guided arrival scene exists only to start the guard tutorial state machine (`first_arrival_seen`/`onboarding_beat`), which is deleted.
**Migration**: retired with the onboarding subsystem; 虛境 threshold + one-way gate flow replaces it.

### Requirement: The South Gate guard offers scripted guidance

**Reason**: The `onboarding_guard` NPC and its `OnboardingGuide` component die with the subsystem; the guard returns in the future only as an ordinary authored-identity NPC.
**Migration**: retired with the onboarding subsystem; 虛境 threshold + one-way gate flow replaces it.

### Requirement: talk behaves predictably for any NPC

**Reason**: The surviving `talk` syntax/greeting/error behavior is already carried by the `scripted-dialogue` capability; the guide-prompt topic line retired with the guard, so the requirement's remaining content is fully covered elsewhere.
**Migration**: retired with the onboarding subsystem; 虛境 threshold + one-way gate flow replaces it; see `scripted-dialogue` for the surviving talk contract.

### Requirement: Guidance hands off at the guild exterior

**Reason**: The guided-corridor hand-off is pure tutorial state-machine semantics with no surviving behavior once the guide is deleted.
**Migration**: retired with the onboarding subsystem; 虛境 threshold + one-way gate flow replaces it.

### Requirement: Onboarding state is written only by the deterministic service

**Reason**: The persisted attributes `onboarded`, `onboarding_beat`, `guide_progress`, and `first_arrival_seen` are deleted from `typeclasses/characters.py`; there is no state left to write.
**Migration**: retired with the onboarding subsystem; 虛境 threshold + one-way gate flow replaces it.

### Requirement: A help entry explains onboarding afterwards

**Reason**: The 新手引導 help entry describes the retired guided route; the surviving player-help surface is the static HelpOverlay controls reference, already mandated by `webclient-contextual-hud`.
**Migration**: retired with the onboarding subsystem; 虛境 threshold + one-way gate flow replaces it; static controls reference (`webclient-contextual-hud`) replaces the tutorial help.

### Requirement: Deviation detection applies to every room type

**Reason**: Deviation detection is the guide-skipping observer (`observe_room_entry`), removed from the movement settlement with the subsystem.
**Migration**: retired with the onboarding subsystem; 虛境 threshold + one-way gate flow replaces it.
