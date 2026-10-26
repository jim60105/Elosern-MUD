---
name: npc-dialogue-content
description: Author or review NPC-facing zh-TW content for Elosern, the JRPG fantasy MUD - authored multi-line dialogue scenes (`world/lore/dialogue/content/*.yaml`), persona cards, voice lines, offline greetings, shop and guild staff scenes. Use this whenever the task touches `world/lore/dialogue/`, `world/lore/npc_profiles/`, `world/lore/npc_card.py`, an `authored-dialogue-content-*` or `npc-persona-content-*` OpenSpec change, or the user asks to write, rewrite, polish, or review what an NPC says, even if they never say "dialogue" or "persona".
---

# NPC dialogue and persona content

An NPC is a person living inside the world. The player talks to a shopkeeper, not
to the game's help system. Every rule below follows from that: the moment an NPC
mentions a command or a mechanic, the fiction breaks, and the line also goes stale
the next time the command is renamed.

Dialogue is a declarative scene player: a topic is a menu entry that selects one
complete linear scene of attributed speech and narration. Content is authored data,
never executable script.

## Mandatory source gate

BEFORE composing or reviewing any prose, read:

1. `tmp/story_settings/world_info.md` — the mandatory world source. If it is
   unavailable, stop: content authoring is blocked until the real source exists.
   Never substitute generic fantasy assumptions or invented lore.
2. This skill and `references/scene-schema.md`, read from the **primary checkout**
   (`/var/home/jim60105/repos/MUD/.agents/skills/npc-dialogue-content/`). A
   feature worktree can predate the latest skill revision; the primary copy wins.
3. The host's own canon: its `NpcProfile` in `world/lore/npc_profiles/<slice>.py`
   (card, voice), its `PlaceDefinition` in `world/lore/settlements/places.py`
   (name, title, race, profession, assortment, `dialogue_key`), plus the lore rows
   the scene actually references (race, religion, item, district).
4. `skill://chinese-content-writing-guideline` and `skill://writing-style-guideline`.

Record which source section each reviewed line rests on. Pay explicit attention
to these traps, which generic fantasy gets wrong:

| Trap | Canon fact (verify in the source) |
|---|---|
| Elves as a downtrodden or quaint minority | ~300 elves in total across three branches; all three human/beastfolk nations treat elves as a rank above royalty and extend the highest courtesy. Rare, self-sufficient, not servants, not curiosities. |
| Elves with trades, schools, marriage | No fixed profession division, no formal schooling, no marriage, open relationships; ability comes from lifespan and oral transmission. |
| Elves with shame about the body | No shame about sex or nudity; other races look away out of awe rather than moral judgment. |
| Elven religion as public gospel | Elves never proselytise; outsiders do not know its content or even the three gods' truth. No non-elf NPC explains 神之秘法 or its chains. |
| 光明教會 as generic church | Its god is the 斐歐恩 (forest elf) ancestral deity; church-run 聖所 are brothels staffed by nuns and priests as a form of worship, and church vestments follow that doctrine. |
| 中式武俠 vocabulary | This is JRPG 劍與魔法奇幻. No 江湖, 客官, 過招, 劍招, 招式, 祕技, 拜師, 功夫, 掌門. |

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
  opener). Read-only for a content slice.
- `world/lore/npc_card.py` — the card contract. Leaves are capped at 600 code
  points, the identity section at 600, the whole card block at 2000, and the
  offline greeting at 300.
- Static YAML carries no `topic_effects`. Actions, quest offers and trade
  outcomes belong to the deterministic owners (quest scene packages, service
  components); authored prose never authorises gameplay.

Exact YAML keys, condition vocabulary, limits and a worked example:
`references/scene-schema.md`.

## Prose standard

A scene is a conversation, not a menu echo. Read one already-accepted scene
(`world/lore/dialogue/content/altoria_merchant.yaml` is the reviewed reference
for a sharp shopkeeper) and match its density before writing your own. The
examples below illustrate technique only: never carry another host's names,
prices, stock or promises into your scene.

