# Webclient Redesign Alignment — Design

Date: 2026-09-04
Status: Approved for spec review
Design source of truth: `docs/design/elosern-redesign/index.html` (v2 static draft) + `REDESIGN.md`

## 1. Context and goal

The Vue webclient implements the v2 redesign cockpit but diverges from the draft in
twelve verified places. This design aligns the implementation to the draft — the
acceptance bar is DOM/CSS equivalence with `index.html` at 1600x900, per surface, per
mode — without inventing new visual language or new data.

Verified divergences (screenshot + DOM audit against the running container):

1. Condition island renders an empty `無條件` placeholder; the draft hides the island entirely.
2. AI suggestion cards render twice (feed `ChoicePointBlock` + dock suggestions section).
3. Quick-word chips dropped the draft's key badges, keybindings, and Tab-completion hint.
4. No bottom-right objective tracker (deferred read model).
5. No companion quickbar (left HUD `.comps`) and no 同伴 · 隊伍 drawer.
6. Narrative feed chrome lacks the draft's `.feed-inner` hairline, mode label head,
   `完整日誌 ↑` capsule, `.sys`/`.cmt` semantic line styles, and the dialogue JRPG box.
7. `.dock-tab-bar__hint` text/structure differs from draft `.dock .hint` (no `<kbd>`).
8. Dock band shows pure-black side gutters: the gradient lives on the max-width-centered
   content container (measured x=210, w=1180 of 1600) instead of the full-width wrapper.
9. Command-line util buttons (lineage/codex/settings/help) have no draft position.
10. There is no dialogue mode: protocol `MODES = ("creation", "exploration", "combat")`;
    the draft's JRPG dialogue box has no server-backed state.
11. Quest rows carry no `tracked` flag; the draft's objectives tracker has no read model.
12. Top meta pill / minimap readout: already corrected by the owner — out of scope.

Owner decisions locked during brainstorming:

