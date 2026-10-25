---
name: npc-dialogue-content
description: Author or review NPC-facing zh-TW content for Elosern, the JRPG fantasy MUD - authored multi-line dialogue scenes (`world/lore/dialogue/content/*.yaml`), persona cards, voice lines, offline greetings, shop and guild staff scenes. Use this whenever the task touches `world/lore/dialogue/`, `world/lore/npc_profiles/`, `world/lore/npc_card.py`, an `authored-dialogue-content-*` or `npc-persona-content-*` OpenSpec change, or the user asks to write, rewrite, polish, or review what an NPC says, even if they never say "dialogue" or "persona".
---

# NPC dialogue and persona content

An NPC is a person living inside the world. The player talks to a shopkeeper, not
to the game's help system. Every rule below follows from that: the moment an NPC
mentions a command or a mechanic, the fiction breaks, and the line also goes stale
the next time the command is renamed.

Dialogue is now a declarative scene player: a topic is a menu entry that selects
one complete linear scene of attributed speech and narration. Content is authored
data, never executable script. Static hosts live in YAML; generated dream hosts
live in immutable published scene packages. Both feed the same selection,
condition, refusal, chain and reading machinery.

## Mandatory source gate

BEFORE composing or reviewing any prose, read:

1. `tmp/story_settings/world_info.md` — the mandatory world source. If it is
   unavailable, stop: content authoring is blocked until the real source exists.
   Never substitute generic fantasy assumptions or invented lore.
2. The host's own canon: its `NpcProfile` in `world/lore/npc_profiles/<slice>.py`
   (card, voice), its `PlaceDefinition` in `world/lore/settlements/places.py`
   (name, title, race, profession, assortment, `dialogue_key`), plus the lore rows
   the scene actually references (race, religion, item, district).
3. `skill://chinese-content-writing-guideline` and `skill://writing-style-guideline`.

Record which source sections each reviewed line rests on. Pay explicit attention
to these traps, which generic fantasy gets wrong:

| Trap | Canon fact (verify in the source) |
|---|---|
| Elves as a downtrodden or quaint minority | ~300 elves in total across three branches; all three human/beastfolk nations treat elves as a rank above royalty and extend the highest courtesy. Rare, self-sufficient, not servants, not curiosities. |
| Elves with trades, schools, marriage | No fixed profession division, no formal schooling, no marriage, open relationships; ability comes from lifespan and oral transmission. |
| Elves with shame about the body | No shame about sex or nudity; other races look away out of awe rather than moral judgment. |
| Elven religion as public gospel | Elves never proselytise; outsiders do not know its content or even the three gods' truth. No non-elf NPC explains 神之秘法 or its chains. |
| 光明教會 as generic church | Its god is the 斐歐恩 (forest elf) ancestral deity; church-run 聖所 are brothels staffed by nuns and priests as a form of worship. |

## Where the content lives

- `world/lore/dialogue/content/<NpcProfile.key>.yaml` — the static scene dialogue.
  The filename stem IS the host profile key: flat directory, no owner field, no
  effect field, no file index, no hot reload. A host still needs a registered
  profile, a place row carrying its `dialogue_key`, and its inventory row in
  `world/lore/npc_profiles/inventory.py`; the topic-ID prefix is that key
  (`guild_staff.topic_01`), not the filename. Full loader/discovery contract:
  `docs/development/adding-npcs.md` Step 3.
- `world/lore/npc_profiles/*.py` — persona profiles, compact cards, voice lines
  (`voice.greeting` stays `None` for a scripted host; the YAML greeting owns the
  opener).
- `world/lore/npc_card.py` — the card contract. Leaves are capped at 600 code
  points, the identity section at 600, the whole card block at 2000, and the
  offline greeting at 300, so check lengths before polishing prose.
- Static YAML carries no `topic_effects`. Actions, quest offers and trade
  outcomes belong to the deterministic owners (quest scene packages, service
  components); authored prose never authorises gameplay.

Exact YAML keys, condition vocabulary, limits and a worked example:
`references/scene-schema.md`.

## Scene model

- A topic is a stable `topic_id`, a short `keyword` and menu `label`, a required
  `fallback` scene, and optional `variants`, `requires`, `unavailable`, `refusal`,
  `predecessors`, `disclosure`.
- A scene is ordered `speech` (`speaker: actor|host`) and `narration` lines.
  `actor` is the acting body: the player's own character, or the companion being
  possessed. `host` is the NPC being talked to. `narration` names neither.
- Formal scenes (`fallback` and every variant) MUST begin with a complete actor
  utterance. A refusal scene MAY begin with the host speaking.
- Aim for 3–8 meaningful lines with at least one real host response. Consecutive
  lines may share a speaker; scene lines are displayed one page at a time, so
  land each line as a complete beat.
- An actor line is the question or remark the menu label promises. Never put a
  decision in the player's mouth: no accepting a commission, paying, promising,
  claiming an identity or rank, or granting consent.
- Actor lines must stay true when a possessed companion speaks them. Do not
  identify the speaker's race, guild, gear or sex, and do not refer to the player
  character as "my master".
- Do not explain requirements in fiction. Locked-topic hints are generated from
  the declared conditions using canonical public labels; a refusal deflects in
  character instead of restating the requirement.
- Variants are complete alternative scenes chosen before playback, not mid-scene
  branches. The highest matching `priority` wins; the fallback must stay
  unconditional. Give explicit distinct priorities (e.g. 20 for a combined
  context, 10 for a single trait) and never duplicate one.