1. **Complete the sentence and the turn.** No telegraphese. A clipped ending
   either disappears or becomes a reason-bearing closing line.
   - weak: `「要出城還是剛回王都？架上的燈與羅盤自己挑。」`
   - better: `「準備出城，還是剛回王都啊？要出城的話，架上的魔法燈和羅盤可以仔細挑；要是剛回來，帶了什麼素材就先放上秤，我替你估個價。」`
2. **Actor lines are real spoken questions with a follow-through**, not a
   one-clause prompt that reads like a menu click.
   - weak: `「請問店裡都備了些什麼行頭？」`
   - better: `「想請問一下，你這間店主要賣些什麼？出城要用的東西都有嗎？」`
   - A second actor turn is how a scene breathes: ask about price, use, timing,
     or a fair reason for the refusal that follows.
3. **Every listed item earns its clause.** Say what it is for.
   - weak: `「魔法燈、附魔羅盤、迷宮探照符，還有紮營用的防護石。」`
   - better: `「魔法燈先備好，迷宮深處黑得連手都看不清；再帶個附魔羅盤，走岔了路也比較容易找回方向。」`
4. **Narration carries a gesture and an attitude**, not just a movement.
   - weak: `他順手拉過算盤，指著後方整齊的木架。`
   - better: `他把算盤往手邊一拉，朝身後排列整齊的深色木架抬了抬下巴。`
5. **Positive framing first; refuse only where the fiction needs it.** State
   what the host does, then where the guest should go.
   - weak: `「這兩樣我不碰。不買也別亂碰。」`
   - better: `「護身首飾和療傷藥水，各有專門的店在賣。飾品去隔壁找艾蓮娜，藥水沿街走到東市找希碧拉。你照我說的找，準能找到合用的東西。」`
   - A blunt refusal stays blunt when that is the character:
     `「至於殺價嘛，就省點口水吧。」`
6. **Persona comes from concrete knowledge**, not adjectives: thirty years at
   the brass scale, the neighbours' names, which hand you swing with. Keep the
   host's own edge — sharp, clipped, warm, fussy — instead of flattening every
   voice into polite neutral.

Register follows the NPC, not the topic. Formal settings (branch counter,
on-duty guard, temple, noble watch) speak in complete formal sentences; casual
settings (eatery, tavern, inn, forge, shop) use everyday spoken zh-TW with
particles 喔／啦／吧／嘛 and short clauses. Never essay prose for a shopkeeper.

Each scene holds 3–8 lines, starts with a complete actor utterance, and carries
at least one real host response.

## Nothing invented

Prose may only name things the registries or the world source already declare.
Inventing one is the most common review failure, and it is silent — the dialogue
loader cannot detect it.

| Do not invent | Check against |
|---|---|
| place, street, district, shop, doorway names | `world/lore/settlements/places*.py`, `docs/lore/settlement-locations.md` |
| item, food, price, assortment | `world/lore/settlements/assortments.py`, `world/lore/items/`, `docs/lore/items.md` |
| F-rank or any commission type | `tmp/story_settings/world_info.md` 冒險者公會 §等級制度 and the quest registries |
| rank, title, office, organisation | the host's profile, `world/lore/guild.py`, world source §國家與政治 / §宗教與信仰 |
| fee, reward, discount, entitlement, healing, service | the place's service component and assortment; when no registry declares a number, describe the act without one |
| race, exposure band, skill, social identity, companion key | `RACE_REGISTRY`, `EXPOSURE_LEVELS`, `SKILL_REGISTRY`, `SOCIAL_IDENTITY_REGISTRY`, `PLAYER_PRESET_REGISTRY` |

Observed failures worth remembering: `西陵谷地` (no such place),
`平原黑水潭` (the smith's surname mistaken for a pond), `驅趕野鼠` (not an
F-rank commission type), `真功夫` (武俠 vocabulary). A name that sounds right is
not evidence.

