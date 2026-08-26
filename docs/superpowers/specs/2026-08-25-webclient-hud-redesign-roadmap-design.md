# WebClient Contextual HUD Redesign — Roadmap

**Date:** 2026-08-25
**Status:** Approved
**Scope:** Completing the *unachieved half* of the Vue SPA migration — replacing the WebClient's static
three-column dashboard with the contextual cinematic HUD of the validated design draft
(`docs/design/elosern-redesign/`), on the Vue 3 SPA and the existing Evennia transport.

This is a **roadmap / intent document**, not an implementation spec. It is the authoritative record of
the *why*, the *delivery order*, and the *cross-change mechanics* that keep the six sub-changes coherent.
The fine-grained requirements for each slice live in that slice's OpenSpec change.

---

## 1. Why this roadmap exists: the migration achieved its spec, not its intent

`docs/superpowers/specs/2026-08-19-webclient-vue-migration-roadmap-design.md` §1 opens with the
motivation for the whole twelve-change migration:

> A complete, validated single-screen design (the 設計稿, the Elosern design draft) now exists, and
> **building to it** as yet another pile of jQuery DOM code would not scale.

The migration landed A1–D1 and every gate is green. The client is a Vue 3 SPA on Vite + Pinia, the
protocol contracts are intact, and the offline text fallback works. But the shipped UI is **not the
設計稿**. It is `2026-08-02-webclient-ui-design.md` §5.1 — the *older* five-surface, three-column
dashboard the 設計稿 was drawn to replace — rendered in Vue instead of jQuery.

The intent was lost in four documented, traceable steps. None of them was a mistake in execution;
each was a correct application of a contract that quietly excluded the layout:

1. **The roadmap's Goals never restated §1's intent.** §1 says "building to it"; §2 Goals reduce the
   design draft to a single deliverable — *"Land the 設計稿 as a committed, linked design reference in
   `docs/`."* Landing a document is not building to it. No goal, no roadmap row, and no "Delivers"
   cell ever assigns the 設計稿's layout, information architecture, or contextual visibility model to
   any change.

2. **The precedence chain ranked the superseded document above the roadmap.** Migration roadmap §3
   places `2026-08-02-webclient-ui-design.md` at precedence **2** and the roadmap itself at **3**, with
   "on conflict, the higher document wins." §5.1 of that document specifies the three-column layout in
   normative prose. The roadmap authorised exactly **one** amendment to it — the D13
   *implementation* swap (GoldenLayout → Vue 3 SPA). The *layout* was never in scope to change, so
   §5.1 stayed binding for all twelve changes.

3. **B1 scoped the 設計稿 down to a colour palette.** `webclient-vue-02-showcase-core`'s proposal binds
   the required component set to "the roadmap's 'Delivers' column (roadmap §5) and
   `2026-08-02-webclient-ui-design.md` §7", and describes the 設計稿's contribution as
   *"the design system carried over from the 設計稿 (ink-night palette + single seal-red accent,
   self-hosted fonts, status never color-only, reduced-motion honored)."*
   `docs/development/frontend-vue-architecture.md` **D6** codifies the same reduction:
   *"Design system extracted from the 設計稿 — the tokens live in `styles/tokens.css` … and the
   subsetted self-hosted `.woff2` faces."* Tokens and fonts, not layout.

4. **D1 finalize amended only the technology sentence.** `webclient-vue-11-finalize` amended the engine
   design doc's D13 row and `webclient-ui-design.md` L75 to say the view layer is a Vue 3 SPA. §5.1
   was left untouched, so the shipped client is *correct* against every binding contract it has.

The result is a faithful implementation of the wrong target. `openspec/specs/webclient-desktop-shell`
still requires *"The narrative log SHALL occupy the primary reading area, with supporting header,
status, placeholders, and action dock visible …"* — the §5.1 shape — and the client satisfies it. The
設計稿's actual contribution to the shipped product is `tokens.css` and the `.woff2` faces.

**This roadmap closes that gap and, critically, closes the process hole that created it**: it
supersedes `webclient-ui-design.md` §5.1–§5.2 outright rather than leaving a superseded document at a
higher precedence, and it names the layout as a *binding deliverable* of specific changes rather than
as background motivation.

---

