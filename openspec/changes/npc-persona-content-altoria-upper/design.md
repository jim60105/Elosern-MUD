## Context

See proposal.md for motivation. The slice's sources (from the `npc-persona-profile-registry` inventory, owner `altoria_upper`):

| Service / profile key | Host | Title | Race | Sex | Profession | Table | Keyword identifiers (unchanged) |
|---|---|---|---|---|---|---|---|
| `altoria_high_priestess` | 艾莉安娜·寒水 | 聖潔王都光明神殿主祭 | human | female | clergy | `altoria_temple` | 禮拜、祝禱、聖所、商店 |
| `altoria_sanctum_deacon` | 羅海西亞·芬威克 | 聖潔王都聖所執事 | human | female | merchant | `altoria_sanctum` | 賣什麼、聖水、禮器、聖所事務 |
| `altoria_noble_watch_captain` | 古利安·鷹守 | 聖潔王都貴族區衛隊長 | human | male | attendant | `altoria_noble_watch` | 貴族區、謁見、衛所、委託 |
| `altoria_drill_instructor` | 伊沃·高丘 | 聖潔王都訓練場教頭 | human | male | attendant | `altoria_drill_yard` | 修煉、考核、切磋、教頭 |
| `altoria_academy_dean` | 奧德溫·薩契 | 聖潔王都魔法學院院長 | human | male | attendant | `altoria_academy` | 魔法等級、元素、親和、拜師 |

Grounding sources the writer must read before drafting: `docs/lore/settlement-locations.md` (the upper terrace, palace, noble quarter, temple and academy), `docs/lore/magic-system.md`, `world/lore/church/`, and the row docstrings in the places file. Settlement and dialogue specs this content must keep satisfying: `altoria-sanctum` (one temple building with three open counters; the sanctuary's host ministers and does not trade; the sanctum's goods trade through the ordinary path), `church-ordination`, `altoria-crown-and-watch` (the crown's rooms stand open until a story closes them; the watch posts no work of its own), `altoria-learning-and-exchange` (the academy is where magical knowledge is asked about and does not implement the system it is the future home of), `merchant-dialogue`, and `scripted-dialogue`.

Slice-specific constraints: The high priestess ministers and must not be voiced as a trader; the sanctum deacon trades through the ordinary shop path and must not quote fixed prices. The two watch/drill hosts and the academy dean are attendants whose tables orient and teach; they must not invent audiences, exams, apprenticeships, or bounties that the specs rule out. The dean's magical guidance must match `docs/lore/magic-system.md` (elements, affinity, magic tiers).

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

Each line must sound like the card's `speech_style` and preserve what the old line taught (the location's purpose and what the host deals in), expressed in the world's own terms per D5. Dynamic information stays authoritative: no fixed prices, stock counts, quest names, or availability promises in prose. Operational errors remain system lines and are not touched here. Lines stay within the existing dialogue session bound and the dialogue panel's four-choice shape.

### D4. Verification without pinning prose

No test pins NPC prose, and this slice adds no data-contract test: an NPC line is authored content, and rewording it must never break a test. Existing pins that would break on a rewrite are removed: `test_dialogue_assembly`'s pre-split content digests (kept as a prose-free four-answer shape check), the drill instructor's command and 「沒有陪練」 pins in `test_altoria_crown_watch`, the dean's 「沒有『拜師』這道門」 and command pins in `test_altoria_learning_exchange`, and `test_altoria_sanctum`'s requirement that the deacon's table quote a trade command. What tests keep checking is mechanical or registry-derived: the shipped place registry validates (each `host_profile_key` resolves and the profile's card validates at registry import); every authored keyword answers through the table API; attendant tables carry no trade verb, no 「賣」 and no backticked command token; the priest's table offers no trade; no line frames the sanctuary as concealed; the academy's rank answer still recites every rung and example spell and its element answer every element, read from the lore registries; the deacon's table names its own goods (`merchant-dialogue`). Completeness of the rewrite, voice distinctness and register are established by the recorded editorial review (task 4).

### D5. Dialogue and voice lines are in character

An NPC knows only its own world. No greeting, response, or voice line names a command, a game mechanic (proficiency, hourly settlement, stock lists as a UI, multipliers), or an interface element; it describes what the world offers instead (the yard's posts, a room and the hours put into drilling, the guild's rank trials, the academy's books, the price board on the counter). The priestess, the noble-quarter captain and the dean speak formally; the deacon and the drill instructor speak colloquially. The noble-quarter table stops naming the builder-only `地圖`. Command discoverability belongs to help, documentation and the interface, not to NPCs. No settlement spec pins command names in these tables (the old pins lived in tests), so no requirement is modified. Alternative rejected: keeping `rest`/`practice`/`guild exam` in the instructor's and dean's tables "because the yard exists to teach them" — the yard's purpose survives in the world's terms, and help already lists the commands.

## Risks / Trade-offs

- [Rewritten lines drop a contract-pinned substring] → run the listed settlement/dialogue labels after the rewrite; `rg` each old line's distinctive phrases across `world`, `web`, `commands`, `tests` before editing to find pinned assertions.
- [Distinct-on-paper voices still read alike] → task 4's side-by-side review of same-profession hosts is mandatory and recorded; automated checks are explicitly not a substitute.
- [Cards exceed the budget after review edits] → the registry import fails immediately with the leaf/total reason; re-import `world.lore.npc_profiles` after every edit.
