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

Each line must sound like the card's `speech_style` and preserve what the old line taught (the location's purpose, command names the specs pin, what the host deals in). Dynamic information stays authoritative: no fixed prices, stock counts, quest names, or availability promises in prose. Operational errors remain system lines and are not touched here. Lines stay within the existing dialogue session bound and the dialogue panel's four-choice shape.

### D4. Verification without pinning prose

The slice's data-contract test (first docstring line `Data-contract test: …`, registered in `tools/test_data_freeze.json`) asserts: every owned place names its own `service_id` as `host_profile_key` and it resolves; each owned profile authors `misunderstood` and no `greeting`; each owned table's keyword tuple equals the identifiers listed above and still has a greeting; no greeting or response equals any provisional line, checked against SHA-256 digests of the pre-change strings embedded in the test (digests, not prose, so the old wording is not re-pinned); no two owned profiles share a normalized `speech_style` or `personality`, and no two owned greetings are equal after replacing every host name and title with one placeholder. These checks prove coverage, not quality; quality is the recorded editorial review (task 4).

## Risks / Trade-offs

- [Rewritten lines drop a contract-pinned substring] → run the listed settlement/dialogue labels after the rewrite; `rg` each old line's distinctive phrases across `world`, `web`, `commands`, `tests` before editing to find pinned assertions.
- [Distinct-on-paper voices still read alike] → task 4's side-by-side review of same-profession hosts is mandatory and recorded; automated checks are explicitly not a substitute.
- [Cards exceed the budget after review edits] → the registry import fails immediately with the leaf/total reason; re-run the slice test after every edit.
