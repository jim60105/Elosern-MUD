## Context

See proposal.md for motivation. The slice's sources (from the foundation inventory, owner `ciaran_homes_a`):

| Service / profile key | Host | Title | Race | Sex | Profession | Table | Keyword identifiers (unchanged) |
|---|---|---|---|---|---|---|---|
| `ciaran_elenis` | 艾莉妮斯·達恩斯特瑞德爾 | 暗影谷村長老 | elf/ciaran | female | attendant | `ciaran_elenis_home` | 村子、基亞蘭、森林、往事 |
| `ciaran_gwenaera` | 格威娜拉·希爾維爾莉夫 | 暗影谷村綴飾者 | elf/ciaran | female | merchant | `ciaran_gwenaera_home` | 綴飾、晶符、耳環、舊飾 |
| `ciaran_hailiel` | 海莉爾·斯塔爾法爾 | 暗影谷村鑄刃者 | elf/ciaran | female | merchant | `ciaran_hailiel_home` | 鍛刀、影刀、鐵料、用刀 |
| `ciaran_lareneth` | 拉瑞內斯·妮特布倫 | 暗影谷村花饌好手 | elf/ciaran | female | merchant | `ciaran_lareneth_home` | 花饌、山產、茶點、口味 |

Grounding sources the writer must read before drafting: `docs/lore/settlement-locations.md` (暗影谷村 / Ciaran), `docs/lore/overview.md` and `world/lore/races.py` (the ciaran elf subrace and lifespan), and the row docstrings in `world/lore/settlements/places_ciaran.py`. Settlement and dialogue specs this content must keep satisfying: `ciaran-village-commerce` (a settlement without shops is fully playable; the village's hosts are its own people; one good is sold at two prices in two settlements), `ciaran-village-commons` (the village has an elder), `ciaran-village-crafts`, `merchant-dialogue` (a village host does not speak as a proprietor or call its goods stock), and `scripted-dialogue`.

Slice-specific constraints: All four hosts are long-lived ciaran elves in one village; their voices must differ by outlook and conversational behavior, not by name or by a decorative catchphrase. Trading hosts speak of sharing, not of a business. The elder's history must not invent events that contradict the settlement document.

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
