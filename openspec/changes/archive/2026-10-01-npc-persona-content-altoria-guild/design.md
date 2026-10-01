## Context

See proposal.md for motivation. The slice's sources (from the `npc-persona-profile-registry` inventory, owner `altoria_guild`):

| Service / profile key | Host | Title | Race | Sex | Profession | Table | Keyword identifiers (unchanged) |
|---|---|---|---|---|---|---|---|
| `altoria_guild_master` | 葛里安·衛登 | 阿爾托利亞分會會長 | human | other | guild_staff | `guild_staff` | 註冊、任務、公會、回報 |

| Rank | Profile key | Examiner | Title |
|---|---|---|---|
| F | `guild_examiner_f` | 雷加·鐵拳 | 公會見習考官 |
| E | `guild_examiner_e` | 薇拉·晨風 | 公會初階考官 |
| D | `guild_examiner_d` | 巴德·石肩 | 公會中階考官 |
| C | `guild_examiner_c` | 賽琳·夜鶯 | 公會高階考官 |
| B | `guild_examiner_b` | 霍克·赤刃 | 公會資深考官 |
| A | `guild_examiner_a` | 卡珊卓·銀輝 | 公會首席考官 |
| S | `guild_examiner_s` | 奧古斯丁·無名 | 公會傳說考官 |

Grounding sources the writer must read before drafting: `world/lore/guild.py` (ranks, branch, examiner names and titles), `docs/lore/overview.md`, `docs/lore/settlement-locations.md` (the guild hall), and the guild-hall row in the places file. Settlement and dialogue specs this content must keep satisfying: `scripted-dialogue` (the `guild_staff` table keeps the `回報` keyword as the register-first fallback and, as MODIFIED here, describes the counter in character), `guild-registration` (MODIFIED here the same way), `guild-rank-exams`, and `npc-identity-titles`.

Slice-specific constraints: The guild-hall host is 葛里安·衛登, the branch master, authored with sex `other`, yet the provisional `guild_staff` greeting narrates an anonymous clerk as 「他」. The rewrite speaks as the branch master, formally (an office-holder receiving adventurers at the counter), and uses no gendered pronoun for this host. The seven examiners are temporary combat opponents with no dialogue capability: their profiles carry complete cards and no voice lines, grounded in their rank's role (`GuildRank.description`, the exam profile's tier, examiner title) without inventing exam mechanics. Examiners spawn as `human` with no authored sex, so their cards use no gendered pronoun or gendered descriptor. The F examiner has no exam profile (F is the entry rank), so that card states no exam it does not run. The `回報` keyword identifier must survive; no browser journey matches the table's prose (the guild-counter browser tests drive the interface's register control).

## Goals / Non-Goals

**Goals:**
- A complete, individually voiced card for every NPC in this slice and a full rewrite of its authored dialogue, consistent with the card and with established world facts.
- Evidence that the rewrite is complete (no provisional line survives) and reviewable (recorded editorial review), without pinning the new prose in tests.

**Non-Goals:**
- Wiring the cards into any creation path, prompt, voice routing, or editor (other changes).
- Changing keyword identifiers, adding or removing topics, or changing any service, price, stock, quest, or command behavior.
- Rewriting any player preset or any NPC outside this slice.

## Decisions

### D1. Keyword identifiers and greeting presence are kept; prose is replaced

Keyword identifiers are the dialogue panel's choice labels and the scripted-talk lookup keys; tests and browser journeys select them, and the guild `回報` keyword is a mechanical action. The rewrite replaces every greeting and response string and keeps the four identifiers per table and the presence of the greeting. Alternative rejected: renaming topics for voice — it would change mechanics and the dialogue panel contract for no characterization gain.

### D2. Cards are grounded, compact, and distinct

Each card follows design §4.1 and §5.3: `identity.public` states the established role; `appearance` includes clothing relevant to the role; `personality` names traits plus a value, tension, or concrete interpersonal tendency; `speech_style` states register, sentence rhythm, how the host addresses the player, and conversational behavior; `life_story` is brief and consistent with the settlement document; `habit` is concrete. `identity.hidden` and `social_connection` are optional — use them only where they add character and contradict nothing (no invented quest hooks, rewards, access conditions, executable relationships, or historical events contradicting lore). Narration and prose follow each host's authored sex; a host with sex `other` receives no gendered pronoun. Every card must stay within the contract's rendered 2,000-code-point budget (the profile registry rejects it at import otherwise).

