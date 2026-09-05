# Design: webclient-align-08-dialogue-surface

## Context

Changes 07/10 committed the session lifecycle plus mode `dialogue` and the `dialogue` panel. The draft's dialogue mode keeps the
whole cockpit visible (REDESIGN §2 matrix: 敘事=對話聚焦, 小地圖 ●, 同伴快帶 ●, 目標追蹤 ●,
指令列 ●, 行動甲板=對話選項) and puts the conversation in the centre: `.dlg` box (64px avatar,
`.who` gold speaker line, serif `.say`) with `.choices`/`.pick` numbered rows (mono `.k` badge,
`⌨` free-dialogue row) embedded in the feed, plus a dock `對話選項` tab mirroring the same picks
with hint `數字鍵 1–4 選 · → 指令列自由對話`. The existing machinery: the borrowed command-line
freeform path (探索 dock → 互動 → 自由對話 already borrows the input), the frame-resolution
per-mode root teardown (`exploration.root`/`combat.root`/`creation.root` — a fourth mode needs
`dialogue.root`), the keyboard router (change 02 owns letters; digits 1–4 are free in dialogue
mode), the art catalog portrait seam (`portrait_ref: null` today → initial fallback, same
contract as the character head card and party rows).

## Goals / Non-Goals

**Goals:**
- Feed dialogue variant inside `NarrativeFeed.vue`: while mode is `dialogue` AND the committed
  panel is available — head label `對話`, `完整日誌` capsule NOT rendered (draft-exact), `.dlg`
  box + `.choices` picks from `dialogue.choices`; freeform row focuses the borrowed command line.
- Dock dialogue form: `dialogue.root` descriptor resolves the single `對話選項` tab/pane
  mirroring the SAME committed picks (one source), pane rows dispatch
  `explore.talk_scripted {npc_id: host.identity, keyword_id}` under the existing contract; hint
  row per change 01's treatment; digits 1–4 bind the first four picks.
- Matrix: dialogue column visible across narrative/islands/minimap/party/tracker/dock/command
  line; teardown gains `dialogue.root` from the single decision point.
- Stale panel (mode dialogue, panel unavailable — the race between clear seams and the commit is
  transient): the feed falls back to plain narrative presentation and the dock resolves
  `dialogue.root` to its degraded reason row (existing unresolvable marker path) — no invented
  surface.

**Non-Goals:**
- No new components/manifest entries (feed variant inside `NarrativeFeed`, dock pane rides the
  existing pane renderers); no client dialogue transcript (history stays in the narrative
  stream); no `.why` reason tags or `.pick.disabled` states (no backing field — the table pool
  ships enabled); no AI-synthesized choices.

## Decisions

- **Draft deviation (backdrop 頭像聚焦):** the REDESIGN matrix's dialogue backdrop treatment is
  achieved by the `.dlg` avatar itself; the scene backdrop keeps its committed art truthfully —
  no client-side backdrop mutation on mode. Documented in the matrix requirement.
- **Two presentations, one source:** feed picks and dock pane rows both derive from
  `dialogue.choices` through ONE shared view-model helper (story-bound derived shape); the dock
  pane does not re-fetch or duplicate state, and both dispatch through the same router entry.
- **Digit binding scope:** digits 1–4 bind picks only while mode is `dialogue` and picks render;
  elsewhere digits keep their current command-line semantics (never intercepted from input).
- **Bond stage line:** `who` renders `display_name` plus ` · 羈絆 <stage>` only when
  `bond_stage` is non-null; stage name verbatim from the panel (numbers never reach the client).
- **Chained deltas:** this change's MODIFIED blocks restate requirements as modified by
  changes 03/05/06 — it lands in wave W3 after those, and the chain note heads the delta file.

## Risks / Trade-offs

- The dialogue feed variant competes with the unread/live-region contract: the `.dlg` box renders
  the SAME committed line the stream already carries — the variant SUPPRESSES the duplicate
  stream tail line for the session's exchange (panel line wins presentation), keeping the live
  region announcing each new line exactly once. Verified by a focused test.
- Transient mode/panel races (clear seam vs commit ordering) are covered by the stale-panel
  fallback above; no mode flap is possible because both surfaces branch on the same committed
  pair.
