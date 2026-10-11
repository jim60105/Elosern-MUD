# NPC editorial review ledger

Indexed editorial review of the shipped NPC characterization: the immutable
profiles, compact cards, bounded voice lines and scripted greetings/responses
authored under `world/lore/npc_profiles/` and `world/lore/dialogue/`. The
authored prose stays authored and freely editable; this ledger records that a
reviewer read each live source and what that review covered, so completeness is
proved without pinning a single sentence, and no test ever compares prose.

Rows are indexed by the pair the live registries actually derive - the source
kind and its key (the same pairs
`world.rules.npc_roster_validation.derive_shipped_sources` produces). A kind and
a key are both needed: `altoria_tailor`, `altoria_jeweller` and
`altoria_alchemist` are each both a `place_host` key and a `dialogue_table`
key. Each row carries the review date, one disposition per face its kind owns,
and the overall disposition. The faces each kind owns are:

- `place_host`: profile, card, voice
- `dialogue_table`: greeting, responses, service-semantics
- `persistent_adventurer`: profile, card, voice
- `starting_companion`: card, voice
- `quest_template_occupant`: card
- `import_example`: card

A cell must never carry a bare `|` (escape it as `\|` or use a fullwidth ｜),
because the parser reads each row's cells to the last pipe. Keep backticked
identifiers out of any other pipe table in this document: the parse guard
treats a row-shaped line carrying a backtick as a ledger row it must accept or
report, so a decorative table would be reported as an unparsed row.

Update a source's entry in the same change that rewrites its profile, card,
voice or dialogue; a new live source has to arrive with its entry, because the
structural check in `world/lore/tests/test_npc_editorial_review.py` requires
exactly one dated, fully dispositioned entry per live source and rejects an
entry for a source the registries no longer derive. The declaration of which
faces a kind owns lives in `LEDGER_FACES_BY_KIND`
(`world/lore/npc_editorial_review.py`): a kind that grows a new authored
surface extends that declaration.

What this ledger does and does not prove: it proves that every live source was
reviewed on a stated date with a recorded disposition for each face its kind
authors. It does not judge prose quality, does not detect two contradicting
passages, and does not establish that a review is still fresh after a later
content edit - those remain editorial responsibilities, and no test asserts
them.

## altoria_lower hosts

| kind | key | reviewed | profile | card | voice | disposition |
| --- | --- | --- | --- | --- | --- | --- |
| `place_host` | `altoria_eatery_owner` | 2026-10-11 | key equals the place's service_id and resolves under slice altoria_lower | card reads as 西格瑪‧庫柏, the 南大道 eatery owner of twenty-odd years, matching the staple-meal service | misunderstanding reply stays the plain cook's voice and asks for a rephrase | accepted: profile, card and voice agree |
| `place_host` | `altoria_tavern_keeper` | 2026-10-11 | key equals the place's service_id and resolves under slice altoria_lower | card reads as 蘿溫‧古橡, the 醉月酒館 keeper who keeps the room's talk in order | misunderstanding reply is teasing and unhurried, asking what the newcomer wants to hear | accepted: profile, card and voice agree |
| `place_host` | `altoria_innkeeper` | 2026-10-11 | key equals the place's service_id and resolves under slice altoria_lower | card reads as 溫弗蕾德‧古林, the 爐火旅店 landlady who keeps rooms and quiet practice | misunderstanding reply calls the listener 孩子 and offers rooms, sleep or the bathhouse | accepted: profile, card and voice agree |
| `place_host` | `altoria_bathhouse_keeper` | 2026-10-11 | key equals the place's service_id and resolves under slice altoria_lower | card reads as 伊莎貝爾‧葦沼, the bathhouse keeper of twenty years who keeps the two sides in order | misunderstanding reply blames the water noise and asks the visitor to repeat louder | accepted: profile, card and voice agree |
| `place_host` | `altoria_guard_captain` | 2026-10-11 | key equals the place's service_id and resolves under slice altoria_lower | card reads as 托瓦德‧鄧堡, the 南門 衛兵隊隊長 who posts no work and points at the guild | misunderstanding reply stays clipped, refuses the question and names what he will answer | accepted: profile, card and voice agree |

## altoria_trade hosts