### D3. Dialogue is written against the card and stays mechanically truthful

Each line must sound like the card's `speech_style` and preserve what the old line taught (the location's purpose and what the counter offers), expressed in the world's own terms per D5. Dynamic information stays authoritative: no fixed prices, stock counts, quest names, or availability promises in prose. Operational errors remain system lines and are not touched here. Lines stay within the existing dialogue session bound and the dialogue panel's four-choice shape.

### D4. Verification without pinning prose

No test pins NPC prose, and this slice adds no data-contract test: an NPC line is authored content, and rewording it must never break a test. Existing pins that would break on a rewrite are removed: `test_dialogue_assembly`'s pre-split content digests (kept as a prose-free four-answer shape check) and the `guild <verb>` substring assertions in `test_dialogue` and `test_talk_turnin_commands`, which become comparisons with the host's own authored table plus a no-command-token assertion on the `guild_staff` table. What tests keep checking is mechanical: the shipped place registry validates (each `host_profile_key` resolves and the profile's card validates at registry import), every rank's examiner profile key resolves at guild-registry import (with a synthetic rejection test), every authored keyword still answers through the table API, the `回報` keyword still routes to the turn-in service and to the register-first fallback, and no talk path writes unexpected state. Completeness of the rewrite, voice distinctness and register are established by the recorded editorial review (task 4).

### D5. Dialogue and voice lines are in character

An NPC knows only its own world. No greeting, response, or voice line names a command, a game mechanic (merit numbers, rank thresholds, quest ids as data), or an interface element; it describes what the counter offers instead (sign the register, take a slip from the board, report back with the slip's number, hand a slip back, ask where one stands). The branch master speaks formally as an office-holder. The `回報` keyword stays because it is what a returning adventurer says; naming it in speech is in character. Command discoverability belongs to help, documentation and the interface, not to NPCs: the webclient's guild counter panel (`GuildCounter.vue`) already offers registering, accepting, abandoning, turning in, the rank and merit readout and the exam, and `help`, `docs/game/commands.md` and `docs/game/command-reference.md` list every `guild` command. The branch master's speech describes the in-world side of those same actions (taking a slip to the counter, handing it back, asking where one stands). This overturns `scripted-dialogue`'s and `guild-registration`'s wording that the table teach the guild commands; both requirements are MODIFIED here. The `scripted-dialogue` Purpose paragraph ("teach players the relevant commands") is not part of any requirement and cannot be changed by a delta; the archive step rewrites it to "answer authored talk lines in character". The `guild-registration` requirement keeps its title for traceability, and its body now forbids naming commands. Alternative rejected: keeping the commands "because new players need them" — it breaks character in the first line a new player hears, and help already lists them.

### D6. The examiner profile key is validated, not constructor-required

`GuildRank` gains `examiner_profile_key: str | None = None` as its last field. `validate_guild_npc_identities` rejects a rank whose key is missing or does not resolve in the profile registry, naming the rank, and it runs over the shipped registry at import, so every shipped rank must name its profile. The default keeps the twelve synthetic `GuildRank` fixtures in tests and browser support unchanged (they are never validated against the shipped profile registry). Alternative rejected: a constructor-required field, which would touch every synthetic fixture for no added safety.

## Risks / Trade-offs

- [Rewritten lines drop a contract-pinned substring] → run the listed settlement/dialogue labels after the rewrite; `rg` each old line's distinctive phrases across `world`, `web`, `commands`, `tests` before editing to find pinned assertions.
- [Distinct-on-paper voices still read alike] → task 4's side-by-side review of same-profession hosts is mandatory and recorded; automated checks are explicitly not a substitute.
- [Cards exceed the budget after review edits] → the registry import fails immediately with the leaf/total reason; re-import `world.lore.npc_profiles` after every edit.
