## Context

See proposal.md for motivation. The slice's sources (from the `npc-persona-profile-registry` inventory, owner `ciaran_homes_b`):

| Service / profile key | Host | Title | Race | Sex | Profession | Table | Keyword identifiers (unchanged) |
|---|---|---|---|---|---|---|---|
| `ciaran_nireth` | 妮瑞斯·米斯特瓦勒 | 暗影谷村調藥者 | elf/ciaran | female | merchant | `ciaran_nireth_home` | 調藥、重傷、魔力、藥草 |
| `ciaran_teliel` | 泰莉爾·菲溫德 | 暗影谷村刀術導師 | elf/ciaran | female | attendant | `ciaran_teliel_home` | 刀術、練習、練刀場、比劃 |
| `ciaran_valwyn` | 瓦爾溫·斯蒂爾瓦特爾 | 暗影谷村蒐羅者 | elf/ciaran | female | merchant | `ciaran_valwyn_home` | 蒐羅、蛛絲、耳環、以物易物 |
| `ciaran_vethiel` | 維特希爾·威爾德布瑞亞爾 | 暗影谷村織衣者 | elf/ciaran | female | merchant | `ciaran_vethiel_home` | 織衣、戰衣、禮袍、舊衣 |

Grounding sources the writer must read before drafting: `docs/lore/settlement-locations.md` (暗影谷村 / Ciaran), `docs/lore/overview.md`, `world/lore/races.py`, and the row docstrings in `world/lore/settlements/places_ciaran.py`. Settlement and dialogue specs this content must keep satisfying: `ciaran-village-commerce` (the village's hosts are its own people), `ciaran-village-commons` (the village has a sword instructor; shared spaces carry no institution and no counter), `ciaran-village-crafts` (adornments and remedies from homes; an elven-made good is everyday at home), `merchant-dialogue`, and `scripted-dialogue`.

Slice-specific constraints: The sword instructor teaches through conversation only and must not promise a training mechanic beyond what the commons spec allows. The remedy-maker and weaver trade by sharing; the gatherer's 以物易物 topic must describe the existing ordinary trade path, not a barter system. Voices must differ from each other and from the first four homes.

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

Each line must sound like the card's `speech_style` and preserve what the old line taught (the location's purpose and what the host shares, naming at least one of its own goods), expressed in the world's own terms per D5. A trading host buys back only goods its own assortment carries. Dynamic information stays authoritative: no fixed prices, stock counts, quest names, or availability promises in prose. Operational errors remain system lines and are not touched here. Lines stay within the existing dialogue session bound and the dialogue panel's four-choice shape.

### D4. Verification without pinning prose

No test pins NPC prose, and this slice adds no data-contract test: an NPC line is authored content, and rewording it must never break a test. What tests keep checking is mechanical: the shipped place registry validates (each `host_profile_key` resolves and the profile's card validates at registry import), every authored keyword answers through the table API, every village trading table names one of its own goods and carries no proprietor vocabulary (`merchant-dialogue`), and the village's trade and commons behaviour is unchanged (the instructor carries no trade or teaching capability). Completeness of the rewrite, voice distinctness and register are established by the recorded editorial review (task 4).

### D5. Dialogue and voice lines are in character

A villager knows only the village's world. No greeting, response, or voice line names a command, a game mechanic, or an interface element; it describes what the home offers instead (jars by the window, silk on the line, robes on the rack, wooden blades by the door, the posts on the clearing). All four speak colloquially; the instructor is spare. The old tables folded `shop stock`, `buy`, `sell`, `rest`, `practice` and `engage` into their lines; the `ciaran-village-commons` requirement that the instructor "teach through the proficiency system that already exists and grant nothing directly" is honoured in the world's terms (practise on the clearing yourself, nobody hands you skill), so no requirement is modified. Alternative rejected: keeping the commands "because the instructor exists to teach practice" — her purpose survives in her own words, and help already lists the commands.

## Risks / Trade-offs

- [Rewritten lines drop a contract-pinned substring] → run the listed settlement/dialogue labels after the rewrite; `rg` each old line's distinctive phrases across `world`, `web`, `commands`, `tests` before editing to find pinned assertions.
- [Distinct-on-paper voices still read alike] → task 4's side-by-side review of same-profession hosts is mandatory and recorded; automated checks are explicitly not a substitute.
- [Cards exceed the budget after review edits] → the registry import fails immediately with the leaf/total reason; re-import `world.lore.npc_profiles` after every edit.