| kind | key | reviewed | profile | card | voice | disposition |
| --- | --- | --- | --- | --- | --- | --- |
| `place_host` | `altoria_merchant` | 2026-10-11 | key equals the place's service_id and resolves under slice altoria_trade | card reads as 瑪爾特‧金秤, the 市場街 sundries shopkeeper for light, compass and camp gear | misunderstanding reply is brisk and asks for a slow, ordered buy-or-sell statement | accepted: profile, card and voice agree |
| `place_host` | `altoria_blacksmith` | 2026-10-11 | key equals the place's service_id and resolves under slice altoria_trade | card reads as 維爾登‧黑潭, the 工匠巷 smith who forges blades and axes and resells bows and staves | misunderstanding reply is terse to the bone - two words about weapons | accepted: profile, card and voice agree |
| `place_host` | `altoria_tailor` | 2026-10-11 | key equals the place's service_id and resolves under slice altoria_trade (the same key also indexes a dialogue_table row) | card reads as 妮絲塔‧狐溪, the 裁縫坊 owner sewing armour, robes and upper-city vestments | misunderstanding reply stays warm and chatty, asking whether it is about clothes | accepted: profile, card and voice agree |
| `place_host` | `altoria_jeweller` | 2026-10-11 | key equals the place's service_id and resolves under slice altoria_trade (the same key also indexes a dialogue_table row) | card reads as 艾蓮娜‧鴉丘, the 首飾坊 jeweller of adornments, keepsakes and small enchanted carry-alls | misunderstanding reply is soft and exacting, asking whether it is about an item | accepted: profile, card and voice agree |
| `place_host` | `altoria_alchemist` | 2026-10-11 | key equals the place's service_id and resolves under slice altoria_trade (the same key also indexes a dialogue_table row) | card reads as 希碧拉‧灰沼, the 東市 鍊金坊 owner brewing remedy and mana potions | misunderstanding reply is flat and orderly, asking about the injury or the timing | accepted: profile, card and voice agree |
| `place_host` | `altoria_merchant_master` | 2026-10-11 | key equals the place's service_id and resolves under slice altoria_trade | card reads as 尤斯汀‧柯德溫, the 商會會長 who logs caravans and weighs tariffs | misunderstanding reply stays formal with 閣下 and 本人 and asks for another wording | accepted: profile, card and voice agree |

## altoria_guild hosts and people

| kind | key | reviewed | profile | card | voice | disposition |
| --- | --- | --- | --- | --- | --- | --- |
| `place_host` | `altoria_guild_master` | 2026-10-11 | key equals the place's service_id and resolves under slice altoria_guild | card reads as 葛里安‧衛登, the 阿爾托利亞分會 branch master behind the counter | misunderstanding reply is courteous and asks for the request again, more concretely | accepted: profile, card and voice agree |
| `persistent_adventurer` | `altoria_hok` | 2026-10-11 | resolves to its own adventurer profile, distinct from every host and other person profile | card reads as 霍克‧赤刃, a coastal-born B-grade adventurer living by the guild | offline greeting and misunderstanding reply both stay in the friendly seafarer's voice | accepted: profile, card and voice agree |
| `persistent_adventurer` | `altoria_cassandra` | 2026-10-11 | resolves to its own adventurer profile, distinct from every host and other person profile | card reads as 卡珊卓‧銀輝, an A-grade adventurer who assists the weekly exam | offline greeting and misunderstanding reply both stay in the measured examiner's voice | accepted: profile, card and voice agree |
| `persistent_adventurer` | `altoria_augustine` | 2026-10-11 | resolves to its own adventurer profile, distinct from every host and other person profile | card reads as 奧古斯丁‧無名, an S-grade adventurer with an older apparent age than his age | offline greeting and misunderstanding reply both stay in the quiet veteran's voice | accepted: profile, card and voice agree |

## altoria_upper hosts