The inverse also matters: item display names are canonical even when they read
oddly. `大術師補綴長袍` and `誘蠱蕾絲內衣` are registered equipment names
(`world/lore/items/data_named_equipment.py`), and 大術師 is a real academy title,
so never "correct" them into new wording — quote the registry, or avoid the
reference.

Before handoff, list every proper noun your scenes contain and the registry row
each one resolves to. If one has no row, rewrite the line.

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

- Mechanic paraphrases count as OOC when they describe a game state: 歇下來 as a
  status, 越久越熟 as a skill model, 不適 as a negative status, plus 系統, 選單
  and 按鈕. The same words used in their ordinary sense are fine.
- No backticks, no ASCII command tokens, no bracketed hint like 「（輸入⋯）」.
- Do not explain a requirement in fiction. Locked-topic hints are generated from
  the declared conditions with canonical public labels; a refusal deflects in
  character instead of restating the condition.
- A merchant only buys back goods its own assortment offers; never promise goods
  the host does not sell.
- Content-only slices add no tests and no manifest entries. If this change's own
  artifacts still demand a content assertion, reconcile that requirement in the
  change's artifacts before marking the affected tasks complete, and record the
  editorial checks in the review document instead.

## Scene model

- A topic is a stable `topic_id`, a short `keyword` and menu `label`, a required
  `fallback` scene, and optional `variants`, `requires`, `unavailable`, `refusal`,
  `predecessors`, `disclosure`.
- A scene is ordered `speech` (`speaker: actor|host`) and `narration` lines.
  `actor` is the acting body: the player's own character, or the companion being
  possessed. `host` is the NPC being talked to. `narration` carries no speaker
  attribution; it may name the host, never the actor.
- Formal scenes (`fallback` and every variant) MUST begin with a complete actor
  utterance. A refusal scene MAY begin with the host speaking.
- An actor line is the question or remark the menu label promises. Never put a
  decision in the player's mouth: no accepting a commission, paying, promising,
  claiming an identity or rank, or granting consent.
- Actor lines must stay true when a possessed companion speaks them. Do not
  identify the speaker's race, guild, gear or sex, and do not refer to the player
  character as "my master".
- Variants are complete alternative scenes chosen before playback, not mid-scene
  branches. The highest matching `priority` wins; the fallback must stay
  unconditional. Give explicit distinct priorities (20 for a combined or more
  specific context, 10 for a single trait) and never duplicate one. When two
  variants can both match, the more specific one takes the higher number.
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
  brand-new unread topic.
- `revision` bumps when the lines of an already-shipped scene change. A wholesale
  rewrite that replaces shipped prose moves to the next revision; polishing
  again inside the same unmerged change keeps the revision it already has.
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

## Deliverables of a content slice

Write only what the change's design lists. For an `authored-dialogue-content-*`
slice that is:

- the owned `world/lore/dialogue/content/<NpcProfile.key>.yaml` files;
- one line-by-line review document under `docs/lore/`;
- the host's `dialogue_table` row in `docs/development/npc-editorial-review.md`
  (reviewed date, greeting, responses, service-semantics, disposition);
- the slice's own `openspec/changes/<change>/tasks.md` checkboxes.

Not yours: runtime code, profiles, place bindings, another slice's YAML, the
loader, or any shared registration list. **Add no test module and no manifest
entry**: content is authored data, not logic, so a test would only pin prose and
break on the next polish. `world/lore` is already covered by its shard label, and
`tools/test_data_freeze.json` needs no row for a file that does not exist.
Editorial quality is carried by the review document, not by an assertion.

## Review pass

1. Prove the file loads before reading prose:
   `uv run --locked python -c "from world.lore.dialogue import DIALOGUE_SNAPSHOT; print(len(DIALOGUE_SNAPSHOT))"`.
   One bad file rejects the whole snapshot and blocks server startup; the error
   names file, profile and dialogue key.
