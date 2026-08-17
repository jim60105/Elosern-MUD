# Design: Raise the Combat-Panel Skill-Count Bound (MAX_SKILLS)

## Context

`MAX_SKILLS = 32` in `world/rules/combat_view.py` bounds the flattened skill-descriptor count of
the combat panel. The bound predates the sexual act catalog: the A2 change (skill-category-combat-
panel) preserved it deliberately ("the actual total-skill-count bound the OOB protocol limit depends
on") and re-asserted it in three places — the build-time bound in `combat_view._build_skills`
(raising `CombatViewError` → `PanelUnavailableError` for the web panel), the server-side payload
validator in `web/webclient/presentation/combat_panel.py`, and the client-side mirror in
`web/static/webclient/js/elosern/protocol.js`. The catalog added 65 active `SEXUAL_ACT` skills on
top of the 91 base active skills (including the two innate), for a theoretical maximum of **157
owned active skills** (the extra one over 91 + 65 being the pre-existing `divine_sexual_arts`
active skill) — any character who unlocks a meaningful share of the catalog alongside
normal spell acquisition exceeds 32 and loses the combat action panel entirely.

## Goals / Non-Goals

**Goals:**
- Raise `MAX_SKILLS` from 32 to **192**, clearing the 157-skill theoretical maximum with headroom
  while staying a multiple of 16 (the presentation-bounds family is `MAX_PARTICIPANTS = 16`,
  `MAX_SKILLS = 32`).
- Update all four enforcement points and both boundary tests with the new value.
- Keep the flattened-total semantics exactly as shipped (A2 design D-5).
- Prove — not assume — that the enlarged panel still satisfies the OOB protocol's envelope limits.

**Non-Goals:**
- No payload-shape changes; no presenter logic changes; no per-category bounds.
- No other presentation bounds are touched (`MAX_PARTICIPANTS`, `MAX_DEPTH`, code-point bounds).

## Decisions

### D-1: One constant, four mirrors — change the value, not the mechanism

`world/rules/combat_view.py` stays the single source of the value. `combat_panel.py` imports it
(unchanged code path), and `protocol.js` carries the hardcoded mirror plus its JS test. The web
v3 payload at 192 descriptors is still a small JSON envelope; `MAX_DEPTH = 12` (A2) already covers
the nesting. The build-time bound keeps rejecting genuinely impossible payloads (a defense-in-depth
guard), just at the new number.

### D-2: The raised bound is gated on the OOB protocol's real limits, measured, not assumed

Two global webclient protocol constants apply to every validated server payload (the client's
`checkEnvelope` rejects any canonical JSON over `MAX_CANONICAL_JSON_BYTES = 65_536` bytes, and
`MAX_LIST_ITEMS = 128` bounds every array):

- **List-item bound**: satisfied structurally. The largest array in the v3 combat envelope is a
  category sub-group's `skills` list — at most 18 descriptors today (關係線), well under 128; the
  `groups` arrays and the top-level category array are bounded by `len(SkillCategory)`; participants
  are bounded by `MAX_PARTICIPANTS = 16`.
- **Byte bound**: measured, not assumed. The actual text payload of all 157 obtainable active
  skills' descriptor fields (key, label, description, cost, spec/group/category strings) totals
  ≈ 20 KB in the current registry (≈130 bytes per descriptor); with per-descriptor JSON scaffolding
  and the envelope overhead, the catalog-complete payload is estimated at ≈ 50–62 KB — inside
  65,536 but with a real margin, so this change ships a **byte-fit gate test** as part of its task
  list: serialize the `context_actions` payload for an entity owning every currently obtainable
  active skill and assert it is at or below `MAX_CANONICAL_JSON_BYTES`. The decision rule is
  deterministic: if the measured payload exceeds the limit, `MAX_SKILLS` SHALL be lowered to the
  largest multiple of 16 that fits and the test re-run; 192 stands only if the gate passes.
  **Measured at implementation time: the catalog-complete payload serializes to 47,805 bytes
  (73% of the 65,536 ceiling), and every array fits under `MAX_LIST_ITEMS` — the gate passes and
  `MAX_SKILLS = 192` stands.**

**Rejected — paging/chunking the skill list.** The webclient panel renders the full list and has no
pagination seam; a byte-aware pagination scheme would be a protocol change (new schema version)
well beyond this capacity fix. The measured-fit gate plus the documented headroom rule is the
smallest change that cannot silently regress the OOB contract.

### D-3: 192, not 256

256 would be the next power of two and offers more headroom, but 192 already clears the maximum by
~25% (and the catalog's remaining deferred acts — 忍耐×3, 交合×2 already landed by a sibling
proposal, 搾取×1 — add at most six more), and the byte budget makes a larger count increasingly
pointless: 256 descriptors at the measured ~325 bytes each would approach 80 KB and breach the
envelope limit on the client. If a future catalog outgrows 192, the same one-line raise applies
together with a byte-budget re-measurement.

## Risks / Trade-offs

- **[Risk] A stale mirror.** The value exists in four files (plus two tests). → Mitigation: the
  tasks update all of them in one change; the JS test and the Python panel test both pin the
  boundary (193 rejects / 192 passes), so a drift fails tests loudly.
- **[Risk] The byte gate is an estimate until the harness runs.** The design's ≈ 50–62 KB estimate
  is derived from real registry text but the full serialized envelope (participants, reasons,
  freeform scales) is measured at implementation time. → Mitigation: the byte-fit gate test is a
  mandatory task; the design's decision rule dictates the outcome either way.
- **[Risk] Larger panel payloads.** Even at the measured fit, a catalog-complete payload is near
  the envelope's middle third; each new act adds ≈ 300–400 bytes. → Mitigation: the design's
  documented re-measurement rule for future catalog growth.
- **[Trade-off] The bound remains a hard cap.** A future catalog growth beyond ~198 active skills
  would need another raise; documented as a one-line change plus byte re-measurement.

## Migration Plan

No migration: no released users. The constant change is deploy-time only; existing sessions
rebuild the panel on the next request.

## Open Questions

None.
