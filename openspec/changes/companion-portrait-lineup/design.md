# companion-portrait-lineup — Design

## Context

The foe line-up (`FoeLineup.vue` / `foe-lineup.js`) already renders a depth-staged row that grows leftward from `actor-right`, with scale/exposed/lift tables for 1-3 figures. The companion lineup mirrors this pattern on the left side. `StageActor.vue` renders one standing portrait with crossfade, speaking-dim, and combat gestures — it can be reused directly for each companion figure. The party panel's `portrait_ref` seam is currently forced-null (schema v1); this change lifts it to v2.

## Goals / Non-Goals

**Goals:**
- Remove PartyStrip from the vitals anchor and the stage
- Render companions as depth-staged standing portraits in actor-left
- Resolve companion portrait images from the art panel's portrait_catalog, with initial-letter fallback
- Support possession swap: controlled character always rightmost
- Keep the party drawer reachable through the character-status drawer

**Non-Goals:**
- Adding interactive controls on the standing portraits (they stay decorative art)
- Showing companion HP or bond stage on the portraits (the drawer handles that)
- Changing the foe line-up on actor-right
- Adding combat beat gestures to companion portraits (only the controlled character gets beats)

## Decisions

### D1 — Mirror the foe-lineup geometry: `companion-lineup.js` + `CompanionLineup.vue`

A pure JS helper (`companion-lineup.js`) computes per-slot geometry: scale, x-offset, lift, z-index for up to 5 figures (1 controlled + 4 companions), exactly like `foe-lineup.js::foeSlots()`. The Vue component (`CompanionLineup.vue`) renders the computed slots as StageActor instances, each absolutely positioned within the actor-left anchor.

**Alternative:** Inline the geometry in the Vue component. Rejected — the pure-function testability of `foe-lineup.js` is proven; copy the pattern.

### D2 — The controlled character is always slot index 0 (rightmost, largest, highest z)

In the geometry helper, slot 0 = controlled character; slots 1..N = companions in party order. During possession, slot 0 becomes the possessed NPC; the player character A moves to the companion's slot position. The AppClient builds the slot list: `[controlledPortrait, ...companions.filter(c => c.identity !== controlledIdentity)]`. When not possessing, controlledPortrait = the roster's current portrait. When possessing, controlledPortrait = the possessed NPC's portrait (resolved from `party.slots[].portrait_ref` by identity join), and A's portrait becomes a companion slot. This logic lives in AppClient's computed properties.

### D3 — Party v2 portrait_ref: server presenter resolves the NPC's default gallery card

The party presenter calls `record_for(ArtSubject(kind=SubjectKind.npc, key=str(npc.id)), create=False)`, reads `record.db.default_image_id`, and emits the same catalog ref key the art panel's `portrait_catalog_for()` uses. The ref is opaque to the client; resolution through `portrait_catalog` is unchanged. The validator at v2 accepts `portrait_ref` as either null or a bounded string (same bound as the exploration vocabulary uses for portrait_ref on the dialogue host). The UMD and Vue mirrors update to v2 in lockstep.

### D4 — Actor-left anchor: overflow visible when companions present

`HudFrame.vue` already sets `overflow: visible` on actor-right in combat. The companion lineup extends leftward beyond the actor-left anchor box, so the same rule applies: the anchor is `overflow: visible` unconditionally (or gated by a data-attribute prop). Simpler: set `overflow: visible` on actor-left unconditionally — a solo portrait fits inside the anchor anyway, so no visual change.

### D5 — Lineup scales: overlap compresses as group count grows

Rough table (mirroring FOE_SCALES but for the left side):
```
count 1: [1.0]                              (solo)
count 2: [0.95, 0.82]                       (player + 1 companion)
count 3: [0.90, 0.78, 0.68]                 (player + 2 companions)
count 4: [0.85, 0.74, 0.64, 0.56]           (player + 3 companions)
count 5: [0.80, 0.70, 0.62, 0.55, 0.48]     (player + 4 companions)
```
Exposed fraction: 0.42 (slightly less than FOE_EXPOSED=0.46, since the group has up to 5 members). Lift: 0.03 per step behind.

### D6 — The party presenter resolves the bound owner while possessing

`present_party()` currently keys off the session actor: `live_companions(actor)` reads `player.db.party`. While possessing, `status.actor.identity` is the possessed NPC's identity and the NPC has no `db.party` binding, so the naive panel would present an empty party at exactly the moment the lineup needs `party.slots` for the front figure. The presenter resolves the OWNER first: when the actor is a character with a `party_member` back-reference to a live player, that player is the party root, and companion bond stages (`relations.stage_for`) stay owner-keyed as they are today. The possessed companion therefore remains listed among the slots and the client can join `status.actor.identity` to `party.slots[].identity`. A possessed NPC with no live `party_member` owner (never happens through gameplay, so it is a tamper/edge path) takes the shared unavailable form — an available empty list would lie about the party. This is presenter plumbing, not a schema change: the six-key row contract is untouched.

### D7 — Party companions join the exploration portrait catalog; eviction degrades to the placeholder

`portrait_ref` only paints when the same committed snapshot's `art.portrait_catalog` carries the key. The exploration catalog today emits dialogue hosts and explicit named-policy characters from `location.contents`; companions with neither fall out, and the party slot would resolve to nothing while its ref is non-null. The exploration catalog's membership therefore also includes the player's live companions (the art-panel delta). The 32-entry catalog cap can still evict a companion behind dialogue hosts; that is the dialogue-host precedent — the client's initial-letter placeholder covers any ref that does not resolve, and no snapshot ever shows a half-resolved portrait.

## Risks / Trade-offs

- **[Five figures crowd the left half]** At 1280x720 the left half is ~640px; 5 figures with 42% exposure is tight. → The scales table keeps the farthest figure at 48% anchor height; the total span is about 2.2 anchor-widths, which at 720 is ~280px — fits within 640px.
- **[Possession swap looks abrupt]** The epoch transition re-paints the entire lineup. → The lineup is keyed by its slot list; Vue's `<Transition>` handles crossfade per slot. At `off` motion level, the swap is instant — acceptable, matching the foe lineup's behavior on combat exit.
- **[No combat gestures on companions]** The gesture props are only forwarded to the controlled character's StageActor; companions get `gesture: null`. → Companions don't act in combat. The controlled character (slot 0) gets gestures via `beatStage`.
- **[Party portrait_ref latency]** The art panel's portrait_catalog may not contain the companion's ref on the very first snapshot. → The catalog is populated in the same push as the party panel; the catalog includes every ref any panel emits.
