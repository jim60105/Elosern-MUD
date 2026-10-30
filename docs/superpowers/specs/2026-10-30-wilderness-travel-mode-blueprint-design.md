# Wilderness Travel Mode Blueprint

**Date:** 2026-10-30
**Status:** Blueprint approved by the user section by section on 2026-10-30. Each sub-project still needs its own spec.
**Implementation status:** Not implemented by this document.
**Scope:** Replace the AVG stage with a map-first travel presentation for wilderness exploration. Split the work into three sub-projects and define their boundaries, ordering, and shared contracts.

## 1. Problem

The AVG stage (`HudFrame.vue`) is built for one place, a few people, and one conversation. It assumes that scene changes are rare and that each one deserves a performance. Wilderness travel inverts every assumption:

- The decision data for travel is spatial: terrain, distance, fords, and how far the party can still walk. The stage gives most of the screen to one backdrop that does not change for hundreds of kilometres, and squeezes the map into a corner minimap and a drawer.
- Every 1 km step costs 20 to 40 minutes of game time and produces a paragraph of narration. Players either read every paragraph or learn to ignore the message band.
- The stage polish proposed earlier (step parallax, day-night filters, marching bob) animates a surface that players should not be looking at during travel.

Comparable travel games (Sunless Sea, Battle Brothers, The Banner Saga, Oregon Trail, Darkest Dungeon camp screens, BotW landmark sighting, Caves of Qud zone layering) put the map on screen during travel and bring people and illustrations in only for events. This blueprint follows that pattern.

## 2. Travel budget facts

Source: `openspec/specs/mental-reserve/spec.md`. A full reserve is 360000 units, foot travel costs 8 units per second, and walking from full to zero takes 45000 seconds (12.5 hours). Fatigue stages scale foot speed by 1, 0.90, 0.75, and 0.50.

| Terrain | Normal (100% to 70%) | To the end of light fatigue (40%) | To zero |
| --- | --- | --- | --- |
| Open ground (1200 s per cell) | 11 cells | 21 cells | about 30 cells |
| Woodland (1800 s per cell) | 7 cells | 14 cells | about 20 cells |
| Mountain trail (2400 s per cell) | 5 cells | 10 cells | about 15 cells |
| Road (800 s per cell, not implemented in the wilderness) | 16 cells | 32 cells | about 46 cells |

Counts are orthogonal steps; diagonal steps cover about 0.7 times as many cells. Sleeping from zero to full takes about 8 hours 20 minutes. A walk from 聖潔王都 to 咆哮王城 (about 830 cells) needs about 40 camps. The travel loop is therefore "walk 10 to 30 steps, then camp", repeated dozens of times. Walking plus sleeping takes about 21 hours, so "walk by day, camp at night" fits the numbers.

## 3. Decisions

1. **Movement unit stays one cell.** The server still settles one 1 km step per `explore.move`. The redesign changes presentation and input only.
2. **Layout A, full-bleed ink map.** Of the three layouts compared (full-bleed map, map with a vertical vista window, scene strip above a map), the full-bleed map was chosen.
3. **Travel is a presentation variant, not a server mode.** The server mode stays `exploration`. The client switches to the travel layout while the current room is a wilderness cell (`subject_id` prefixed `wilderness:`).
4. **The browser never derives eligibility or time.** Route previews come from a server-side read-only query, and steps execute through the existing transactional move.
5. **Time of day is shown by the map's tint, and night has rule consequences.** Night shrinks sight so that players prefer to camp at night.

## 4. Screen composition (layout A)

| Region | Travel-mode element | Replaces |
| --- | --- | --- |
| Full-bleed main surface | `TravelMap`: ink map, revealed cells, distant-sighting markers, route preview, party token with the neighbour compass on it | `SceneBackdrop` and both actor anchors |
| Top right | `PlaceCard` (unchanged) | — |
| Lower left | Party medallions: round face crops, reserve bar, fatigue and sleep marks | `CompanionLineup` |
| Band, left 2/3 | Travel log: one line per noteworthy event; full scenery prose through 環顧 or the full log | Per-step narration in `MessageWindow` |
| Band, right 1/3 | Leg panel: today's leg gauge, 保守／標準／強行, 紮營, 環顧; 停步 while walking | Movement parts of `ExitCompass` and `ActionDock` |
| Map bottom edge | `PresenceRail` (unchanged) for same-cell figures and the existing person-focus card | — |
| Centre card anchor | Event cards: landmark arrival, sighting, camp | New |
| Drawer | `MapDrawer` with only the world tab | The area tab merges into the main surface |

Transitions:

- Leaving a settlement onto its approach cell crossfades the stage to the map over `--motion-scene`. Entering a settlement reverses it.
- Dialogue and combat in the wilderness use the existing dialogue and combat layouts, with the region's scene art as backdrop, and return to the map when they end. Those layouts are unchanged.
- At motion level `off`, transitions finish in the commit's frame.

Excluded: a new server mode, changes to the dialogue and combat layouts, and the backdrop parallax or day-night filters proposed for the AVG stage during travel.

## 5. Movement and the daily leg

Both inputs produce a sequence of single steps.

- **Neighbour step.** Aim with the arrow keys and press Enter, or click a neighbour cell next to the token. Holding for 400 ms walks continuously in that direction, as the current `ExitCompass` does.
- **Destination.** Click any revealed cell to preview a route, then click again or press Enter to depart. Esc cancels. Unrevealed cells cannot be destinations, so this is never whole-map auto-routing.

The **pace setting** decides where today's walking stops. It applies to both inputs, including held walking.