## 2. Gap analysis: 設計稿 vs. shipped client

Measured on 2026-08-25 against the running client (`podman compose` image `elosern-mud:edge`,
1440×900 and 1280×720) and `docs/design/elosern-redesign/index.html`.

### 2.1 What the migration *did* carry over

The complete `:root` token set (ink-night palette, seal-red accent, gold focus ring, vitals colours,
type ramps, spacing, motion), the self-hosted font faces, the gold double focus ring, the
`prefers-reduced-motion` kill-switch, the not-color-only `.status-marker--*` utilities, and the
component *inventory* (25 components, all with Storybook stories). None of that needs redoing.

### 2.2 Layout architecture — the structural gap

| Aspect | 設計稿 | Shipped client |
|---|---|---|
| Root | `.game{position:fixed;inset:0}` full-bleed cinematic stage | CSS grid `auto / minmax(0,1fr) / auto / auto` |
| Backdrop | `.scene` + `.layer` (bank/lamp/fog), per-mode gradients, inset vignette, red low-HP vignette | none — the page background is flat `--ink-950` |
| Data panels | floating HUD islands anchored to corners (`--panel` + `backdrop-filter:blur(8–9px)` + `--shadow`) | boxed `<aside>` cards stacked in two 300px scrolling columns, no blur, no shadow, no z-layering |
| Narrative | lower-centre caption card, `width:min(880px,90vw)`, `max-height:30vh`, blurred, with a `完整日誌 ↑` escape hatch | fills the entire centre column, unbounded measure |
| Action dock | floating `clamp(150px,22vh,184px)` panel, `max-width:1180px`, icon tabs + count badges + `.crumb` breadcrumb | full-width bar of equal-width text buttons, no icons, no badges, no breadcrumb |
| Reference panels | seven right-side slide-in drawers (`width:min(560px,94vw)`) over a blurred scrim | six panels permanently stacked in the right column, most of them below the fold |
| Command line | always-visible 46px bar: `›` prompt, field, quick-word chips, history/Tab hints | collapsed `指令輸入（/）` button; the field only exists while open |
| Overlays | four full-screen overlays (map / settings / help / creation) reachable from the UI | only `CreationOverlay` is mounted; `MapOverlay`, `SettingsOverlay`, `HelpOverlay` are built, tested, manifest-listed — and imported by nothing |

`--dock-h` is defined in `tokens.css:88` and referenced by **zero** components. `@keyframes
elosern-toast-in`, `elosern-combat-pulse` and `elosern-hp-pulse` are defined in `tokens.css:92–113`
and referenced by zero components. The token file already carries the redesign's motion system; the
components never consumed it.

### 2.3 Contextual behaviour — the behavioural gap

The 設計稿's central thesis (REDESIGN.md §0.1) is *contextual HUD*: each game state shows only the
surfaces it needs, and hidden means hidden, not dimmed. REDESIGN.md §2 gives the full mode × surface
matrix, of which the load-bearing rule is **the minimap disappears in combat** and the companion strip
becomes the participant frame.

The shipped client renders `mode` onto `data-elosern-mode` on the root element — and **no stylesheet
or component selects on it**. Panel visibility is gated purely on data availability
(`panelAvailable('status')` etc.), so the minimap, the shop panel and the lore drawer stay mounted
through combat. Mode changes what the dock's *rows* contain; it changes nothing about *which surfaces
exist*.

Also absent: the trailing "damage taken" ghost bar on the HP track, the low-HP pulse and red vignette,
condition chips with duration badges and a `+N` overflow, the per-mode scene tint, and the
`--prose-scale` A−/A/A+ control (built inside the unmounted `SettingsOverlay`).

### 2.4 Surfaces the 設計稿 shows that no read model backs

Verified against `web/webclient/presentation/` and `web/webclient/actions/registry.py`:

