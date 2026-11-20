# Inn Lodging and Settlement Sleep

**Status:** Approved design

## Player contract

Cities offer reliable overnight sleep through paid lodging. Ordinary shops and homes belonging to others refuse voluntary sleep without advancing time. Awake rest and waiting retain their existing rules. No free urban overnight shelter is added. Outside the city, safe camping retains ordinary free recovery. This change adds no theft, resurrection point, or restriction on involuntary sleep.

City streets allow voluntary naps. The player sees a general warning about patrols, without the patrol time. The server settles patrols on the game clock, without a random roll or real-time wait. A patrol that reaches a sleeping party ends the street sleep for its members, credits the elapsed recovery, and asks the party to leave. The same street location refuses another voluntary nap by that party for the remainder of that in-game day. The interruption offers no sleep continuation. A street nap can finish before the patrol reaches it.

## Paid lodging

The innkeeper offers one whole-party check-in. The quote lists the player and every present companion, with a total of 20 copper per person. Guests cannot select a subset. Remote companions are neither charged nor moved. No bed assignments or room numbers are needed.

At confirmation, the rules revalidate the offer, quoted roster, funds, and ability of the full roster to enter. One atomic check-in deducts the total, establishes lodging authorization, and moves the whole roster to the same private guest room. If any present guest cannot enter, the check-in refuses as a whole. Cancellation or refusal leaves funds, locations, sleep state, and clock unchanged. Check-in does not start sleep.

Each inn generates one real, persistent guest room from a shared template on its first successful check-in. Later stays reuse its stable identity. It connects to that inn's existing lobby without authored floors or corridors. The active booking gates access; lobby occupants are not present in the guest room. Guests stay in the room on waking. The room can host future private scenes using the actual location and occupants; this design adds no such events.

Voluntary sleep at the inn requires a valid booking and presence in its guest room. Guests can choose when to sleep and select recovery sleep or an explicit duration under the existing limits. The sleep entry still checks safety. The paid rate belongs to the accepted sleep receipt and requires the same booking and room. No existing sleep receipt is replaced by check-in.

Each check-in covers one paid sleep per guest. During that sleep, positive HP, MP, SP, and mental reserve recovery rates are twice their ordinary rates. Existing caps and eligibility still apply. Prediction and settlement use the same rules. A resumable interaction preserves the receipt and its remaining target; continuing in place incurs no additional charge. Waking early forfeits that guest's remaining paid sleep without a refund or new lodging bonus. Leaving ends that guest's access and forfeits any unused sleep. Neither action cancels another guest's sleep. The booking closes when its last guest leaves. Existing safety and dream-consent rules still apply.

## Well rested

A guest receives the bonus after completing a positive-duration lodging sleep and waking with full HP, MP, SP, and mental reserve. The bonus applies to that body. It reduces mental reserve consumption on foot by 25% for the next two accumulated hours of foot travel. Waiting, combat, conversation, and other nonwalking time neither consume the allowance nor receive its benefit. A later qualifying stay replaces the remaining allowance without stacking.

Travel prediction and settlement both split an interval at the exact allowance boundary. This includes any downstream change to depletion predictions or fatigue-dependent speed. Interrupted travel consumes only the allowance corresponding to actual walking.

## Ownership and scope

Authored location identities distinguish lodging, city streets, and interiors that disallow voluntary sleep. Use the existing lodging place declaration for the Hearthstone Inn; do not infer policy from display names or artwork. Resolve voluntary sleep permission through the deterministic sleep entry path shared by text and web, including explicit party sleep and camp. Keep combat and hostile checks in the existing safety gate. The innkeeper's service uses deterministic wallet and sleep settlement. The map owns location facts, the clock owns elapsed boundaries, and the client displays server quotes and outcomes without calculating rules. Core behavior works offline.

The implementation change modifies the inn-specific no-mechanism requirement in `altoria-hospitality`. Its other hospitality locations retain their current behavior except where the general city sleep restriction applies. No per-inn guest-room map, patrol simulation AI, inventory theft, or municipal shelter is required.

## Acceptance

- Text and web agree on location refusal, party scope, quote, and outcome. Solo, party, and camp entry cannot bypass a refusal. Involuntary sleep remains recoverable.
- A street sleep crossing a patrol boundary settles only its elapsed prefix, wakes the affected sleepers, and refuses a second nap at that location until the next game day. No time is charged for a refusal.
- Check-in charges for every present guest and moves them to one private room. Remote companions remain unchanged. Insufficient funds or a failure after the debit leaves funds and locations unchanged. Repeated stays reuse the room, and unauthorized lobby occupants cannot enter.
- A paid stay restores all four resources faster when each is depleted. Failed sleep entry leaves sleep state unchanged. A paused and reloaded stay continues without a second debit. Early wake, departure, and partial recovery grant no new bonus; replay cannot award it twice.
- Prediction and settlement agree when the walking allowance expires mid-route. Interruptions and reload preserve the unused allowance; ordinary time does not consume it.