| Setting | Stops at | Open ground |
| --- | --- | --- |
| 保守 | Entering light fatigue (70%) | 11 cells |
| 標準 (default) | Entering moderate fatigue (40%) | 21 cells |
| 強行 | No voluntary stop; stops when preflight refuses | about 30 cells |

A separate **stop at nightfall** toggle (入夜停步) defaults to on.

Walking also stops when a landmark is sighted or reached, when a new monster enters ground sight, when a member falls asleep, when preflight refuses, or when the player presses any key.

The route preview marks each step's predicted fatigue stage by colour, the nightfall point with a moon mark (later steps are dimmed), the stop point with a camp mark, and the total duration.

The map tint has four phases: dawn, day, dusk, and night. At night, revealed cells outside current sight fade to a memory tint, leaving a small clear circle around the party. Night travel stays legal, but sight shrinks and distant sighting shows only light sources.

## 6. Shared server and client contracts

1. **`travel.plan` (read-only query).** Input: the destination cell and the pace setting. The server routes eight-directionally over revealed cells only, using the existing pure functions (`plan_traversal`, reserve prediction, terrain rates). It returns each step's cell, duration, and predicted fatigue stage, plus the nightfall point, the stop point, and the stop reason. It writes nothing and never ticks the clock.
2. **Step execution.** The client sends the existing `explore.move` for each previewed step and waits for each commit before sending the next. Every step result carries **interrupt flags** (landmark sighted or reached, new monster in sight, pace threshold crossed, nightfall, member asleep). Any flag, a preflight refusal, a disconnect, or a key press stops the queue. Each step remains its own transaction.
3. **Neighbour step and held walking** keep the current `ExitCompass` logic and also stop on interrupt flags.
4. **Travel log entries** come from structured server events (region entered, landmark sighted, fatigue stage changed, nightfall, camp result). The client never infers importance from prose.

## 7. Sub-projects

### 7.1 Sub-project 1: sight and fog reveal (rules)

In scope:

- Ground sight radius by terrain and time of day, enlarged by elevation prominence and by authored vantage landmarks. Ground sight reveals terrain, passability, fords, roads, and monsters.
- Permanent reveal: every cell that has entered ground sight stays revealed and can be a destination. This replaces the current visited-cells-only memory.
- Distant-sighting markers: tall landmarks, mountains, and light sources beyond ground sight produce a bearing and an approximate distance without revealing cells. At night only light sources remain.
- No change to the anti-peek rule: unrevealed cells are never sent to the browser.
- Interrupt flags and `travel.plan` (section 6), because both depend on sight and reveal.

Questions for its spec: the sight radius per terrain and time of day, and the sighting distances; who owns the reveal record (character, account, or party); its storage format and size bound; how to enlarge the `area_map` window and packet limit; whether sighting a landmark lights its district; and how to migrate existing visit records.

The detailed design is in [Wilderness Sight and Fog Reveal](2026-10-30-wilderness-sight-and-fog-reveal-design.md).

### 7.2 Sub-project 2: travel-mode interface

The detailed design is in [Wilderness Travel-Mode Interface](2026-10-30-wilderness-travel-interface-design.md).

In scope: the layout in section 4, both inputs and the pace setting in section 5, the map tint, the travel log, the leg panel, event cards, and the settlement transitions. The layout and step-by-step movement can ship before sub-project 1; the destination input waits for `travel.plan`.

### 7.3 Sub-project 3: lightweight camping

The detailed design is in [Lightweight Wilderness Camping](2026-10-30-wilderness-camping-design.md).

- 紮營 opens one camp card with one main choice: 睡到天亮 (default after nightfall) or 睡到精力全滿 (default in daytime). Camping from dusk to dawn takes about 12 hours, which covers a full refill.
- The dream-collaboration question becomes a checkbox on the card, unchecked every time; ticking it is that sleep's explicit opt-in, replacing the separate prompt after falling asleep.
- One confirmation puts the whole party to sleep.
- The camp event card shows a campfire scene illustration with anonymous seated silhouettes painted into the art. The party appears as the same round medallions used in travel, in an arc along the card's lower edge; each reserve bar fills from its pre-sleep to its post-sleep value, and sleepers carry a moon mark. Standing portraits are not reused, because the `data-fallen="down"` deformation does not read as sitting. After about 1.5 seconds the result line appears (for example 「夜裡無事。全隊精力恢復至 100%，第 13 日 05:50」) and the map returns. The card is skippable; at motion level `off` the result shows directly.
- When a member is forced asleep while walking, the existing handoff menu stays, with 全員紮營 as its first option leading to the camp card.
- New art: one campfire scene. This is the only new art in the blueprint.

Excluded: night ambushes, watch rolls, and the ambient respawn cooldown (ecology rules, handled separately).

### 7.4 Ordering

Sub-project 1 is the prerequisite for `travel.plan` and interrupt flags. Sub-project 2's layout and step movement can start in parallel, and its destination input lands after sub-project 1. Sub-project 3 depends only on the current sleep rules and can run in parallel with sub-project 1.

The remaining items from the earlier analysis (overland roads, continuous scenery narration, ambient respawn cooldown) are independent and out of this blueprint.

## 8. Testing direction

- Server: deterministic unit tests for `travel.plan`, interrupt flags, sight radius, and reveal persistence, including the anti-peek guarantee.
- Client: vitest for the step queue (stops on any interrupt, sends the next step only after a commit) and for the pace and nightfall stop rules as reported by the server.
- Layout: Storybook stories plus browser screenshots at 1451×790 and 2560×1440.