| kind | key | reviewed | profile | card | voice | disposition |
| --- | --- | --- | --- | --- | --- | --- |
| `place_host` | `altoria_high_priestess` | 2026-10-11 | key equals the place's service_id and resolves under slice altoria_upper | card reads as 艾莉安娜‧寒水, the 光明神殿 主祭 who answers for worship, sanctuary and shop | misunderstanding reply is gentle and asks the traveller to repeat, plainly | accepted: profile, card and voice agree |
| `place_host` | `altoria_sanctum_deacon` | 2026-10-11 | key equals the place's service_id and resolves under slice altoria_upper | card reads as 羅海西亞‧芬威克, the 聖所 執事 minding the shop and sanctuary arrangements | misunderstanding reply is light and asks whether it is about the counter or the sanctuary | accepted: profile, card and voice agree |
| `place_host` | `altoria_noble_watch_captain` | 2026-10-11 | key equals the place's service_id and resolves under slice altoria_upper | card reads as 古利安‧鷹守, the 貴族區衛所 captain patrolling an open, ungated quarter | misunderstanding reply is formal, apologizes and asks for another attempt | accepted: profile, card and voice agree |
| `place_host` | `altoria_drill_instructor` | 2026-10-11 | key equals the place's service_id and resolves under slice altoria_upper | card reads as 伊沃‧高丘, the 校場 教頭 who keeps the field and teaches self-drill only | misunderstanding reply stays blunt and asks whether the visitor came to drill or chat | accepted: profile, card and voice agree |
| `place_host` | `altoria_academy_dean` | 2026-10-11 | key equals the place's service_id and resolves under slice altoria_upper | card reads as 奧德溫‧薩契, the 魔法學院 院長 who teaches levels, elements and affinity | misunderstanding reply stays scholarly and asks the question to be rephrased | accepted: profile, card and voice agree |

## ciaran_homes_a hosts

| kind | key | reviewed | profile | card | voice | disposition |
| --- | --- | --- | --- | --- | --- | --- |
| `place_host` | `ciaran_elenis` | 2026-10-11 | key equals the place's service_id and resolves under slice ciaran_homes_a; the elven age pair is authored as age 980 with apparent age 42 | card reads as 艾莉妮斯‧達恩斯特瑞德爾, the village elder who remembers and has nothing to give | misunderstanding reply is unhurried and calls the listener 小傢伙 | accepted: profile, card and voice agree |
| `place_host` | `ciaran_gwenaera` | 2026-10-11 | key equals the place's service_id and resolves under slice ciaran_homes_a; age 420 with apparent age 23 | card reads as 格威娜拉‧希爾維爾莉夫, the 綴飾者 of silver thread, shell and crystal sand | misunderstanding reply is bright and asks whether it is about jewellery or a repair | accepted: profile, card and voice agree |
| `place_host` | `ciaran_hailiel` | 2026-10-11 | key equals the place's service_id and resolves under slice ciaran_homes_a; age 480 with apparent age 30 | card reads as 海莉爾‧斯塔爾法爾, the 鑄刃者 forging shadowsteel by the drill field | misunderstanding reply is terse and asks whether it is about the blades | accepted: profile, card and voice agree |
| `place_host` | `ciaran_lareneth` | 2026-10-11 | key equals the place's service_id and resolves under slice ciaran_homes_a; age 390 with apparent age 26 | card reads as 拉瑞內斯‧妮特布倫, the 花饌好手 preserving blossom and honey | misunderstanding reply offers tea first and asks for a repeat | accepted: profile, card and voice agree |

## ciaran_homes_b hosts

| kind | key | reviewed | profile | card | voice | disposition |
| --- | --- | --- | --- | --- | --- | --- |
| `place_host` | `ciaran_nireth` | 2026-10-11 | key equals the place's service_id and resolves under slice ciaran_homes_b; age 460 with apparent age 33 | card reads as 妮瑞斯‧米斯特瓦勒, the 調藥者 brewing remedy and mana potions from her own garden | misunderstanding reply is flat and asks about the wound or the medicine | accepted: profile, card and voice agree |
| `place_host` | `ciaran_teliel` | 2026-10-11 | key equals the place's service_id and resolves under slice ciaran_homes_b; age 620 with apparent age 28 | card reads as 泰莉爾‧菲溫德, the 刀術導師 who keeps the drill field and teaches nobody by hand | misunderstanding reply is quiet and asks whether the visitor wants to drill | accepted: profile, card and voice agree |
| `place_host` | `ciaran_valwyn` | 2026-10-11 | key equals the place's service_id and resolves under slice ciaran_homes_b; age 370 with apparent age 20 | card reads as 瓦爾溫‧斯蒂爾瓦特爾, the 蒐羅者 whose hoard carries a story each | misunderstanding reply drifts off mid-thought and asks for a repeat | accepted: profile, card and voice agree |
| `place_host` | `ciaran_vethiel` | 2026-10-11 | key equals the place's service_id and resolves under slice ciaran_homes_b; age 450 with apparent age 36 | card reads as 維特希爾‧威爾德布瑞亞爾, the 織衣者 weaving dark robes, battle dress and white spider-silk | misunderstanding reply is dry and asks whether it is clothes or weaving | accepted: profile, card and voice agree |

