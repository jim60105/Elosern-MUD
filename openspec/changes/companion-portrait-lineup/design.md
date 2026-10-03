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

### D2 — The controlled character is slot index 0 (rightmost, highest baseline z)

Slot 0 is the controlled character; slots 1..N follow party order. AppClient's pure `companionFigures()` mapping exchanges slot 0 and exactly the possessed companion's former slot, without filtering/re-appending or disturbing other companions. It joins the committed `status.actor.identity` to party rows only while the possession banner is available, resolving every portrait via the catalog.

**Live-contract correction:** the old status presenter emitted the owner's identity while possessing, contrary to the proposed join. `status.actor.identity` now always addresses `context.actor.pk`. Its existing bounded-string wire type is mandatory in the UMD status validator, status read model and client fixtures; changing it to an integer would change a separate panel schema. Party identities remain safe integers, so the join compares `String(row.identity)` to the string status identity. Status name/resources/conditions and every other hybrid field remain owner-keyed verbatim. The possession-presentation delta explicitly records this exception.

### D3 — Party v2 portrait_ref: server presenter resolves the NPC's default gallery card

The actual art API is `world.art.subjects.character_subject_for(npc)`; there is no `SubjectKind.npc`. Resolve that canonical named-character policy, call `record_for(subject, create=False)`, and confirm the default card belongs to `cards_for(record)`. Emit `portrait_catalog_key(npc.pk)`, or null for absent/malformed policy, record or default card. Gallery reads never create records or enqueue generation; catalog resolution retains its age gate. The v2 validator accepts null or 1–32 ASCII decimal digits (`[0-9]+`), matching the combat-ref bound. UMD validation is shared by Vue; no second mirror is introduced.

### D4 — Actor-left anchor: overflow visible when companions present

`HudFrame.vue` already sets `overflow: visible` on actor-right in combat. The companion lineup extends leftward beyond the actor-left anchor box, so the same rule applies: the anchor is `overflow: visible` unconditionally (or gated by a data-attribute prop). Simpler: set `overflow: visible` on actor-left unconditionally — a solo portrait fits inside the anchor anyway, so no visual change.

### D5 — Equal-size horizontal party stance; compress overlap, never scale

The user's revised directive supersedes the original depth-shrinking table: **every figure, including the controlled character, is scale 1 with lift 0**, sharing the portrait anchor's full height and ground line. No rear-depth brightness ramp is used. Baseline z is count minus slot index. Horizontal exposed fractions for counts 1–5 are 0, .42, .30, .24, .22. These produce a maximum span of 1.88 anchor widths; the real anchor width is two thirds of `--actor-h`, not the original rough estimate. A multi-figure row translates right only enough to preserve a 16px scaled left gutter, remaining in the stage's left half. Solo remains at its existing anchor without translation.

In dialogue, the equal-size row compresses its horizontal step to the room left of the real choice column (`max(30vw, 50vw - 280px * --ui-scale)`), keeping scaled 16px gutters on both sides. The whole row is aligned to the left gutter. No measurement observer, size change or foe-lineup edit is needed. The pure helper optionally accepts a maximum span for deterministic geometry assertions. Rear fallback initials sit in each exposed shoulder rather than being hidden beneath the next portrait; no invented image or URL is supplied.

### D6 — The party presenter resolves the bound owner while possessing

The NPC has no `db.party` binding. Resolve the owner through existing `bound_owner_of()` (live player plus bidirectional party membership) before `live_companions()` and owner-keyed `relations.stage_for()`. The controlled companion remains in the party rows and can join the corrected status identity. No live owner raises the registry-unavailable error, never an available empty party. The six-key row contract is untouched.

### D7 — Party companions join the exploration portrait catalog; eviction degrades to the placeholder

The exploration art view appends the owner's live, co-located companions in party order after existing dialogue hosts/named-policy entries, deduplicated, including the controlled companion while possessing. Companions without an eligible policy still receive truthful unavailable catalog entries. The 32-entry cap can evict a companion; an unresolved ref falls back to its initial rather than invented art.

### D8 — A speaking companion receives temporary paint-only focus

The user's AVG directive applies the existing `StageActor` speaking dim (`--actor-dim`) to companions: they are listeners unless the committed dialogue host identity equals their party identity and the existing `dialogueSpeaker` signal is `"host"` in dialogue mode. That companion is lit and temporarily gets z 6, above every baseline slot. Speaker changes, dialogue exit, possession swaps and count changes derive fresh baseline z immediately; no remembered focus can leak. Focus changes neither x, scale nor lift. The controlled figure keeps its existing player speaking-dim and beat behavior. No prose inference or combat-speaking state is added; motion off/reduced motion still applies correct z immediately.

**Optical polish:** a party/controlled dialogue host already has a standing figure in the lineup, so suppress only its duplicate actor-right host, by committed identity join. Non-party hosts retain their existing actor-right portrait/motion; name plate, pagination, focus and keyboard paths are untouched. The existing contextual-HUD stage-actor speaking requirement is explicitly MODIFIED in the delta to cover this exception and companion listener dim outside dialogue.

## Risks / Trade-offs

- **[Five equal-size figures crowd dialogue]** Choice clearance can require strong overlap, especially at 1440x900. → Compress horizontal exposure only; temporarily lift the active companion so the speaking face is unobscured. Never reduce a rear figure's size.
- **[Possession swap looks abrupt]** The epoch transition re-paints the entire lineup. → The lineup is keyed by its slot list; Vue's `<Transition>` handles crossfade per slot. At `off` motion level, the swap is instant — acceptable, matching the foe lineup's behavior on combat exit.
- **[No combat gestures on companions]** The gesture props are only forwarded to the controlled character's StageActor; companions get `gesture: null`. → Companions don't act in combat. The controlled character (slot 0) gets gestures via `beatStage`.
- **[Missing or cap-evicted art]** A catalog key need not resolve in every snapshot. → Use the shared truthful initial-letter placeholder, retaining authoritative pending/unavailable entries when present.
