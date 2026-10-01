## Context

See proposal.md for motivation. The slice's sources (from the `npc-persona-profile-registry` inventory, owner `altoria_lower`):

| Service / profile key | Host | Title | Race | Sex | Profession | Table | Keyword identifiers (unchanged) |
|---|---|---|---|---|---|---|---|
| `altoria_eatery_owner` | 西格瑪·庫柏 | 聖潔王都餐館老闆 | human/human_plains | male | merchant | `altoria_eatery` | 餐點、招牌、乾糧、收食 |
| `altoria_tavern_keeper` | 蘿溫·古橡 | 聖潔王都酒館老闆 | human | female | attendant | `altoria_tavern` | 傳聞、同伴、委託、歇腳 |
| `altoria_innkeeper` | 溫弗蕾德·古林 | 聖潔王都旅店老闆娘 | human | female | attendant | `altoria_lodging` | 房間、過夜、修煉、澡堂 |
| `altoria_bathhouse_keeper` | 伊莎貝爾·葦沼 | 聖潔王都公共浴場管理員 | human | female | attendant | `altoria_bathhouse` | 規矩、精靈、泡湯、歇息 |
| `altoria_guard_captain` | 托瓦德·鄧堡 | 聖潔王都衛兵隊隊長 | human | male | attendant | `altoria_guardhouse` | 進城、找活、治安、過夜 |

Grounding sources the writer must read before drafting: `docs/lore/settlement-locations.md` (南門、南大道、客棧巷 and the lower terrace), the row docstrings in the places file, and `docs/lore/overview.md`. Settlement and dialogue specs this content must keep satisfying: `altoria-hospitality` (each host's dialogue teaches what its location is for; a hospitality location adds no mechanism it does not have), `altoria-crown-and-watch` (the watch posts no work of its own), `merchant-dialogue` (the eatery host answers and names what it deals in), and `scripted-dialogue`.

Slice-specific constraints: Three hosts are attendants whose whole service is conversation (tavern, inn, bathhouse); their tables are the location's only function, so each rewritten line must still teach what the place is for without promising drink effects, gambling, rest mechanics, or services that do not exist. The guard captain's table must keep stating that the watch posts no work and point to the existing guild board and private commissions. The eatery host is a merchant: keep the goods guidance consistent with its live assortment and never quote fixed prices.

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
