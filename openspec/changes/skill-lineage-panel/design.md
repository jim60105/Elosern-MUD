# Design: skill-lineage-panel

Implements D8 (§12) of
`docs/superpowers/specs/2026-08-30-use-driven-progression-design.md`.

## Context

`use-driven-skill-lineage` landed the prerequisite DAG, tip caps, ladder, and
`can_use_skill`. All render inputs already exist: registry edges + reverse-edge
cache, `db.skill_proficiency`, `can_use_skill`. The WebClient already has the
frozen four-mirror panel contract (protocol validator / panel view / JS
validator / boundary tests) and the stage-icon big-window pattern from the
character/combat panels; Telnet commands mount through `CharacterCmdSet` and
the command-docs trio is a hard invariant.

## Goals / Non-Goals

- Goals: one pure read model; versioned bounded panel; Telnet parity; unlock
  toast.
- Non-Goals: any state mutation (this is read-only by contract), branching
  tree *rendering* polish (the view is already topological-order, so branch
  content upgrades the client without a contract change), mobile layout.

## Decisions

### DD1: three frozen view dataclasses, exactly the design's fields

`LineageNodeView(skill_key, display_name_zh, owned, usable, level,
xp_into_level, xp_to_next_level, capped, prereq_text_zh)`,
`LineageChainView(root_skill_key, element_or_style_zh, nodes, consumed, meter)`,
`LineageView(chains, completed_count, total_count)` — verbatim from §12.
`usable` calls `can_use_skill`; `capped` reads the derived tip cap;
`prereq_text_zh` renders 「需「X Lv.N」」 from registry data, empty for
roots/unlocked nodes. Rationale: one source (registry + proficiency), zero new
storage, mirrors are serialization only. Because a registry label is legal up
to `LABEL_MAX` (128) while the panel text cap is also 128, the wrapper can
overshoot; the read model therefore clamps deterministically — 需「 prefix and
the Lv.N」 suffix survive, the label tail becomes one ellipsis — so a legal
label never forces the whole panel unavailable (rubber-duck R2-1); the clamp
is total — a legal threshold whose digit count alone overshoots the bound
(unmeetable by rule, a totality guarantee only) loses its digit tail instead.
The panel validator keeps its hard bound; the clamp lives in the pure read
model, which both the panel and the Telnet command share.

### DD2: chain = one root's reachable subtree, topological order

A chain is the reverse-edge closure from a root, nodes in topological order.
`consumed` = every node capped; `meter` = shallowest-uncapped progress 0..1.
Linear first-round content renders as today's lists; a branch content drop
needs no contract change.

### DD3: one panel, four mirrors, conventional caps

Panel name `lineage`, schema version 1, availability discriminator per the
existing OOB contract; payload carries the serialized `LineageView` under
`LINEAGE_MAX_CHAINS` / `LINEAGE_MAX_NODES_PER_CHAIN` / bounded text lengths.
The four mirrors ship in lockstep; boundary tests pin every cap. The WebClient
icon opens the big window: expanded tree renders per-node `xp_into_level / 50`
meters and prereq text; collapsed tree renders the chain meter; header shows
`已完成 N / M 樹`.

### DD4: Telnet parity + unlock notification on the post-commit channel

`lineage` prints the same tree (見頂 marker, prereq text). The unlock moment is
detected where `use-driven-skill-lineage`'s accrual seam already runs:
`grant_skill_practice_xp` takes an optional `unlocks_out` list sink and, after a
live award, re-evaluates `can_use_skill` for edges consuming that skill (cached
reverse-edge map), appending one line per newly usable skill.
`ActionResolver` owns the per-resolve sink and folds its lines into
`ActionResult.notifications` only after the commit succeeds (cleared on
`CommitFailed`); the existing settlement boundaries (cast settlement, combat
round, plain command) deliver those lines post-commit exactly as they already
deliver title-grant toasts — there is no separate OOB toast transport in the
repository, and the delta spec's wording follows that real channel. Detection
is derived, never stored — a reload recomputes; no new persistence face.
Auto-seed never calls the grant, so it is intrinsically silent.

## Risks

- Panel size growth with content: bounded by `LINEAGE_MAX_*` truncation order;
  content growth is gradual (tree nodes per element).
- Toast storms on auto-seed cascades (import): toasts fire only on live
  practice grants, never on import/scene-build seeding.

## Migration Plan

One-shot; no compat surface (unreleased).

## Open Questions

None.