| 設計稿 surface | Backing read model | Verdict |
|---|---|---|
| Scene backdrop image | `art.scene.{status,url,aspect_ratio,alt,placeholder}` — real on-disk asset via `world/art/presenter.py` | **backed** |
| Combat participant frame (token / name / HP / state) | `context_actions.participants[]` with `team`, `token`, `state`, `hp_current`, `hp_maximum`, `portrait_ref` | **backed** |
| Condition chips with severity + duration | `status.conditions[].{code,label,severity,remaining_seconds,modifiers}` | **backed** |
| Minimap fog-of-war | `local_map.nodes[].visibility` ∈ current / visible_unvisited / visible_visited / remembered | **backed** |
| Wallet, guild rank, merit, equipment, disguise true-vs-displayed | `character.{wallet,guild,equipment,disguise}` | **backed** |
| Held-item bag | `services.inventory.rows[]`, bounded to 32 (`MAX_INVENTORY_ROWS`) | **backed, bounded — but the true total is NOT surfaced**: `pagination.inventory_total` is `len(inventory.rows)` (`world/rules/service_view.py:757`), i.e. the *capped* count, so a bag holding more than 32 kinds cannot say how many it hides. The UI states the ceiling in words and never renders "32 of N". |
| World date/time | envelope `server_time` (already rendered in the top bar) | **backed** |
| Player's own portrait outside combat | `world/rules/art_view.py:176` — *"The actor itself is never a present focusable subject of their own exploration catalog"* | **not backed** — glyph placeholder only, exactly as the 設計稿 itself draws it |
| Race / subrace / class / faction on the character card | `character` payload carries `traits`, `equipment`, `disguise`, `guild`, `wallet`, `persona.background` — no race/class/faction fields | **not backed** |
| Companion / party panel (bond stage, affinity, follow) | none — `world.rules.party` gates affordances only, no roster read model | **not backed** |
| Event toasts | none — no `event-log` panel; only the synchronous per-action `result.message` | **not backed** |
| Persistent objective tracker | `services.guild.quests[]` carries one `objective_summary` string + `stage_index`/`stage_progress`; no per-objective array, and the `services` panel is absent outside a service host | **not backed as a persistent HUD surface** |
| 親密狀態 collapsible (arousal / wetness / shame / exposure / climax) | none in `status` or `character` | **not backed** |

The first group is built. The second group is **not built and not mocked** — same rule as migration
roadmap §7, and the existing `tests/overlays/deferred_surfaces_absent.test.js` assertion is extended,
not relaxed. A component is never faked to look real.

---

## 3. Goals and Non-Goals

**Goals**

- Ship the 設計稿's layout, information architecture, and contextual visibility model as the live
  client, at 1440×900 and a 1280×720 minimum.
- Make `mode` load-bearing: implement REDESIGN.md §2's mode × surface visibility matrix so hidden
  surfaces are absent from the layout, not dimmed.
- Move the reference panels out of a permanently-visible column into demand-opened drawers and
  overlays, and wire the three already-built, never-mounted overlays to real triggers.
- Consume the tokens the migration already extracted but never used (`--dock-h`, the three keyframe
  sets, `--prose-scale`).
- Keep every protocol, dispatch, epoch/revision, offline-degradation and keyboard-parity contract
  **identical**. This is a view-layer change, exactly as the Vue migration was.
- Close the process hole: supersede `webclient-ui-design.md` §5.1–§5.2 in place, so no superseded
  layout document outranks this roadmap.

**Non-Goals**

- No server, OOB schema, action allowlist, or presenter change. The six changes consume the eight
  allowlisted panels as-is.
- No new read model, and therefore no companion panel, no toast queue, no persistent objective
  tracker, and no 親密狀態 block (§2.4). Each gets its own OOB change when its read model lands.
- No mobile or tablet support. Desktop only.
- No change to the narrative *text stream*. The client renders what the server sends; curating the
  prose the server emits (today the raw room description, exit list and ASCII map reach the graphical
  feed verbatim) is a separate server-side concern — see §8.
- No back-compat and no data migration (0 released users). A stale persisted layout version is reset,
  not migrated.
- No second client. Telnet stays fully playable; the dependency-free text console stays the fallback.

---

## 4. Source of Truth and Precedence

Highest precedence first:

1. `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md` — the architectural source of truth.
2. **This roadmap** — authoritative for the WebClient's visual layout, information architecture, and
   contextual visibility model.
3. `docs/design/elosern-redesign/` (`index.html` + `REDESIGN.md`) — the **binding visual and IA
   reference**. Where this roadmap is silent on a visual or navigational detail, the draft governs.
   It is no longer "a design reference in `docs/`"; it is the target.