- Quickbar: real keybindings + real Tab completion (not cosmetic badges).
- Dialogue: one-shot — server-owned dialogue session, not client text-mining.
- Command-line util buttons: keep in place, restyle to draft `.hist button`.
- Objectives: server-side `tracked` flag + cap, disclosed through a host-independent
  `objectives` panel (2026-09-04 amendment §7 supersedes the original "extend `services`,
  no second read model" note — the derivation cannot work guild-host-gated).
- Party rows must reuse existing NPC wire vocabulary (`identity`, `display_name`,
  `portrait_ref`, flat `hp_current`/`hp_maximum` from the combat participant row).
- Each OpenSpec change must fit one workday for one engineer (`tmp/propose.md` scale rule).
- No backward-compatibility or migration work: pre-release, zero users.

## 2. Cross-cutting principles

1. **Contextual hiding is `display:none`** (REDESIGN §0.1). Empty islands (conditions,
   tracker, suggestions) are not rendered at all — never a placeholder, never dimmed.
2. **Single source of truth.** New HUD surfaces (tracker, companion quickbar, dialogue
   box) consume server panels only. The client never mines narrative text or derives
   persistent state locally.
3. **Client stays read-only.** New persistent state (quest `tracked`, dialogue session)
   is written by the deterministic core and pushed through the coordinator; the client
   submits registered WS actions only.
4. **Accessibility floor is unchanged**: icon+symbol+value (never color alone), focus
   rings, `prefers-reduced-motion`, live regions; new components carry draft-matching
   `aria-label`/`role`.
5. **Preserved render pipeline.** The `NarrativeMarkup` tokenize→vnode pipeline,
   `.inp` echo lines + `.narrative-divider`, `.map-art` box-drawing monospace path,
   unread counting + jump-to-latest, and scroll pinning are existing verified
   contracts. The feed redo changes shell chrome and semantic line classes only —
   zero pipeline changes.
6. **Token reuse**: existing `styles/tokens.css` variables back every restyle
   (`--panel`, `--ink-*`, `--paper-*`, `--seal-*`, `--gold-*`, `--vit-*`, `--dock-h`).

## 3. Change decomposition

Ten changes, each ≤ one workday. Names follow the `webclient-align-NN-*` series.

### Change 1 — `webclient-align-01-dock-chrome` (client only, ~0.5d)

- Move the dock gradient, `border-top`, and shadow from the centered content container
  to the full-width stage anchor, matching `.dockwrap` (full-bleed) + `.dock`
  (max-width centered). Fixes the black side gutters.
- `.dock-tab-bar__hint` becomes the draft `.hint` structure: `數字鍵 1–4 · <kbd>Enter</kbd>
  執行 · <kbd>Esc</kbd> 返回`; dialogue-mode variant `數字鍵 1–4 選 · <kbd>→</kbd>
  指令列自由對話`. `<kbd>` gets mono styling (`--ink-780` ground, 2px bottom border).
  The `/ 聚焦指令列` broadcast is dropped (binding stays).
- To keep the legend truthful, the digits it names become real here: `1`–`4` pick the first
  four rows of the current dock frame (move focus + activate via the same confirm path as
  Enter; unclaimed when the frame is shorter or the stack is empty; the quantity form keeps
  precedence). Implemented in the store's focus entry through the frozen router façade —
  the UMD router source is not edited (design D1); the digits join the bridge's claimed-key
  set. The draft's own `1–4` badges on suggestion cards reflect this same intent.
- Command-line util buttons keep position; restyle to draft `.hist button`
  (transparent ground, 26×26, hover `--ink-700`). Function unchanged.

### Change 2 — `webclient-align-02-quickbar-shortcuts` (client + server aliases, ~1d)

- Badges are command-initial letters, and every badge letter is a real command word on
  the server. Owner rule: the badge equals the command's initial; prefer an existing
  Evennia single-letter alias, otherwise create the alias so the shortcut text is a
  literal, playable command on every transport (telnet included).
  - Explore: `看 l` (alias `l` already exists on 看/look), `拿 g` (get), `說 s` (說/say),
    `交談 t` (talk), `等待 w` (wait). Combat: `說 s`, `施法 c` (cast).
  - Server work in this change: add the single-letter aliases `g`→拿(get), `s`→說(say),
    `t`→talk, `w`→wait, `c`→cast where absent (verified current state: only `l` exists).
    Alias additions are a player-command surface change → update
    `docs/game/commands.md` + `docs/game/command-reference.md` and keep
    `tests/test_command_docs.py` green in the same change.
  - Client: a bound letter, from any non-input focus, focuses the command line and
    inserts the badge letter + space (the inserted text IS the command word); never
    submits. Letters avoid existing client bindings (`/`, Esc, arrows, 1–4 card picks,
    Tab). The verb set stays the five commands that actually exist — no fictional 走/問.
    This supersedes the `QuickWordChips.vue` no-badge decision.
- Tab completion inside the field: candidates = input history + quickbar verbs + committed
  exploration panel exit names/interact target names (zero protocol change). Single
  candidate → complete (caret at end); many → complete to longest common prefix,
  subsequent Tab cycles; Shift+Tab reverse-cycles.
- Hint becomes the truth: `↑↓ 歷史 · Tab 補全`.

### Change 3 — `webclient-align-03-narrative-feed` (client only, ~1d)

- Feed shell: `.feed-inner` gains the left hairline (`::before` gradient rule) and a head
  row = mode label (`敘述` / `戰鬥日誌`, derived from committed mode) + `完整日誌 ↑`
  capsule (`--ink-780` ground, radius 99, gold hover border). `UnreadIndicator` moves
  beside the head label.
- Semantic line classes at the renderer mount point: server `sys`-class lines render
  `.sys` (sans, seal `◈ ` prefix); emphasis renders gold `--gold-400`.
- Condition island renders nothing when `conditions.length === 0`.
- De-dupe suggestions: remove `ChoicePointBlock` from the feed end; the only suggestion
  surface is the dock 建議 tab pane (existing router/legacy suppression in
  `ActionDock` stays). Migrate the choicepoint-behavior test anchors; simplify the
  feed-end block-swap pinning watcher accordingly.

### Change 4 — `webclient-align-04-party-panel` (server only, ~1d)

New `party` panel presenter (registry, schema v1, unavailable form
`("party_unavailable", "隊伍資訊目前無法顯示")`). Row vocabulary is the existing NPC
wire shape (exploration target row + combat participant row):

```
{ available: true, slots: [
  { identity,        # int pk — same field name as exploration/combat rows
    display_name,    # npc_display_name(), bounded by MAX_DISPLAY_NAME_CODE_POINTS
    portrait_ref,    # participant contract: opaque decimal catalog key or null (null this version)
    hp_current,      # flat integers, participant field names
    hp_maximum,
    bond_stage } ] } # canonical zh-TW affinity stage name; raw affinity value never ships
```

- Sources: `world/rules/party.py::live_companions()` (stale dbids filter out), affinity
  seven-stage name from the rulebook stage rules (never the raw value). Cap 4.
- Empty party is still an available panel (`slots: []`) so the client renders the dashed
  invite slot rather than an unavailable branch.
- No `token` field: the combat participant row already carries `identity` + `token`;
  the combat HUD joins panels by `identity`. The numbering owner stays `combat_view`
  alone (no duplicated source).
- Dirty-flag hook for party membership changes follows the existing watcher/coordinator
  push rhythm.
- Tests: presenter shape (empty/full/stale dbid), validator rejections; register the new
  test module in `.github/evennia-shards.json`; `@covers_requirement` markers.

### Change 5 — `webclient-align-05-party-hud` (client only, ~1d; depends on 4)

- Left HUD `.comps` island from the party panel: avatar letter + name + HP hairline +
  state line (combat variant `aN 180/220 親睦` joined from combat participants by
  `identity`; explore variant `180/220 親睦`). Pad to dashed `+ 邀請` slots. Island
  click opens the drawer. Renders in explore and combat; the `slots: []` case still
  renders (per draft).
- 同伴 · 隊伍 drawer on the existing `HudDrawer` shell: intro paragraph, `compbig` rows
  (avatar / name + class / 羈絆 stage / HP bar + value / 請其離隊 button), and the
  fixed three-line follow-rules card, all verbatim from draft `dr-party`.

### Change 6 — `webclient-align-06-quest-tracking-contract` (server only, ~1d)

- Runtime: persistent boolean `tracked` on the quest record (default false; accepting a
  quest never auto-tracks), written through the quest lifecycle API. New WS action
  `guild.quest_track` — payload `{quest_id, tracked}`; setting true beyond 3 tracked is
  `rejected` (server cap); only `in_progress` quests are trackable.
- Services panel v3 → v4: `guild.quests` rows gain `tracked: bool` (validator mirrored).
- New `objectives` presentation panel (schema v1): `rows` of the holder's
  `tracked && in_progress` records in quest-log order (cap 3), each `{quest_id,
  display_name, objective_line, stage_index, stage_total, stage_progress,
  objective_quantity, reward_copper, deadline_line}` with prose from the existing
  `describe_objective`/`describe_deadline` seams. Host-independent — the original sketch
  derived the tracker from guild-host-gated `services` rows, which would blank the
  tracker outside the guild hall (§7 amendment). Empty tracked set → `rows: []`;
  corrupt log → shared unavailable form.
- Client surfaces (tracker island, browser toggle, showcase) are change 9.

### Change 7 — `webclient-align-07-dialogue-session-state` (server only, ~1d)

- Session state lives on the character (`db.dialogue_session` — `{npc_id, line,
  updated_tick}`); the writers are the deterministic core only: the
  `talk_scripted`/`talk_freeform` adapter success paths and the `talk` command path
  record the result line; the clear seams are a successful `settle_movement`,
  `explore.engage`, and NPC leave-room/despawn/leave-party cleanup naming the session
  NPC. A session whose host dbid no longer resolves to a present, interactable NPC is
  not live and its stale dbid never reaches any presentation. This change ships no
  client-visible surface; the panel + mode are change 10 (§7 amendment).
- Offline guarantee: with `LLM_ENABLED=false`, scripted dialogue (`run_scripted_talk`)
  fully drives open, refresh, and clear (REDESIGN principle 7).
- Tests: session lifecycle (open via either path / move-clears / engage-clears /
  departure-clears / stale-dbid not-live), shards, traceability.

### Change 8 — `webclient-align-08-dialogue-surface` (client only, ~1d; depends on 3 and 10)

- Feed dialogue variant: `.dlg` box (64px avatar, `portrait_ref`-missing fallback to the
  initial mono letter; `who` row = name + ` · 羈絆 stage`; serif line) + numbered `.choices`
  picks (`1..n` badges submit `explore.talk_scripted{npc_id, keyword_id}`; trailing
  `⌨ 自由對話 → 指令列` row uses the existing borrowed-send path). Head label `對話`
  only — no `完整日誌` capsule in dialogue mode (draft-exact).
- Dock 對話選項 tab mirrors the same choices list; the dock legend swaps to the draft's
  dialogue hint (`數字鍵 1–4 選 · <kbd>→</kbd> 指令列自由對話`) through the
  shortcut-legend requirement restated MODIFIED in change 8's own delta (change 1 owns
  the legend contract; the original "hint text per Change 1" note understated that 8
  must chain the restatement — §7 amendment).
