## Context

`services.guild` is host-gated as a whole, so its `quests` section vanishes away from a clerk. The
`objectives` panel is host-independent but carries only tracked in-progress rows capped at three, with
no detail, no issuer, and no settlement.

Parent design: `docs/superpowers/specs/2026-09-06-quest-issuer-model-design.md` §8.1.

## Goals / Non-Goals

**Goals:**

- The player's own quest book is readable anywhere.
- One row shape covers guild and private commissions alike.
- The book, the tracker, and the counter can never print different prose for the same record.

**Non-Goals:**

- No action descriptors beyond `track`. Abandon and turn-in stay counter capabilities and remain in
  `services.guild`; the drawer merges them by `quest_id`.
- No change to the `objectives` panel.
- No client component (owned by `webclient-quest-drawer-split`).

## Decisions

### D1: A new panel, not an extended `objectives`

`objectives` is specified as the HUD tracker island: "discloses exactly the quest records the holder
tracks", capped at `MAX_TRACKED_QUESTS`. Widening it to the full log would change that capability's
meaning and its row cap, and would make one payload serve two surfaces with different lifecycles and
different bounds. Two panels sharing the same describe seams is the cheaper honest answer.

### D2: Read model only — actions stay where they are

The row carries the `track` descriptor because tracking is host-independent by contract, and nothing
else. Abandon and turn-in genuinely require a clerk, so their descriptors stay in `services.guild`
where the host gating already lives. The drawer joins the two by `quest_id`, which is the single
merge point in the whole feature.

Putting abandon/turn-in descriptors in this panel would mean duplicating the host gating in a second
presenter — two places that could disagree about whether the counter is open.

### D3: All-or-nothing degradation

A partial row list would silently hide a quest the player holds, which is worse than an honest
unavailable panel. This matches the `objectives` panel's stated rule: a corrupt quest log "degrades
the WHOLE panel to the registry-owned common unavailable form — never a partial row list".

### D4: An unresolvable issuance degrades the row, not the panel

Content edits can unregister a generated definition's issuance while a player holds the quest. The
quest is still real and still completable, so hiding it would be wrong. The row renders with a null
reward line.

The row also renders a null `settlement` in that case (review round two): the parent design pins
`npc:` issuances to `auto` as a design intent, but the archived `quest-issuance` contract still
admits either settlement value for a private commission — the shared test fixture itself registers
an npc commission with `counter` — so a namespace-derived fallback could disclose a settlement the
unregistered issuance never carried. Until a later change (the generative issuer work) narrows the
construction contract to npc-implies-auto, an unresolvable row discloses `null` like its missing
reward.

### D5: Row cap truncation and counter-parity boundary

The presenter carries the first `MAX_QUEST_ROWS` records in stored quest-log order (the services
quest-row precedent); the validator still rejects an over-cap producer payload so drift fails
closed. `detail` receives the resolved issuance, which keeps guild rows byte-identical to the
`services` counter rows (same `.reward`) and omits the reward section exactly when the issuance is
unresolvable. The counter parity scenario is stated for a clerk present at the record's issuing
branch: `turn_in_quest` pays the offer at the serving staff's branch, and the quest book shows the
commission terms the record's governing issuance carries — these coincide in every state the game
can currently produce (one branch, registration never transfers), and any future branch-transfer
feature must reconcile the turn-in payment, the counter rows, and this panel together.

### D6: Push coverage beyond the affected-panel tuples

The affected-panel tuples (accept, abandon, turn-in, track, and the trade surfaces) plus the
combat-round `AFFECTED_PANELS` are the targeted publications. Every other quest-log mutation seam —
stage advance on movement and engagement, deadline settlement on `explore.wait`, dialogue and NPC
intent acceptance, inventory actions, and ordinary text-command settlement — publishes through the
existing full-snapshot path, which re-renders every registered panel including `quest_log`. The
same split covers `objectives` after this change, so neither quest surface can lag the other.

The `npc:#<pk>` label resolution performs one bounded database read per row per panel build (at
most twelve on a combat-round republish). This is accepted for correctness first; a request-local
lookup cache is the first optimization if profiling ever shows the cost.

## Risks / Trade-offs

- **`objectives` and `quest_log` overlap** → Accepted and deliberate. Both derive from the same
  describe seams and a parity test pins that they agree byte-for-byte, so the duplication cannot
  drift into disagreement.
- **Issuer label resolution for an `npc:#<pk>` key needs a database lookup** → Bounded to at most
  twelve rows, and a deleted commissioner falls back to the key remainder rather than failing the
  panel.
- **Push on combat puppets too** → Necessary, because a DEFEAT quest can complete mid-fight, and the
  drawer is openable during combat.