4. `docs/superpowers/specs/2026-08-02-webclient-ui-design.md` — retains authority over **everything
   except layout**: the OOB architecture, presenter/adapter boundaries, §7 surface *content*, and the
   focus model of §5.3. Its §5.1 (default desktop layout) and §5.2 (visual language) are
   **superseded** by items 2–3 above.
5. Each `webclient-hud-0N-*` change — the implementation contract for its own slice.

**Deliberate inversion of the migration's precedence chain.** The migration ranked
`webclient-ui-design.md` *above* its own roadmap, which is why §5.1 survived twelve changes. Here the
layout authority sits at 2–3 and the superseded sections are named explicitly. **H6 applies the
amendment in the document itself** — rewriting §5.1/§5.2 rather than leaving a contradiction for a
future reader to rediscover.

`webclient-ui-design.md` §14 requires a unit's proposal to be based on both the suite document and a
focused design. **This roadmap plus `docs/design/elosern-redesign/REDESIGN.md` together are that
focused design** for the HUD redesign; no separate per-unit design document is created.

---

## 5. Cross-Cutting Mechanics

These rules bind every sub-change.

- **The client stays shippable after every change.** No wave may leave the client in a state where a
  required surface is unreachable. A surface is moved from its old home to its new home *within one
  change*, never split across two.
- **Preserve the DOM contract, re-map the rest.** The identifiers the keyboard router, the public
  façades and the OOB bridge depend on — the single persistent `#action-dock` node with its `data-mode`
  attribute and listbox composite role, `#elosern-action-live`, `#elosern-offline-overlay`,
  `#inputfield`, `#narrative-unread`, and the `action-*` / `target-*` item keys — are **preserved
  unchanged**. Everything else re-maps to `data-testid`. This is the same mechanism
  `webclient-browser-verification` sanctioned for the GoldenLayout → Vue swap.
- **Each wave owns the browser assertions it breaks.** A change that relocates a surface re-maps the
  Playwright selectors for that surface *in the same change*, so the managed suite is green at every
  landing. H6 re-freezes the audit; it does not perform a deferred bulk re-map.
- **Truthful data scope (unchanged from migration roadmap §7).** No component may present data with no
  backing read model. The §2.4 unbacked surfaces stay absent and the deferred-surface assertion is
  extended to cover the new names.
- **Manifest grows, then re-freezes.** `component-manifest.json` is frozen at 25. Each wave that adds a
  component extends the `required` array and `MODIFIED`s the `webclient-component-showcase` frozen-set
  requirement in lockstep; H6 re-freezes at the complete set. Every new component ships with a
  Storybook story and offline deterministic args before it is wired, preserving the migration's
  showcase-before-wiring discipline.
- **Contextual visibility is CSS, driven by one attribute.** `data-elosern-mode` on the shell root is
  the single source for mode gating; a surface is hidden with `display:none`, never `opacity`/
  `visibility`, so hidden surfaces leave the accessibility tree and the tab order.
- **Motion is token-gated.** Every animation uses the `--motion-*` tokens so the existing
  `prefers-reduced-motion` block disables it at the token level.

---

## 6. Delivery Roadmap

