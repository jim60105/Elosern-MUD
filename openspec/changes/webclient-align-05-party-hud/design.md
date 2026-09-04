# Design: webclient-align-05-party-hud

## Context

Change 04 committed the `party` panel: ordered `slots` of `{identity, display_name,
portrait_ref, hp_current, hp_maximum, bond_stage}`. Combat participants carry `{identity,
token}` — quickbar tokens come from a store-side join by `identity`, never a party field. The
draft's quickbar is the `.comps` island (header `同伴 N / 4`, `.comp` cells with `.av` initial
fallback, `.nm`, `.cbar` HP hairline, `.st` row `[aN] hp/max bond`, `.comp.empty` dashed
`+ 邀請`), and the drawer `dr-party` is `compbig` rows + 空位 invite row + fixed 跟隨規則 card.
Both are banned today by the showcase deferred-surface contract, whose test pins
`companion-`/`party-` testid prefixes at the source level; the manifest/story/spec lockstep
rule governs the new components. The existing drawer shell (`HudDrawer`) plus the existing
`explore.party_invite` / `explore.party_leave` actions and their confirm contracts already
exist.

## Goals / Non-Goals

**Goals:**
- Quickbar and drawer render from `party.slots` + the combat-panel join only — no invented
  fields, no affinity numerals.
- `portrait_ref: null` falls back to the draft's initial-letter avatar (display face, gold) —
  the same missing-portrait contract the character head card uses.
- Mutations ride the existing dispatch/confirm contract (請其離隊 → `explore.party_leave`).
- Deferred bookkeeping updated in lockstep: deferral entries removed, manifest + stories added.

**Non-Goals:**
- No invite-rule numerals on the wire (change 04's contract stands); no status-detail panel
  work (詳情 links to the existing status drawer); no map/quest interplay.

## Decisions

- **Draft deviation (invite rule line):** the draft's empty-slot copy shows `（invite 70）`.
  The raw threshold is not on the wire and the panel contract forbids affinity numerals, so the
  shipped copy states the rule in stage-name words: `邀請需當地自由 NPC，且羈絆達「親睦」階段`.
  The stage name is draft vocabulary for the invite threshold (the rulebook's invite gate is
  the 親睦 stage); the number is dropped. 跟隨規則 keeps its three fixed lines verbatim —
  static client copy like the existing control reference.
- **Empty-slot enabled state:** `邀請當前 NPC…` dispatches `explore.party_invite` with the
  committed exploration panel's current interact target when the frame context names one
  (existing action payload contract); otherwise it renders disabled with the rule line as its
  reason — never a fake target.
- **Token join:** `PartyStrip`/drawer read `store.combatParticipants` (committed combat panel)
  and match `identity`; no fighting companion shows no token (draft's non-combat `.st` row).
- **Mode gating:** island visible in exploration + combat, hidden in creation (shared
  visibility matrix); hidden entirely when the `party` panel is unavailable (no placeholder),
  matching the contextual-hiding rule.
- **Lockstep:** new components `PartyStrip`, `PartyDrawer` get manifest titles + Storybook
  stories with deterministic offline party payloads before live wiring; the deferred-surface
  test drops the party entry and its `/\bParty\b/`+`/\bCompanions?\b/` title patterns
  (intimate/event-log/etc. entries stay).

## Risks / Trade-offs

- Dropping title patterns from the deferred test weakens one guardrail — compensated by the
  manifest gate (a party story without a manifest title still fails).
- The drawer's 詳情 button navigating to the status drawer is draft behaviour; deep-linking to
  a companion's full status does not exist (status drawer is player-only) — 詳情 opens the
  player's status drawer only when present in the draft for the player card; companion rows
  ship 請其離隊 only until a companion-status read model exists. (Draft's 詳情 → status button
  is dropped with this note.)