## altoria dialogue tables

| kind | key | reviewed | greeting | responses | service-semantics | disposition |
| --- | --- | --- | --- | --- | --- | --- |
| `dialogue_table` | `altoria_eatery` | 2026-10-11 | 西格瑪‧庫柏 greets from the stove, asks whether the guest has eaten and names the counter's list as the stock authority | four keyword answers cover meals, the signature lobster soup, travel rations and buying in hunted meat | keeps the eatery's trade role; quotes no price or count, leaving both to the counter's list | accepted: greeting is the sole source and service semantics hold |
| `dialogue_table` | `altoria_tavern` | 2026-10-11 | 蘿溫‧古橡 leans on the bar, states the house rule and points at the room rather than at a notice board | four answers cover rumours, companions, commissions and a rest, each redirecting to people or the guild | sells nothing and promises no rumour or commission; the cups stay scenery | accepted: greeting is the sole source and service semantics hold |
| `dialogue_table` | `altoria_lodging` | 2026-10-11 | 溫弗蕾德‧古林 rises from the counter, calls the guest 孩子 and offers rooms and the hearth | four answers cover the room, sleeping, quiet practice and the bathhouse next door | speaks as a landlady of rooms and rest, quoting no rate, bill or stay entitlement | accepted: greeting is the sole source and service semantics hold |
| `dialogue_table` | `altoria_bathhouse` | 2026-10-11 | 伊莎貝爾‧葦沼 surfaces from the steam and states the one rule of the house, men left and women right | four answers cover the rule, the elven custom, soaking and resting outside | runs no mechanism - the text itself denies that soaking heals anything | accepted: greeting is the sole source and service semantics hold |
| `dialogue_table` | `altoria_guardhouse` | 2026-10-11 | 托瓦德‧鄧堡 turns from the stove and offers directions and rules while stating the post carries no contracts | four answers cover entering the city, seeking work, order on the streets and a bed for the night | orients with real street names and posts no work, pointing at the guild board and private deals | accepted: greeting is the sole source and service semantics hold |
| `dialogue_table` | `altoria_general_store` | 2026-10-11 | 瑪爾特‧金秤 looks up from the ledger and asks whether the visitor is heading out or back | four answers cover stock, materials, a first-trip kit and where accessories and remedies moved to | states the sundries bundle and its wall-board prices, and redirects jewellery, remedies and holy water elsewhere | accepted: greeting is the sole source and service semantics hold |
| `dialogue_table` | `altoria_forge` | 2026-10-11 | 維爾登‧黑潭 keeps hammering and asks what weapon and which hand, in three short clauses | four answers cover the wall, his best blades, buy-back and maintenance | bounds his wall to common arms and his buy-back to what he hangs, promising no repair service | accepted: greeting is the sole source and service semantics hold |
| `dialogue_table` | `altoria_tailor` | 2026-10-11 | 妮絲塔‧狐溪 surfaces from the cloth and measures the visitor up while asking where they are bound | four answers cover armour, travel wear, formal commissions and buy-back | names the common-outfit rack and the cathedral and upper-city orders without quoting a price | accepted: greeting is the sole source and service semantics hold |
| `dialogue_table` | `altoria_jeweller` | 2026-10-11 | 艾蓮娜‧鴉丘 puts down the cloth, studies the visitor's collar and invites them to browse | four answers cover adornments, setting and provenance, the two rare carry-alls and buy-back | bounds the glass case to capital adornments and the blessed and hunter's work, and asks after odd heirlooms | accepted: greeting is the sole source and service semantics hold |
| `dialogue_table` | `altoria_alchemist` | 2026-10-11 | 希碧拉‧灰沼 peers from behind the wall of bottles, still smeared green, and asks about the injury | four answers cover remedies, salves, the special shelf and where the baptismal holy water lives | never oversells an effect and sends holy water to the sanctum up the 聖階 | accepted: greeting is the sole source and service semantics hold |
| `dialogue_table` | `altoria_merchant_hall` | 2026-10-11 | 尤斯汀‧柯德溫 rises from the tariff table, greets with 閣下 and states at once that the hall issues no contract | four answers cover caravans, trade roads, contracts and chamber business, in complete formal sentences | logs and coordinates caravans without arranging escorts or guaranteeing cargo, and never says 賣 | accepted: greeting is the sole source and service semantics hold |
| `dialogue_table` | `altoria_temple` | 2026-10-11 | 艾莉安娜‧寒水 closes the lectionary and greets the traveller with 願平安與你同在 | four answers cover worship, blessing, the sanctuary and the shop | keeps worship, sanctuary and shop as three counters of one faith and answers truthfully for each | accepted: greeting is the sole source and service semantics hold |
| `dialogue_table` | `altoria_sanctum` | 2026-10-11 | 羅海西亞‧芬威克 turns the ledger page, smiles and asks whether it is for oneself or a gift | four answers cover the shelves, the baptismal holy water, ritual vessels and sanctuary arrangements | lists the ritual and intimate wares with prices on the counter card and hands worship back to the main hall | accepted: greeting is the sole source and service semantics hold |
| `dialogue_table` | `altoria_noble_watch` | 2026-10-11 | 古利安‧鷹守 looks up from the register and states that the noble quarter sets no checkpoint | four answers cover the quarter, audiences, the watch's duties and its refusal to post contracts | keeps the watch to patrol, fire and errands and points work-seekers at the guild | accepted: greeting is the sole source and service semantics hold |
| `dialogue_table` | `altoria_drill_yard` | 2026-10-11 | 伊沃‧高丘 walks back from the post, still dusty, and warns there is no shortcut here | four answers cover drill, examinations, sparring and instruction | lends the field and the posts but promises no examination, opponent or certificate | accepted: greeting is the sole source and service semantics hold |
| `dialogue_table` | `altoria_academy` | 2026-10-11 | 奧德溫‧薩契 erases a formula and sets down the chalk to welcome the visitor | four answers cover the five magic grades, the eight elements, affinity and why the academy has no apprenticeship | teaches knowledge only, sends rank-checking to the guild and refuses shortcuts | accepted: greeting is the sole source and service semantics hold |

