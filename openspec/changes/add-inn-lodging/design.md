# Design

## Context

The capital inn has one authored interior and a dialogue-only host. Sleep entry uses durable per-body receipts in `world/rules/time_skip.py` and `sleep_receipt.py`; clock settlement handles the committed prefix of an advance. Fatigue prediction and travel settlement currently use fixed activity rates. The approved product design is linked from the proposal.

## Goals / Non-Goals

**Goals:** Reuse the authored lobby, custody of location state, the existing sleep transport and recovery machinery, and the game clock. Identify and isolate the inputs that alter rates and boundary predictions.

**Non-Goals:** Map sub-floor authoring, temporary quest-scene reclamation, NPC patrol simulation, private event authoring, or separate client-side game rules.

## Decisions

### Check in and create the room in one transaction

Add a lodging capability to the existing place-bound host. Build the quote from the canonical present-party roster and validate its identity, price, host, and room again on confirmation. Reject changed quotes and any ineligible member before moving anyone. Snapshot affected wallet, locations, booking, and related attributes for rollback, including Evennia caches. Install one booking for the whole roster and publish only after commit.

Derive the room's persistent identity from the lodging place key in `world/maps/`. Provision one template room with both directions represented in the exit graph. The room stays outside `InstanceRoom` reclamation so later stories can refer to a stable place. Persist booking identity and participants independently of the room. Authorize entry through the booking at the server movement boundary, including party followers; never lock the way out. Reject overlapping check-ins to the same room. An occupant's departure releases that guest's entitlement and access; release the booking when its last guest leaves. Sleep completion alone preserves access. Locate the room from the booking on reload without refreshing it or moving anyone.

### Apply location policy at voluntary sleep entry

Resolve the city and street or interior classification from authoritative map identity. Classify city streets as napping locations, booked guest rooms as paid sleep locations, and other city locations as unavailable for voluntary sleep. Do not derive rules from display names or apply a city rule to unrelated villages. Use one policy in single and party entry, preview, camp, and existing sleep handoff surfaces. City camp cannot create a wilderness sleep session. Keep the location check outside `evaluate_skip_safety` because that path also gates awake rest and waiting. Forced sleep keeps its current threshold and progression.

Declare recurring patrol coverage and timing in deterministic authored or rulebook data and validate coverage for city streets. Expose only the general warning at street nap entry. Wire the next applicable patrol into interruptible clock settlement, including progress caused by another body. On reaching it, settle through the boundary, end matching active voluntary street receipts, wake those bodies, and record the remaining-day refusal for the canonical party owner and street identity. A patrol on the receipt's exact wake deadline takes precedence. Do not process already-completed or forced sleep receipts, advance beyond the boundary for that request, charge money, or offer continuation of an expelled receipt.

### Settle paid sleep and grant walking allowance at natural wake

Bind paid sleep to booking, guest, and room at accepted positive-duration entry. Persist whether a guest has consumed the stay's paid sleep; a pause retains the same receipt. Resolve the same per-body paid rate in the sleep target calculation, gauge settlement, and fatigue planner. Apply it only to positive recovery during actual eligible sleep; preserve zero or negative rates, caps, and ordinary awakening rules. Speculative projections and unrelated sleepers gain nothing.

At committed completion, test the final four gauges and positive elapsed duration before awarding the allowance. Save the award with the completed receipt's transaction and deduplicate by sleep identity. Leave existing allowance unchanged for a nonqualifying stay. Use the fatigue writer for the allowance and reserve settlement, with the active walking rate established from the shared rulebook. Carry remaining walking seconds in the detached travel snapshot and split both prediction and settlement at allowance exhaustion as well as existing fatigue thresholds. Apply the same rule to travel capacity and movement preflight. Consume no allowance for a rejected, unperformed, or nonwalking interval.

## Risks / Trade-offs

- Check-in crosses wallet and map ownership. Fault injection after debit and after movement must prove durable and cached rollback, including first room provisioning.
- Sleeping companions can remain in a suite while control moves elsewhere. Neither receipt revalidation nor lifecycle checks may infer room occupancy from the commander alone.
- Clock advances already split at physiological, interaction, and contact boundaries. Patrols must compete with those boundaries without duplicate recovery. Use authority and location identities when replaying a receipt.
- Route planning is detached from writes. Missing allowance state in any preflight or preview would produce inconsistent route feasibility even if final reserve settled correctly.