- Mode gating per the REDESIGN §2 visibility matrix (minimap ●, tracker ●, command line
  ●, narrative = dialogue focus). Digit keys 1–4 bind the choice picks and `→` focuses
  the borrowed command line while the dialogue form presents (orthogonal to Change 2
  letter bindings; never intercepted from the input field).

### Change 9 — `webclient-align-09-objective-tracker-ui` (client only, ~1d; depends on 6)

- Bottom-right `.obj` tracker island from the committed `objectives` panel: head
  `目標 … N 追蹤`; per row a stage box (done check at `stage_progress >=
  objective_quantity`), `objective_line`, a mono-gold slot (`n/m` when the objective
  counts, else `+reward_copper`), optional muted `deadline_line`. No rows / panel
  unavailable / creation mode → island not rendered.
- Toggle entry points: 追蹤/取消追蹤 buttons on the service quest browser rows,
  dispatching `guild.quest_track {quest_id, tracked}`; the enabled matrix derives from
  the committed row's `tracked` field.
- Showcase lockstep: `ObjectiveTracker` joins the manifest with a deterministic offline
  story; the `objective-*` deferred entry is removed from
  `tests/overlays/deferred_surfaces_absent.test.js` in the same change.
- Documented deviation: the draft's `選修` optional tag has no backing field, so the
  draft's combat `.mode-combat .obj .opt` hiding rule has nothing to hide.

