# Proposal

## Why

Inns currently offer the same recovery as any safe place. Give players a reason to pay for lodging and provide real private rooms without authoring a separate floor plan for each inn.

## What Changes

- Add whole-party check-in and one reusable private room per inn, generated from a shared template. Charge 20 copper per player or present companion at check-in. Sleep remains a separate choice.
- Reject voluntary sleep in other people's homes and shops in cities. Allow warned street naps that patrols can interrupt. Keep safe camping outside cities free.
- Double recovery rates during paid sleep. A fully recovered guest earns a nonstacking reduction in mental reserve consumption for the next two hours of foot travel.
- Leave involuntary sleep, resurrection, theft, and private events themselves outside this change.

## Capabilities

### New Capabilities

- `inn-lodging`: Paid check-in, private guest room access, and paid-sleep settlement.
- `city-sleep-policy`: Urban voluntary sleep permissions, interruption, and re-entry rules.
- `well-rested-travel`: A per-body walking allowance with consistent prediction and settlement.

### Modified Capabilities

- `altoria-hospitality`: Permit lodging at the existing inn and apply the common city sleep policy to the other hospitality interiors.
- `mental-reserve`: Define paid sleep and well-rested foot travel as explicit rate exceptions.

## Impact

Map room provisioning, NPC services, wallet, sleep and clock settlement, travel planning and settlement, text commands, web service actions, and player command documentation. Builds on the approved [inn lodging design](../../../docs/superpowers/specs/2026-11-20-inn-lodging-design.md). No data migration or external service dependency.