| Order | OpenSpec change | Depends on | Delivers | Status |
|---|---|---|---|---|
| H1 | `webclient-hud-01-shell-and-scene` | — | the `webclient-contextual-hud` capability; the full-bleed cinematic shell (`.game` stage, `.scene` backdrop from `art.scene` + per-mode gradients + vignette), the HUD anchor frame replacing the 3-column grid, the mode × surface visibility matrix made load-bearing, the bounded lower-centre narrative caption card + `完整日誌` full-log overlay, the top-meta pill; existing panels re-homed into the anchors unchanged | Done |
| H2 | `webclient-hud-02-status-islands` | H1 | the left HUD island stack: character head card (glyph portrait, magic rank, guild rank), vitals with icons + trailing ghost bar + low-HP pulse and vignette, condition chips with severity glyph + duration + `+N` overflow, the minimap island with combat hide | Done |
| H3 | `webclient-hud-03-action-dock` | H1 | the floating dock: icon tab bar with count badges, `.crumb` breadcrumb + back, the pane vocabulary (exit outlet / target rows / suggestion cards / target affordances), the combat participant token frame and the skill master-detail (category → group → skill → power scale → target), the 2-step forfeit confirm; `#action-dock` and keyboard parity preserved | Done |
| H4 | `webclient-hud-04-reference-drawers` | H1, H3 | the right-side drawer surface (scrim, focus trap, Escape, slide transition) and the migration of SkillBook / InventoryPanel + equipment paper-doll / ShopPanel / QuestBoard / LoreDrawer / a full character-status drawer out of the right column into it; the right column is removed | Done |
| H5 | `webclient-hud-05-overlays-and-command-line` | H1, H2, H3 | the persistent command line (prompt chevron, always-visible field, history + hints, mode-contextual quick-word chips) replacing the collapsed drawer entry; `MapOverlay` / `SettingsOverlay` / `HelpOverlay` wired to real triggers; the `--prose-scale` A−/A/A+ control persisted through the settings surface | Done |
| H6 | `webclient-hud-06-remap-and-finalize` | H2, H4, H5 | apply the §5.1/§5.2 supersession into `webclient-ui-design.md`; re-freeze the browser contract audit and the component manifest at their complete new sets; extend the deferred-surface assertion; flip this roadmap's Status column; final gates | Done |

**Critical path:** `H1 → H3 → {H4, H5} → H6`. H2 depends only on H1 and runs parallel to H3, but **H5 also depends on H2**: H2's `webclient-local-map` delta withholds the minimap's full-map
affordance until the surface it opens is reachable, and H5 is the wave that mounts `MapOverlay`, so the
control lands in H5 editing H2's `LocalMap.vue` — a forced serialize under §7, not a merge.

**Sizing.** H1, H3 and H4 are each larger than the one-workday budget the migration roadmap set. A
wave that cannot be verified in one workday is **split, not stretched** — splitting a wave amends this
table (§9) and does not require re-opening the other waves.

---

## 7. Parallelism and File Ownership

A non-owner that needs to edit a row's file is a **forced serialize**, not a merge.

| Hot file | Author | Rule for all others |
|---|---|---|
| `components/AppShell.vue`, `AppClient.vue` | **H1** establishes the anchor frame → each later wave edits only its own slot | a structural edit to the frame serializes behind H1 |
| `styles/tokens.css`, `styles/app-shell.css` | **H1** | H2–H5 consume; a token addition serializes |
| `components/StatusPanel.vue`, `LocalMap.vue`, `ArtPanel.vue` | **H2** (H1 only re-homes them) | one sanctioned exception: **H5** adds the minimap's full-map control to `LocalMap.vue`, because H2's own delta forbids that control existing before H5 mounts the surface it opens — a forced serialize behind H2, not a merge |
| `components/ActionDock.vue`, `DockMenu.vue`, `DockMenuItem.vue` | **H3** | H5's quick-word chips live in the command line, not the dock |
| `components/{SkillBook,InventoryPanel,ShopPanel,QuestBoard,LoreDrawer}.vue` | **H4** | — |
| `components/CommandDrawer.vue`, `{Map,Settings,Help}Overlay.vue` | **H5** | — |
| `component-manifest.json` + `webclient-component-showcase` spec | each wave extends → **H6** re-freezes | the serial bottleneck; extend at your own archive, never two at once |
| `docs/development/webclient-vue-frozen-contract-audit.md` | **H6** (re-freeze) | H1–H5 record their re-maps in their own change; H6 consolidates |
| `docs/superpowers/specs/2026-08-02-webclient-ui-design.md` §5.1/§5.2 | **H6** | — |
| `openspec/specs/<capability>/spec.md` | applied only at a change's archive, topologically | never two archives of the same capability at once |