### Change 10 — `webclient-align-10-dialogue-panel` (server only, ~1d; depends on 7)

- Protocol: `MODES` gains `"dialogue"`. New `dialogue` panel (schema v1, unavailable form
  `("dialogue_unavailable", "對話目前無法顯示")`):

```
{ available: true,
  host: { identity, display_name, portrait_ref },  # same host triple as party rows
  bond_stage | null,                               # stage name when the host is a bonded NPC
  line,                                            # latest server-authored line (zh-TW prose)
  choices: [ { keyword_id, label } ] }              # server-authorized keyword pool (talk_scripted vocabulary)
```

- Mode resolution order in the coordinator: creation > combat > dialogue-session-live >
  exploration. The `exploration` and `character` panels keep shipping their ordinary
  payloads while dialogue is live; every open/refresh/clear commits mode + panel
  atomically with the underlying state change.
- Client protocol mirrors: `dialogue` joins the UMD + Vue panel and mode allowlists in
  lockstep with the server registry (three-list agreement test + oob snapshot mirror).
- Tests: presenter/validator (host triple, bonded/unbonded, corrupt session →
  unavailable), mode-resolution matrix, live→clear snapshot transition; Node-gate
  mirror fixtures.

## 4. Dependencies and batching

Hard dependencies: 4 → 5 (quickbar consumes the party panel); 6 → 9 (tracker UI consumes
the committed objectives panel and the track action); 7 → 10 (the panel and mode present
the session state); 3 + 10 → 8 (dialogue box mounts the rebuilt feed shell and the
dialogue panel).

File conflicts (why some same-wave changes must not run concurrently):

- `CommandLine.vue`: change 1 (util styling) ∩ change 2 (Tab/hint) → 2 follows 1.
- `NarrativeFeed.vue`: change 3 ∩ change 8 → serialized by wave.
- `registry.py` / `protocol.py`: change 4 ∩ change 10 both register panels / extend
  `MODES`.
- `AppClient.vue` / `stores/elosern.js`: near-universal touchpoints; keep cross-batch
  serialization, within-batch same-owner integration for shared files.