## ciaran dialogue tables

| kind | key | reviewed | greeting | responses | service-semantics | disposition |
| --- | --- | --- | --- | --- | --- | --- |
| `dialogue_table` | `ciaran_elenis_home` | 2026-10-11 | 艾莉妮斯‧達恩斯特瑞德爾 looks up from the warm sitting stone with a strip of bark on her knee | four answers cover the village's move, the Ciaran line's love of blades, the forest and old small stories | gives nothing and asks for nothing, answering only what she remembers | accepted: greeting is the sole source and service semantics hold |
| `dialogue_table` | `ciaran_gwenaera_home` | 2026-10-11 | 格威娜拉‧希爾維爾莉夫 lifts two silver blossoms to the visitor and asks which looks better | four answers cover trinkets, the crystal talisman, the crescent earrings and repairs | hangs finished work on the window cord and takes broken pieces back, for a token or free | accepted: greeting is the sole source and service semantics hold |
| `dialogue_table` | `ciaran_hailiel_home` | 2026-10-11 | 海莉爾‧斯塔爾法爾 quenches a fresh blade, then looks at the visitor's hands and asks to see the grip | four answers cover forging, the offhand shadow blade, iron stock and matching blade to use | keeps to the valley's own iron and to what she forges, in pairs | accepted: greeting is the sole source and service semantics hold |
| `dialogue_table` | `ciaran_lareneth_home` | 2026-10-11 | 拉瑞內斯‧妮特布倫 holds out a leaf of honeyed blossom from behind the preserving jars | four answers cover the blossom confection, valley produce, tea and the mild valley taste | keeps to what she gathers herself and takes back unopened jars | accepted: greeting is the sole source and service semantics hold |
| `dialogue_table` | `ciaran_nireth_home` | 2026-10-11 | 妮瑞斯‧米斯特瓦勒 damps the stove and checks the visitor for wounds before speaking of the brew | four answers cover brewing, the strong healing potion, the mana potion and garden herbs | makes only the two potions and takes back unused jars, refusing outside herbs | accepted: greeting is the sole source and service semantics hold |
| `dialogue_table` | `ciaran_teliel_home` | 2026-10-11 | 泰莉爾‧菲溫德 finishes her last set, still sweating, and looks at the visitor's stance | four answers cover the blade, practice, the field and refusing to spar | keeps the field open day and night and teaches nobody by hand, giving nothing | accepted: greeting is the sole source and service semantics hold |
| `dialogue_table` | `ciaran_valwyn_home` | 2026-10-11 | 瓦爾溫‧斯蒂爾瓦特爾 hangs a string of shells and turns, delighted at a visitor | four answers cover the hoard, spider silk, the crescent earrings and trading stories | gives away spider silk and trades in stories, keeping the personal pieces for display | accepted: greeting is the sole source and service semantics hold |
| `dialogue_table` | `ciaran_vethiel_home` | 2026-10-11 | 維特希爾‧威爾德布瑞亞爾 steps out of the warp, shuttle in hand, and asks what colour the visitor likes | four answers cover weaving, the battle dress, the ritual robe and taking back old cloth | weaves and dyes alone and takes back only what she wove herself | accepted: greeting is the sole source and service semantics hold |

