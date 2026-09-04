<!-- Scope note (2026-09-04 split): client surfaces (tracker island, browser toggle,
     showcase) moved to webclient-align-09-objective-tracker-ui; this design covers the
     server contract decisions only; client decisions live in change 09. -->
# Design: webclient-align-06-quest-tracking-contract

## Context

Alignment design §3 Change 6 fixes the tracker's semantics: server-side tracking state —
persistent boolean `tracked` on the quest record (default false, accept never auto-tracks),
written through the deterministic core; WS action `guild.quest_track` payload
`{quest_id, tracked}`; cap 3 (setting true beyond 3 tracked is rejected); only `in_progress`
records are trackable; the tracker shows the first 3 tracked rows with stage box, objective
summary, progress numerals, optional deadline line; head `目標 … N 追蹤`; toggle entry points
on the quest board/log rows; the `objective-*` deferred entry is removed in the same change.
The original sketch derived the tracker client-side from `services.guild.quests` rows — which
fails because that section is present only when a local `GuildStaff` host resolves
(`world/rules/service_view.py::_build_guild`), so the island would disappear the moment the
player leaves the guild hall. The quest record already round-trips
`{quest_id, definition_key, state, stage_index, stage_progress, deadline_tick, accepted_tick,
stage_room_id, objective_target_ids, protected_entity_ids, failure_reason}` through JSON in
`db.quest_log`; `describe_objective`/`describe_deadline` are the canonical prose seams; offers
carry integer copper (`describe_reward`).

## Goals / Non-Goals

**Goals:**
- `tracked` boolean on `QuestRecord` with a bounded lifecycle op (`set_quest_tracked`) that
  validates the whole log before writing, enforces cap 3, and rejects non-`in_progress`
  targets with `QuestTransitionError`.
- `guild.quest_track` service action riding the exact-payload/allowlist/dispatch contract.
- `services` schema v4: quest rows gain `tracked`.
- New `objectives` panel disclosing exactly the `tracked && in_progress` rows in quest-log
  order (cap 3 by construction) with describe-seam prose, reward copper integer, and the
  deadline line — host-independent, so the tracker works everywhere.
- Client protocol mirrors only (UMD + Vue panel allowlists, services v4 validators, the
  command-echo entry): every client SURFACE (tracker island, QuestBoard 追蹤/取消追蹤
  toggle, showcase) is owned by webclient-align-09-objective-tracker-ui.

**Non-Goals:**
- No `選修` tag (no backing field; the draft's `.mode-combat .obj .opt` rule then has nothing to
  hide — documented), no drawer 追蹤中/進行中 sections (the toggle is the honest model), no
  turn-in/abandon controls on the tracker, no tracker reordering UI (log order is the order).

## Decisions

- **Panel over services derivation (design amendment):** the design doc chose services-row
  derivation for payload economy; host-gating makes it wrong. A dedicated `objectives` panel
  reads `read_records(actor)` + definition registry directly, mirroring `service_view`'s
  degrade-independently discipline (corrupt log → shared unavailable form, never partial). The
  design doc §3 Change 6 gets a dated amendment note in this change.
- **Cap ownership:** the cap (3) lives in the quest lifecycle module next to the state it
  protects (registry-style constant), the action adapter surfaces the rejection message; the
  panel does NOT re-clamp (tracking truth already enforces it) but validates the bound.
- **Row disclosure:** `{quest_id, display_name, objective_line, stage_index, stage_total,
  stage_progress, objective_quantity, reward_copper (int | None), deadline_line (str | None)}`
  — prose from `describe_objective`/`describe_deadline`, reward as canonical integer copper
  (never prose-parsed client-side); `reward_copper` null when no live offer exists.
- **Services v4 bump:** `tracked: bool` on quest rows is a wire-shape change →
  `SERVICES_SCHEMA_VERSION = 4`, mirrored validators (server + client mirrors), same three-list
  allowlist discipline for the new `objectives` panel name.
- **Push timing:** every quest write seam (accept/abandon/fulfil/fail/progress via
  acquire/planner/room_observation/transitions) and the new `set_quest_tracked` mark the
  holder's presentation dirty for BOTH `services` and `objectives` (services rows carry the
  toggle state; the island needs the list) — same coordinator rhythm as change 04's party.
- **Toggle UI (delegated):** QuestBoard quest-log rows rendering 追蹤/取消追蹤 that dispatch
  `guild.quest_track {quest_id, tracked}` (no confirmation gate — non-destructive
  presentation of one's own log) is change 09's decision; only the wire contract lives here.

## Risks / Trade-offs

- Stored records predate `tracked`; a missing key reads false via the record loader — that is
  the default, not a migration shim (no released users; the loader default IS the schema).
- Progress transitions re-push both panels per seam; cost is two small payloads per quest
  commit, acceptable for correctness of the toggle + island pair.
- The 3-row cap makes the tracker's `N 追蹤` count equal `rows.length` always (never a log
  count), keeping the header truthful against the payload.