2. Run the mechanical lint over your files:
   `uv run --locked python .agents/skills/npc-dialogue-content/scripts/npc_content_lint.py world/lore/dialogue/content/<host>.yaml`.
   It reports OOC and 武俠 tokens, backticks, ASCII commands, 您, sentence-final
   的, CJK–Latin spacing, half-width punctuation, calques, unbalanced 「」, scene
   shape and condition operands that do not exist in the registries. It reads the
   registries of the checkout that contains the target file, so running the
   primary copy against a worktree's content is safe (`--repo` overrides). Exit 1
   means an ERROR finding; WARN findings are prompts and fail only under
   `--strict`. Add `--places` when the scene names streets or buildings to get
   a heuristic list of place-like words missing from `places*.py`
   (warnings there are prompts, not verdicts).
3. Read the lint's WARN lines, then sweep every proper noun by hand and resolve
   it to a registry row (see *Nothing invented*). The lint cannot detect an
   invented title, fee, commission type or institution.
4. Read each line asking "could this character know this?" Anything about
   skills, ticks, stats, exposure bands, or the UI fails.
5. Check register against the setting, then the banned-pattern list: no 您, no
   sentence-final 的, no mid-sentence colon, no 疊字 such as 慢慢／輕輕, no
   half-width punctuation beside Chinese, single space between CJK and
   alphanumerics, no English calques (折入／賦能／拉齊, and 回填／深潛／落地 when
   used as calques rather than literally), no 中式武俠 vocabulary.
6. Check scene shape: actor-first formal scene, actor line possession-safe, no new
   player commitment, at least one host line, 3–8 lines, complete beats.
7. Check qualification: only optional personal content is gated, service access is
   open, every locked topic has an in-character refusal, and no refusal or public
   chain leaks protected facts or restates the generated hint.
8. Check identity and limits: topic/scene IDs unchanged, variant priorities
   distinct and most-specific-highest, no `topic_effects`, no owner field, guild
   turn-in keys untouched.
9. Run the language linter for anything the content lint does not cover and
   reach 0 errors:
   `sh /home/jim60105/.agents/skills/chinese-content-writing-guideline/scripts/lint.sh <file>`.
   Expected false positives are YAML keys, 分會會長 (會會) and ordinary
   reduplicated verbs such as 談談／說說; anything else is a finding.
10. Run the focused logic modules that exercise the shipped snapshot, then the
    gate:
    `world.lore.tests.test_dialogue_assembly`, `world.rules.tests.test_dialogue_sources`,
    `world.rules.tests.test_authored_dialogue_runtime`,
    `uv run --locked python -m tools.contract_gate`.
    Test commands in this repo take the single-token form
    `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb <label>`;
    pipes, redirects and `;` are rejected by the guard, and `.env.test` inside the
    repository is not used.

## Workflow

- A rewrite replaces every owned topic body, variant, refusal and the opening. Do
  not wrap an old one-line answer in actor/host padding: the old prose is
  discarded, only service behaviour and stable IDs survive.
- Write, then read the whole file aloud once as a conversation. Stiff actor lines
  and clipped host endings are the defects that survive a schema check.
- Behaviour tests use synthetic fixtures; naming shipped content needs a tagged
  data-contract test (first docstring line `Data-contract test: <rationale>`,
  registered in `tools/test_data_freeze.json`) — but a content slice adds none,
  because it adds no logic.
- Before handoff run `scripts/npc_content_lint.py` over every owned dialogue YAML
  file you changed,
  the focused module for the owning package, and
  `uv run --locked python -m tools.test_data_lint check`,
  `uv run --locked python -m tools.spec_traceability check`, and
  `uv run --locked python -m tools.contract_gate`.
- Parity matters: the same authored scene must read correctly in the browser
  player and in the text client's single emission.