## guild and companion, occupant and import sources

| kind | key | reviewed | greeting | responses | service-semantics | disposition |
| --- | --- | --- | --- | --- | --- | --- |
| `dialogue_table` | `guild_staff` | 2026-10-11 | 葛里安‧衛登 sets down the quill and welcomes the visitor to the branch, asking whether it is to register or to hand in a contract | four answers cover registration, contracts, the guild itself and handing in, each naming the register as the guild's only record | carries the one rule-bearing 回報 keyword route that resolves contracts, and no other table imitates it | accepted: greeting is the sole source and service semantics hold |

| kind | key | reviewed | card | voice | disposition |
| --- | --- | --- | --- | --- | --- |
| `starting_companion` | `violet_altoria:lidzia_rosenthal` | 2026-10-11 | the derived card resolves from the 莉茲婭 partner preset's persona and passes the compact-card contract | speech_style and greeting keep the rigorous squire's register, warm only to 薇歐蕾特 | accepted: card and voice agree |
| `starting_companion` | `lidzia_rosenthal:violet_altoria` | 2026-10-11 | the derived card resolves from the 薇歐蕾特 partner preset's persona and passes the compact-card contract | speech_style and greeting keep the composed royal register with a trace of boyish curiosity | accepted: card and voice agree |
| `starting_companion` | `yuka_darknight:yuna_darknight` | 2026-10-11 | the derived card resolves from the 悠奈 partner preset's persona and passes the compact-card contract | speech_style and greeting keep the slow, gentle voice and its poised teasing | accepted: card and voice agree |
| `starting_companion` | `yuna_darknight:yuka_darknight` | 2026-10-11 | the derived card resolves from the 悠花 partner preset's persona and passes the compact-card contract | speech_style and greeting keep the brisk, bright register that warms at the blades | accepted: card and voice agree |

| kind | key | reviewed | card | disposition |
| --- | --- | --- | --- | --- |
| `quest_template_occupant` | `討伐林間盜匪:0:0` | 2026-10-11 | the blueprint persona reads as the bandit chief of the woodland path, with a hidden past as a dismissed gate guard | accepted: the card is a valid, in-character compact card |
| `import_example` | `example_character` | 2026-10-11 | the shipped reference card's persona reads as a plains-born apprentice swordsman keeping road notes for caravans | accepted: the card is a valid, in-character compact card |
| `import_example` | `yohanna_cooper` | 2026-10-11 | the shipped card's persona reads as 尤漢娜‧庫柏, the guild coopers' barrelwright | accepted: the card is a valid, in-character compact card |

## Notes

- No source rewritten by this change received a modified profile, card, voice or
  dialogue line: the review above is the first indexed record of the shipped
  corpus, taken over the current authored content, and the disposition of every
  source WP4 did not rewrite is worded as a read, not as a rewrite review.
- `import_example` sources carry a persona card and no separate greeting field,
  so their single reviewed face is `card`; the roster gate validates them
  through `validate_character(record, NPC)`.