**Safe parallel lanes:** H2 ∥ H3 (disjoint component sets, both consume H1's frame); H4 ∥ H5 after H2 and H3
(drawers vs. command line + overlays are file-independent). Everything else is serial.

**Global rule:** coding may overlap; **merge and archive are strictly topological**.

---

## 8. Risks and Trade-offs

- **Raw telnet text in a cinematic feed.** The server currently sends the room description, the exit
  list and an ASCII minimap as narrative text; in a 30vh caption card that reads far worse than in a
  full-height log. → The `完整日誌` overlay (H1) keeps the whole stream reachable, and the caption card
  never truncates without an escape hatch. Curating the emitted prose is a **server-side follow-up,
  explicitly out of scope**; this roadmap must not silently narrow the text stream.
- **The 30vh caption card contradicts "narrative log occupies the primary reading area."** → H1 carries
  an explicit `MODIFIED` delta on `webclient-desktop-shell` re-expressing the requirement as
  "the narrative occupies the visual centre of the stage and the complete log is reachable in one
  action", and adds a scenario for the full-log overlay.
- **A persistent command line contradicts the closed-by-default drawer requirement.** → H5 carries the
  `MODIFIED` delta; the `#inputfield` id, the `/`-to-focus behaviour and the send/cancel focus-return
  contract are preserved, so the keyboard contract is unchanged even though the chrome is.
- **Overlapping floating islands at 1280×720.** Measured: the left island stack ends at y=474 and the
  dock begins at y=515 at 1280×720, so the anchors do not collide — but the margin is 41px and the
  island stack grows with condition count. → H2 caps the condition row at the `+N` overflow chip and
  every wave's browser acceptance asserts non-overlap at **both** supported viewports.
- **Drawers hide surfaces that are currently always visible.** A player who never opens a drawer loses
  sight of the shop/quest/lore panels. → That is the 設計稿's deliberate trade (REDESIGN.md §0.1,
  "不常用→隱藏"); H4 compensates with count badges on the dock tabs that open them, and the
  non-closable-surface requirement is narrowed to the dock, the narrative and the command line only.
- **Blast radius on the managed browser suite.** ~17 Playwright files assert `.art-panel__*`,
  `.local-map__*`, `.quest-board__*`, `.status-gauge__*` literal selectors, several of which are also
  pinned in spec *text*. → §5's per-wave re-map rule plus H6's re-freeze; the preserved-id list is
  frozen up front so `#action-dock`-based tests (11 files) never move.
- **Two pre-existing defects surfaced by the gap analysis, each fixed by the wave that touches it.**
  `stores/elosern.js:703-705`'s `openCharacter` branch sets `activeSubDock = "character"` and pushes no
  frame — the Character dock root has been a silent no-op ever since the permanently-visible right
  column *was* the character surface; **H4** gives it the surface it always implied.
  `QuestBoard.vue:155-161` dispatches the destructive `guild.quest_abandon` straight from a click with
  no confirmation, while the dock path has required a two-step confirm since the services wave; **H4**
  brings the pointer path to parity. Neither is new work invented by this roadmap — both are contract
  violations the old layout hid, and neither may be left for H6 to sweep up.
- **The settings overlay emits actions the server does not allowlist.** `SettingsOverlay.vue:74` emits
  `options.type_scale` (and siblings), but `options.dismiss` is the *only* allowlisted `options.*`
  action (`web/webclient/actions/registry.py:350`). The mismatch has never fired because the overlay is
  never mounted — wiring it in H5 is the moment it would. → H5 resolves it by treating the settings as
  **client-local presentation state** and carrying the `MODIFIED` delta on
  `webclient-component-showcase`'s "SHALL emit `options.*`" clause. Adding allowlisted actions would be
  a server change and is out of scope; the roadmap must not let a wave quietly widen the dispatch
  surface to make a component compile.
- **Repeating the migration's failure mode.** The whole point of §1. → §4 inverts the precedence chain
  and H6 *edits* the superseded sections rather than layering another document on top of them.
- **Six changes drifting from the draft.** → §4 item 3 makes `index.html` binding for unstated details,
  so a wave resolves a visual question by reading the draft, not by inventing.

---

## 9. Governance

- **The Status column is the tracker.** Flip each row `Planned → In-progress → Done` as it lands.
  `Done` only after `openspec validate <change> --strict` passes and that change's gates plus its
  focused test slice are green.
- **Every sub-change must cite this roadmap** in its `proposal.md` and adopt the "Depends on" column as
  its binding prerequisite. A sub-change may not start before its dependencies are `Done`.
- **Amending this roadmap.** A delivery-order or mechanic change — including splitting an oversized
  wave — is made by editing this document. A sub-change that resizes its own tasks does not edit it.
- **Precedence.** If a sub-change finds this roadmap wrong, it amends this roadmap rather than silently
  diverging. That is the rule whose absence produced §1.