- `unavailable: hidden` (the default) is absent from the menu. `unavailable:
  locked` exposes the label, a generated hint and a `refusal` scene, and every
  locked topic MUST declare `requires` plus `refusal`. Qualify only genuinely
  optional personal content; service access, registration, turn-in and baseline
  information stay open.
- Chains: `predecessors` is a DAG inside the file, and a topic with any unread
  predecessor does not appear at all. `disclosure: pure_chain` means an
  effect-free public successor revealed after its predecessors in order; it MUST
  declare predecessors, MUST NOT declare `requires`, and no ancestor may declare
  `requires`. Use it for reading order only — never for rewards or protected
  facts.
- Topic and scene IDs are the persisted reading, unread and notification
  identity, not just labels. Keep them stable across rewrites; renaming creates a
  brand-new unread topic. Bump `revision` when a scene's lines change.
- Keep `keyword`/`label` recognisable so text clients still find the topic. Never
  rename the `guild_staff` topic IDs or the `回報` keyword: the guild turn-in path
  is bound to `回報` and `topic_04`.
- Every formal qualified delivery applies one talk-affinity step to the host,
  subject to the existing affinity budget; pure-chain successors and the guild
  turn-in path apply none. Never add topics to farm affinity.
- Size limits are load errors, not warnings: ≤16 topics per file, ≤8 variants per
  topic, ≤32 lines per scene, ≤2000 code points per line, ≤8192 canonical bytes
  per scene, ≤24576 bytes for the complete dialogue panel, and ≤16384 bytes for a
  delivery plus its reachable public successors. Keep scenes lean.

## In-character only

An NPC knows only its own world. It never names a command (`rest`, `buy`,
`shop stock`, `前往`, `guild list`), never explains game operations (熟練度,
整點結算, 指令), and never mentions UI or the scene player. Describe the
world-side equivalent instead.

| Out of character | In character |
|---|---|
| 輸入 `rest` 就可以休息 | 樓上有床，累了就上去躺一下 |
| 用 `shop stock` 看庫存 | 看看架上有什麼吧 |
| 去公會用 `guild list` 接委託 | 去公會大廳的看板找找委託 |
| 熟練度越高越快 | 做久了手腳自然就俐落了 |

- Mechanic paraphrases count as OOC even without a command: 歇下來, 越久越熟,
  and 不適 used for a negative status all leak the system underneath.
- A merchant only buys back goods its own assortment offers; never promise goods
  the host does not sell.
- Existing specs or tests that require dialogue to "name the commands" must be
  MODIFIED in the change's delta spec, with the tests switched to a "no backticked
  token / no OOC" assertion.

## Setting and register

- The setting is JRPG 劍與魔法奇幻. Avoid 中式武俠 vocabulary (過招, 劍招, 招式,
  祕技, 拜師, 功夫).
- Casual settings (shops, taverns, inns, baths, homes) use natural spoken
  zh-TW as in everyday small talk: particles 喔/啦/吧/嘛, short clauses, never
  essay-like prose. Only formal settings (on-duty officials, ceremonies, nobility)
  use formal phrasing. Pick the register from the NPC's setting, not the topic.
- Apply the `chinese-content-writing-guideline` bans (banned phrases, contrastive
  不是…而是, em-dash, physical verbs on abstract objects). Also: no sentence-final
  的, no mid-sentence colon, no reduplication, no 您/不舒服.
- The greeting is the host's own opener and the first thing a player sees. Replace
  it in the same rewrite; it is not a summary of the dialogue tree.

## Review pass

1. Prove the file loads before reading prose:
   `uv run --locked python -c "from world.lore.dialogue import DIALOGUE_SNAPSHOT"`.
   One bad file rejects the whole snapshot and blocks server startup; the error
   names file, profile and dialogue key.
2. Grep the content for backticks, the command words above, and mechanic
   paraphrases; any hit is OOC.
3. Read each line asking "could this character know this?" Anything about
   skills, ticks, stats, exposure bands, or the UI fails.
4. Check register against the setting, then the banned-pattern list.
5. Check scene shape: actor-first formal scene, actor line possession-safe, no new
   player commitment, at least one host line, 3–8 lines, complete beats.
6. Check qualification: only optional personal content is gated, service access is
   open, every locked topic has an in-character refusal, and no refusal or public
   chain leaks protected facts or restates the generated hint.
7. Check identity and limits: topic/scene IDs unchanged, revision bumped for edited
   lines, published slugs/word limits respected, no `topic_effects`, no owner
   field, guild turn-in keys untouched.
8. Update the host's `dialogue_table` row in
   `docs/development/npc-editorial-review.md` (faces: greeting, responses,
   service-semantics) in the same change, and the change's line-by-line review
   document when it owns one.

When reviewing someone else's content, report findings as `file:line`, the
offending phrase, which rule it breaks, and a suggested in-character rewrite.

## Workflow

- The lead agent authors content slices directly rather than delegating to
  subagents, so the whole set keeps one voice. Subagents are fine for review.
- A rewrite replaces every owned topic body, variant, refusal and the opening. Do
  not wrap an old one-line answer in actor/host padding: the old prose is
  discarded, only service behaviour and stable IDs survive.
- Behaviour tests use synthetic fixtures; naming shipped content needs a tagged
  data-contract test (first docstring line `Data-contract test: <rationale>`,
  registered in `tools/test_data_freeze.json`). Never pin prose text in a test.
- Before handoff run the focused module for the owning package plus
  `uv run --locked python -m tools.test_data_lint check`,
  `uv run --locked python -m tools.spec_traceability check`, and
  `uv run --locked python -m tools.contract_gate`; add new test modules to
  `.github/evennia-shards.json` in the same change.
- Parity matters: the same authored scene must read correctly in the browser
  player and in the text client's single emission.
