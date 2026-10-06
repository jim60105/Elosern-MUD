---
name: npc-dialogue-content
description: Author or review NPC-facing zh-TW content for Elosern, the JRPG fantasy MUD - scripted dialogue, voice lines, persona cards, offline greetings, shop and guild staff lines. Use this whenever the task touches `world/lore/npc_profiles/`, `world/lore/dialogue/`, `world/lore/npc_card.py` content, an `npc-persona-content-*` OpenSpec change, or the user asks to write, rewrite, polish, or review what an NPC says, even if they never say "dialogue" or "persona".
---

# NPC dialogue and persona content

An NPC is a person living inside the world. The player talks to a shopkeeper, not
to the game's help system. Every rule below follows from that: the moment an NPC
mentions a command or a mechanic, the fiction breaks, and the line also goes stale
the next time the command is renamed.

## Where the content lives

- `world/lore/npc_profiles/*.py`: persona cards and profiles per settlement area.
- `world/lore/dialogue/*.py`: authored scripted dialogue and voice lines.
- `world/lore/npc_card.py`: the card contract. Leaves are capped at 600 code
  points, the whole card block at 2000, and the offline greeting at 300, so
  check lengths before polishing prose.

## In-character only

An NPC knows only its own world. It never names a command (`rest`, `buy`,
`shop stock`, `前往`, `guild list`), never explains game operations (熟練度,
整點結算, 指令), and never mentions UI. Describe the world-side equivalent instead.

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
  祕技, 拜師, 功夫). Elves have no fixed trades, schooling, or inherited posts.
- Casual settings (shops, taverns, inns, baths, homes) use natural spoken
  zh-TW as in everyday small talk: particles 喔/啦/吧/嘛, short clauses, never
  essay-like prose. Only formal settings (on-duty officials, ceremonies, nobility)
  use formal phrasing. Pick the register from the NPC's setting, not from the topic.
- Apply the `chinese-content-writing-guideline` bans (banned phrases, contrastive
  不是…而是, em-dash, physical verbs on abstract objects). Also: no sentence-final
  的, no mid-sentence colon, no reduplication, no 您/不舒服.

## Review pass

Run these over every line before calling content done:

1. Grep the content for backticks and for the command words above; any hit is OOC.
2. Read each line asking "could this character know this?" Anything about
   skills, ticks, stats, or the UI fails.
3. Check register against the setting, then the banned-pattern list.
4. For buy-back or service lines, confirm the host's assortment really covers it.
5. Check card, leaf, and greeting lengths against the limits above.

When reviewing someone else's content, report findings as `file:line`, the
offending phrase, which rule it breaks, and a suggested in-character rewrite.

## Workflow

- The lead agent authors content slices directly rather than delegating to
  subagents, so the whole set keeps one voice. Subagents are fine for review.
- When slices branch from master independently, shared test edits must be
  byte-identical hunks so they merge cleanly. Host-less test fixtures that
  `replace()` a shipped row must also set `host_profile_key=None`.
- Behavior tests use synthetic fixtures; naming shipped content needs a tagged
  data-contract test (see `AGENTS.md`).
