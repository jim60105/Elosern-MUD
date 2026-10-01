## Context

See proposal.md for motivation. The slice's sources (from the `npc-persona-profile-registry` inventory, owner `altoria_trade`):

| Service / profile key | Host | Title | Race | Sex | Profession | Table | Keyword identifiers (unchanged) |
|---|---|---|---|---|---|---|---|
| `altoria_merchant` | 瑪爾特·金秤 | 阿爾托利亞雜貨商店老闆 | human | other | merchant | `altoria_general_store` | 賣什麼、材料、行頭、飾品藥水 |
| `altoria_blacksmith` | 維爾登·黑潭 | 聖潔王都鍛造鋪鐵匠 | human/human_plains | male | merchant | `altoria_forge` | 兵器、好貨、賣鐵、保養 |
| `altoria_tailor` | 妮絲塔·狐溪 | 聖潔王都裁縫坊坊主 | human/human_plains | female | merchant | `altoria_tailor` | 衣甲、旅裝、禮服、收衣 |
| `altoria_jeweller` | 艾蓮娜·鴉丘 | 聖潔王都首飾坊主 | human/human_plains | female | merchant | `altoria_jeweller` | 飾品、鑲工、奇物、收飾 |
| `altoria_alchemist` | 希碧拉·灰沼 | 聖潔王都鍊金坊主 | human/human_plains | female | merchant | `altoria_alchemist` | 藥劑、外敷、特殊、聖水 |
| `altoria_merchant_master` | 尤斯汀·柯德溫 | 聖潔王都商會會長 | human | male | attendant | `altoria_merchant_hall` | 商隊、商路、委託、會務 |

Grounding sources the writer must read before drafting: `docs/lore/settlement-locations.md` (the middle terrace's craft alley, market belt and 商會), `docs/lore/items.md` for what each shop actually sells, the row docstrings in the places file, and the assortment rows in `world/lore/settlements/assortments.py`. Settlement and dialogue specs this content must keep satisfying: `merchant-dialogue` (every merchant answers and names what it deals in; no shared generic line), `altoria-learning-and-exchange` (the merchant hall does not implement the trade system it is the future home of), `commerce-assortments`/`shop-economy` (live stock and prices stay authoritative), and `scripted-dialogue`.

Slice-specific constraints: Five of these six hosts are merchants in one city, which is exactly where the design forbids profession-wide personas and name-substitution variants: each must differ in outlook and in speech behavior (register, rhythm, how they address a customer, what they ask first). Goods guidance must match each host's assortment rows and never quote a fixed price or stock count. Two hosts author sex `other`; prose and narration must not assign them a gendered pronoun. The merchant hall's master is an attendant: keep the line that the hall does not yet run caravans or trade contracts as a system.

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
