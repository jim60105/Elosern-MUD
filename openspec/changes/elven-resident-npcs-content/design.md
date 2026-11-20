# Design

## Context

Mechanism and behaviour are in `elven-resident-npcs-mechanism` (registry vocab, sync, route, roster). This slice only authors the 45 residents. Authoring prerequisites: `tmp/story_settings/world_info.md` §種族設定›精靈族／生活方式›性文化／社會與文化, `docs/lore/overview.md` 精靈諸節, `docs/lore/settlement-locations.md` 精靈村落與〈聚落差異深論〉, `skill://npc-dialogue-content`, `skill://map-data-authoring`, and the Chinese/writing-style content skills.

## Goals / Non-Goals

Goals: three villages × 15 authored chat-only residents, each with a home, an adult-woman persona, literal in-band stats, one conditional dialogue table, and the shared `resident` schedule. Names, homes, dialogue, and schedules resolve entirely to authored registries and existing shared rooms.

Non-Goals: no engine/runtime code, no loader/registry-list edits, no new schedule/capability vocabulary, no test module or manifest entry, no rework of the existing service hosts.

## Decisions

### D1 — Naming and identity

- Resident `key` is a new lowercase slug; a resident's `profile_key` equals its `key` (the established host convention). Display `name` is authored 名‧姓, unique across the resident roster for its village and never reusing an existing host's name. Elven names come from the world's elven naming pool (same source the existing 幽月谷村／暗影谷村／翠綠森林村 hosts use), not invented syllables from thin air.
- `race=elf`; `subrace` per village (`eolas`／`ciaran`／`fionnen`); `sex=female`.

### D2 — Adult register, ages unstated

Every card and line treats each resident as an adult woman. No prose states a year count or an apparent age. 幻童（伊歐拉斯族）residents are written as adult elves only — no child framing, no "外表十歲/永駐童年" phrasing, keeping the 裏設定 out of all dialogue/cards/articles. The `age`/`apparent_age` fields live in the profile only and are not echoed in prose.

### D3 — Literal stats in-band

`hp=10000, mp=10000, sp=10000`; `atk_phys`/`agility`/`defense` each authored 70–95; `magic_power` authored 100–200. Each resident gets one specific literal value per axis (authored, within band); no learning/body-enhancement multiplier is baked into stored traits. Element affinity is left to the subrace seed (never authored on the card).

### D4 — Homes and schedule targets

Fifteen new interior rooms per village under `content/maps/interiors/` (plus editor layouts), each with a real Exit onto the village's street/public node so scheduled traversal resolves. `home_room` is that room's ID. Every resident uses the existing `resident` schedule template; the resident sync (mechanism) binds `residence`→home and `market_square`→the village's authored shared public room (read from `content/maps/` and `settlement-locations.md` — e.g. 幽月谷村的溫泉浴場／共食棚／圖書館 以及另兩村的對應共用場所; never invented). Public rooms may be shared by multiple residents.

### D5 — Conditional dialogue shape

Each resident gets one `world/lore/dialogue/content/<key>.yaml` table (5–10 topics): baseline open topics (village life, the resident's own craft or pastime, the shared space they frequent) plus at least one optional topic gated behind `unavailable: locked` + `requires` + an in-character `refusal`, using the canonical condition vocabulary (`race_is`／`carries`／`affinity_at_least`／`skill_owned`／`time_period` 等). `greeting` is authored on the table; the profile keeps `voice.greeting=None` and authors `voice.misunderstood`. Actor lines stay possession-safe and never grant consent or commit; every formal scene begins with a complete actor utterance.

### D6 — Editorial review and generated context

One `docs/lore/` review document per village (or one combined resident-review document) records the line-by-line register/voice/source-fidelity check per resident. `docs/development/npc-editorial-review.md` gains one `resident` row per resident. `content/map-reference-context.json` is regenerated after the home rooms land.

## Risks / Trade-offs

- [45 × (home + card + table) is a large surface] → three village slices; reuse the shared `resident` template; keep tables lean (5–10 topics, ≤8 lines/scene).
- [Scheduled movement skips when a home lacks a street/public Exit] → each home authors that Exit; the content slice verifies via the map sources check + a per-village schedule runtime test.
- [A proper noun without a registry row] → each slice's review pass resolves every named place/item/title to a registry row; invented names are caught by the `--places` lint and the hand sweep before handoff.
- [Eolas secret leaking into prose] → the adult-register rule in D2 is a hard review checkpoint per card and line.

## Migration Plan

Content-only; no migration. `RESIDENT_REGISTRY` rows + profiles + tables + homes + inventory/ledger rows land together in this slice. Regenerate `content/map-reference-context.json`. No rollback beyond reverting the content.

## Open Questions

None blocking. The exact per-village public-space room ID and per-resident optional-topic conditions are fixed during authoring from the actual map/registry data; they do not change the mechanism, the spec, or the task breakdown.