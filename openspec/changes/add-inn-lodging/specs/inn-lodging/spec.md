# Spec Delta

## Purpose

Provide atomic whole-party check-in, durable private room access, and paid sleep with faster recovery.

## ADDED Requirements

### Requirement: Check-in books the whole present party
The innkeeper SHALL quote the player and every present companion at an initial price of 20 copper per person, without bed assignment or partial booking. Confirmation SHALL revalidate the quote and atomically charge the total, authorize the roster, and move it into one guest room without entering sleep or advancing the clock. Rejection, cancellation, or failure SHALL leave all state unchanged. Text and web SHALL use the same rules.

#### Scenario: Whole-party quote and confirmation
- **WHEN** the player, two present companions, and one remote companion belong to the party and the player confirms a valid quote
- **THEN** 60 copper is deducted and the player and the two present companions enter the same room awake; the remote companion is neither moved nor charged

#### Scenario: Stale, insufficient, or failed confirmation
- **WHEN** the roster changes, the wallet cannot pay the quoted amount, or a room or move write fails during confirmation
- **THEN** the request commits no charge, booking, room provisioning, location change, or elapsed time

### Requirement: An inn provides one reusable private guest room
Each inn SHALL generate a real guest room from a shared template on first successful check-in and reuse its stable identity on later stays. Only guests authorized by the active booking may enter. The room SHALL be separate from the lobby and have a way back to it. Waking SHALL leave guests in the room. A guest leaving forfeits its access and unused paid sleep; the booking closes when the last guest leaves. Reload SHALL preserve room identity, occupancy, and authorization.

#### Scenario: Privacy and reuse
- **WHEN** a stay is active, an unauthorized lobby occupant attempts to enter, and the booked guests later depart and check in again
- **THEN** the occupant cannot enter and is never present in the room, and the new stay uses the same room identity

### Requirement: Booked guests can sleep once at accelerated recovery
An eligible guest in its booked room SHALL be able to start one positive-duration paid sleep after check-in using existing safety checks and bounds. HP, MP, SP, and mental reserve SHALL recover during paid sleep at twice their ordinary positive rates, within existing caps. Predictions SHALL use the same rates. Ordinary sleep and camp SHALL NOT bypass booking.

#### Scenario: Faster recovery with no recovery at check-in
- **WHEN** a depleted guest checks in, enters recovery sleep, and reaches its planned wake without interference
- **THEN** check-in alone grants no recovery, the predicted wake reflects the four doubled recovery rates, and the completed sleep settles all four to full

### Requirement: Interruption does not duplicate paid sleep
A resumable interaction SHALL retain the same paid sleep across reload without a new charge. An early wake or departure SHALL forfeit that guest's remaining paid sleep without a refund and SHALL NOT cancel another guest's sleep.

#### Scenario: Pause and reload
- **WHEN** a paid sleep is paused by a resumable interaction, reloaded and resumed
- **THEN** neither payment nor elapsed recovery is repeated

#### Scenario: Early wake
- **WHEN** one guest wakes early while another guest sleeps
- **THEN** the early riser forfeits the paid sleep without a refund and the other guest's receipt remains active