Proposed batches (parallel within a wave, serial across waves; ~9 workdays). Change 10
consumes change 7's helper API and chains its delta, so 7 and 10 never share a wave:

- W1: 1, 3, 4
- W2: 2, 5, 6
- W3: 7, 9
- W4: 10
- W5: 8

## 5. Verification

- Client: real-browser screenshot parity vs the draft at 1600×900 for explore, dialogue,
  combat (logged-in character, same viewport both sides); focused Vitest for new behavior
  (Tab completion, key bindings, empty-island rendering).
- Server: smallest focused Evennia test labels (`--keepdb`), `tools.spec_traceability
  check`, shard manifest updated in the same change; observability lint where logging
  paths change.
- Player-command surface change is limited to change 2's single-letter aliases
  (`docs/game/commands.md` + `docs/game/command-reference.md` updated in the same
  change); `guild.quest_track` is a WS action, not a text command.

## 6. Non-goals

- Top meta pill and minimap coordinate readout (already corrected by the owner).
- Adding fictional `go`/`ask` commands to match the draft's 走/問 chips.
- A full 58-command completion catalog panel.
- Layout/format changes to drawers other than the party drawer content.
- Any backward compatibility, schema migration, or legacy payload handling.

## 7. Amendments

### 2026-09-04 — Change-set restructure after rubber-duck review

Two changes were split so each ships one independently testable contract, and the
suggestion-surface dedupe (change 3) gained explicit showcase/manifest/browser-test
follow-through.

- **Change 6 split.** `webclient-align-06-quest-tracker` becomes
  `webclient-align-06-quest-tracking-contract` (server only: `tracked` record field,
  `guild.quest_track`, `objectives` panel, services v4) plus
  `webclient-align-09-objective-tracker-ui` (client only: `.obj` tracker island,
  quest-browser tracking toggle, showcase registration, deferred-surface test trim).
  All Change 6 server decisions stand, including the host-independent `objectives`
  panel replacing the guild-host-gated services-row derivation.
- **Change 7a split.** `webclient-align-07-dialogue-session` becomes
  `webclient-align-07-dialogue-session-state` (deterministic-core session helpers,
  writer/clear seams — invisible on its own) plus `webclient-align-10-dialogue-panel`
  (`dialogue` mode, panel registry/validator, coordinator resolution order, client
  protocol mirrors). Change 08's dependency is now change 10, not 07.
- **Change 3 scope closed.** Deleting the stream choice-point also deletes its
  showcase story/manifest entry, its browser test file and browser-shard entry, and
  retargets the evidence-harness annotations; a showcase delta removes the
  choice-point from the manifest minimum and the action-dock family contract.
- **Change 8 legend ownership corrected.** Its dock dialogue hint had been attributed to a
  nonexistent "command-line hint contract"; it is change 1's shortcut-legend requirement,
  which change 8 now restates as MODIFIED with the reference's dialogue variant
  (`數字鍵 1–4 選 · → 指令列自由對話`, draft line 911) and the matching `→` key binding.
- **Traceability timing pinned repo-wide:** `covers_requirement` annotations for new
  requirement IDs land at each change's archive/sync commit (the checker resolves IDs
  only from `openspec/specs/`; magic-xp P1 precedent).

Revised batches (parallel within a wave, serial across waves; ~9 workdays). The
7 → 10 helper-API dependency and delta chain keep 7 and 10 in separate waves:

- W1: 1, 3, 4
- W2: 2, 5, 6
- W3: 7, 9
- W4: 10
- W5: 8

### 2026-09-06 — Change 8 dialogue surface superseded by align-11

`webclient-align-11-dialogue-ux` supersedes Change 8's dock mirror design: the
`對話選項` dock tab, the `dialogue.root` frame, the dialogue legend swap, and
the `→` dock borrow are deleted. The narrative caption is the ONE dialogue
surface — digits 1–4 retarget to its scripted picks, it carries its own
`結束對話` exit row (the new `explore.dialogue_leave` seam), and the dock
keeps its ordinary exploration form while talking. The panel choice cap
becomes a panel-owned literal (4), independent of the affordance keyword
pool's 16 bound. The frozen `index.html` reference draft is NOT edited; this
addendum records the decision against the normative design record.
