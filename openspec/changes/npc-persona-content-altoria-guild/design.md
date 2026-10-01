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

Grounding sources the writer must read before drafting: `world/lore/guild.py` (ranks, branch, examiner names and titles), `docs/lore/overview.md`, `docs/lore/settlement-locations.md` (the guild hall), and the guild-hall row in the places file. Settlement and dialogue specs this content must keep satisfying: `scripted-dialogue` (the `guild_staff` table teaches `guild register`, `guild list`, `guild accept`, `guild log`, `guild show`, `guild turnin`, `guild abandon`, `guild merit`, and the `talk <guild-staff> 回報 <任務編號>` path, and keeps the `回報` keyword as the register-first fallback), `guild-registration`, `guild-rank-exams`, and `npc-identity-titles`.

Slice-specific constraints: The guild-hall host is 葛里安·衛登, the branch master, authored with sex `other`, yet the provisional `guild_staff` greeting narrates an anonymous clerk as 「他」. The rewrite speaks as the branch master and uses no gendered pronoun for this host. The seven examiners are temporary combat opponents with no dialogue capability: their profiles carry complete cards and no voice lines, grounded in their rank's role (`GuildRank.description`, reward band, examiner title) without inventing exam mechanics. The guild-staff table's contract-pinned command substrings and the `回報` keyword must survive verbatim inside the new prose; the browser guild journeys that match those substrings must stay green.

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

Each line must sound like the card's `speech_style` and preserve what the old line taught (the location's purpose, command names the specs pin, what the host deals in). Dynamic information stays authoritative: no fixed prices, stock counts, quest names, or availability promises in prose. Operational errors remain system lines and are not touched here. Lines stay within the existing dialogue session bound and the dialogue panel's four-choice shape.

### D4. Verification without pinning prose

The slice's data-contract test (first docstring line `Data-contract test: …`, registered in `tools/test_data_freeze.json`) asserts: every owned place names its own `service_id` as `host_profile_key` and it resolves; each owned profile authors `misunderstood` and no `greeting`; each rank names `guild_examiner_<rank>` and those profiles author no voice lines; each owned table's keyword tuple equals the identifiers listed above and still has a greeting; no greeting or response equals any provisional line, checked against SHA-256 digests of the pre-change strings embedded in the test (digests, not prose, so the old wording is not re-pinned); no two owned profiles share a normalized `speech_style` or `personality`, and no two owned greetings are equal after replacing every host name and title with one placeholder. These checks prove coverage, not quality; quality is the recorded editorial review (task 4).

## Risks / Trade-offs

- [Rewritten lines drop a contract-pinned substring] → run the listed settlement/dialogue labels after the rewrite; `rg` each old line's distinctive phrases across `world`, `web`, `commands`, `tests` before editing to find pinned assertions.
- [Distinct-on-paper voices still read alike] → task 4's side-by-side review of same-profession hosts is mandatory and recorded; automated checks are explicitly not a substitute.
- [Cards exceed the budget after review edits] → the registry import fails immediately with the leaf/total reason; re-run the slice test after every edit.
