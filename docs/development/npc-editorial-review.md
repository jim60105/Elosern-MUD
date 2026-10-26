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
| `dialogue_table` | `altoria_eatery` | 2026-10-26 | 西格瑪‧庫柏 stirs the iron pot, welcomes the guest out of the wind and refers to the counter list for stock and portions | four multi-line scenes cover hot stew and rye bread, signature lobster soup with elven blossom lore, mountain travel rations and strict buying of fresh game | keeps the eatery's trade role and assortment; quotes no invented prices and grants no free food; service semantics unchanged | accepted: revised to r2 with full actor utterances and gesture-rich narration |
| `dialogue_table` | `altoria_tavern` | 2026-10-26 | 蘿溫‧古橡 tosses her cloth, rings her copper earrings and restates the rule that tavern talk leaves no regrets | four scenes cover listening for rumours with violet_altoria variant, pure-chain reflection on travel companions, guild commissions and lodging next door | sells no rumours, commissions or party slots; cups remain tavern atmosphere; service semantics unchanged | accepted: revised to r2 with pure-chain topic_02 continuation and companion variant |
| `dialogue_table` | `altoria_lodging` | 2026-10-26 | 溫弗蕾德‧古林 greets the guest warmly as 孩子 while checking the ledger with jingling brass keys | four scenes cover quiet upstairs rooms and solid latches, restful sleep vs wilderness camping, quiet study and Isabelle's bathhouse | offers hospitality and quiet study atmosphere without free heals or fee modifications; service semantics unchanged | accepted: revised to r2 with full actor questions and landlady care |
| `dialogue_table` | `altoria_bathhouse` | 2026-10-26 | 伊莎貝爾‧葦沼 emerges from the steam with warm towels and welcomes guests briskly, stating the house rule | four rich multi-line scenes cover partition rules with elf and exposure variants, elven rarity (~300 on the continent) and nudity shamelessness met by respectful awe, heated river water soaking while explicitly disclaiming magical healing, and cooling down on hall benches while directing overnight guests to Hearthstone Inn | runs no mechanism - the text itself denies that soaking heals anything and service semantics are unchanged | accepted: greeting is the sole source and service semantics hold |
| `dialogue_table` | `altoria_guardhouse` | 2026-10-26 | 托瓦德‧鄧堡 turns sharply from inspecting the south gate channel in chainmail, offering directions and order while stating the guardhouse issues no commissions | four rich multi-line scenes cover entering the city using wall map and canonical street names, seeking work by redirecting to guild bulletin boards, public defense by patrolling guards while disclaiming trade disputes, and resting on bare benches while directing travelers to Hearthstone Inn | orients with real street names, posts no work, and service semantics are unchanged | accepted: greeting is the sole source and service semantics hold |
| `dialogue_table` | `altoria_general_store` | 2026-10-26 | 瑪爾特‧金秤 looks up from the ledger and asks whether heading out or returning | four multi-line scenes cover exploration sundries, monster material buy-back, first-trip gear, and redirection for accessories/remedies/holy water | states the sundries assortment and board prices, buys back declared monster materials, and redirects to jeweller, alchemist and Grand Temple sanctuary; service semantics unchanged | accepted: multi-line actor-first scenes and greeting meet all lore/style rules; services unchanged |
| `dialogue_table` | `altoria_forge` | 2026-10-26 | 維爾登‧黑潭 keeps hammering and asks weapon preference and dominant hand | four multi-line scenes cover weapons rack, knight/magic blades, weapon buy-back, and blade care with a basic_swordplay skill-owned variant | bounds weapons to common arms, buys back intact weapons, directs ore to general store, offers swordsman maintenance advice; service semantics unchanged | accepted: multi-line actor-first scenes and greeting meet all lore/style rules; services unchanged |
| `dialogue_table` | `altoria_tailor` | 2026-10-26 | 妮絲塔‧狐溪 surfaces from colourful fabrics with tape measure and welcomes traveler | four multi-line scenes cover protective outfits, journey travel wear, formal/church vestments with a noble social-identity variant, and garment buy-back | names common outfits, noble formalwear, Grand Temple nun/saintess vestments, and buys back clothing for restitching; service semantics unchanged | accepted: multi-line actor-first scenes and greeting meet all lore/style rules; services unchanged |
| `dialogue_table` | `altoria_jeweller` | 2026-10-26 | 艾蓮娜‧鴉丘 puts down polishing cloth, observes collar and invites guest to view items in daylight or place keepsakes on velvet | four multi-line scenes cover capital adornments, claw settings with a protective_ring carried variant, imperial storage pouch/gliding cloak, and buy-back | bounds items to capital adornments, buys back covered items with provenance check on odd heirlooms, carried-ring variant does not consume or trade; service semantics unchanged | accepted: multi-line actor-first scenes and greeting meet all lore/style rules; services unchanged |
| `dialogue_table` | `altoria_alchemist` | 2026-10-26 | 希碧拉‧灰沼 peers out from behind bottle shelves with green-stained fingers, asking about injuries or expedition potions | four multi-line scenes cover healing/mana potions, topical herbal salve/miner broth, passion draughts with usage inquiry and red-label restriction, and holy water redirection | explains remedies accurately, keeps red-label brews behind counter, sends baptismal holy water up the 聖階 to the sanctum counter; service semantics unchanged | accepted: multi-line actor-first scenes and greeting meet all lore/style rules; services unchanged |
| `dialogue_table` | `altoria_merchant_hall` | 2026-10-26 | 尤斯汀‧柯德溫 rises from tariff table, greets with 閣下 and states at once that the chamber issues no escort commissions | four multi-line scenes cover trade caravans with a morning time-period variant, East Gate/East Market trade routes, lack of commission boards with guild redirection, and chamber civic governance | logs and coordinates caravans without arranging escorts or guaranteeing cargo, reviews tariffs and redirects work-seekers to guild hall; service semantics unchanged | accepted: multi-line actor-first scenes and greeting meet all lore/style rules; services unchanged |
| `dialogue_table` | `altoria_temple` | 2026-10-26 | 艾莉安娜‧寒水 closes the lectionary and greets the traveller with 願平安與你同在 in composed, modern formal sentences | four answers cover worship (with respectful elven variant), free blessings, open sanctuary ministry, and the deacon's shop counter | keeps worship, sanctuary and shop as three open counters under one roof, gives blessing without fee, and directs purchases to the deacon | accepted: greeting is the sole source and service semantics hold |
| `dialogue_table` | `altoria_sanctum` | 2026-10-26 | 羅海西亞‧芬威克 turns the ledger page, smiles and asks whether it is for oneself or a gift in light, friendly spoken zh-TW | four answers cover canonical wares across all categories, baptismal holy water, ritual vessels with buy-back, and sanctuary arrangements | lists sanctum_wares with prices on the counter card, explains light-magic contraception and mutual consent, and hands worship back to the main hall | accepted: greeting is the sole source and service semantics hold |
| `dialogue_table` | `altoria_noble_watch` | 2026-10-26 | 古利安‧鷹守 turns a page of the register, adjusts glasses and affirms the noble quarter sets no checkpoint | four multi-line scenes cover the open quarter with noble identity variant, the quiet royal palace approach, watch patrol/fire duties, and redirecting commissions to the adventurers' guild | keeps the watch to patrol, fire and errands; offers no audience arrangements or palace exemptions; service semantics unchanged | accepted: multi-line actor-first scenes meet all style and lore standards; noble variant priority 10 |
| `dialogue_table` | `altoria_drill_yard` | 2026-10-26 | 伊沃‧高丘 shakes mud off his sleeves, welcomes visitor bluntly and states there are no shortcuts | four multi-line scenes cover free practice and posts, guild rank examinations at the guild hall, sparring refusals and safety on soft dirt, and instructor duties emphasizing sweat over certificates | lends the field and the posts but promises no examination, opponent or certificate; service semantics unchanged | accepted: multi-line actor-first scenes meet all style and lore standards; natural veteran register |
| `dialogue_table` | `altoria_academy` | 2026-10-26 | 奧德溫‧薩契 erases a blackboard formula, sets down chalk and invites scholarly inquiries without shortcuts | four multi-line scenes cover magic tiers with magic_circle_comprehension skill-owned variant, the eight canonical elements, racial/individual affinity, and the refusal to tutor one student privately | teaches knowledge only, explains MP tiers and elements, sends rank-checking to the guild and refuses shortcuts; service semantics unchanged | accepted: multi-line actor-first scenes meet all style and lore standards; 拜師 keyword cleanly renamed to 求學 |

## ciaran dialogue tables

| kind | key | reviewed | greeting | responses | service-semantics | disposition |
| --- | --- | --- | --- | --- | --- | --- |
| `dialogue_table` | `ciaran_elenis_home` | 2026-10-26 | 艾莉妮斯‧達恩斯特瑞德爾 sits barefoot by the ancient tree with smoothed bark, warmly welcoming the youngster with no tasks or treasures | four conversational turns cover the underground village origin, the Ciaran line's enduring memory and blade intent via pure chain, forest respect and small generational memories | gives no tasks or items, demands no obedience, and shares lived history without dogma or wuxia tropes | accepted: rewritten r2 YAML with pure chain; non-commercial elder semantics hold |
| `dialogue_table` | `ciaran_gwenaera_home` | 2026-10-26 | 格威娜拉‧希爾維爾莉夫 sits behind her work table on silver-leaf slope, enthusiastically presenting two newly finished silver floral coils and inviting the guest to inspect her window cord ornaments | four multi-line scenes cover twisting silver wire and creek shells, prismatic crystal charms aiding spellcasting without grand claims, crescent earrings aired under silver leaves with Valwyn's matching pair, and repairing/recycling her own ornaments | bounds ornaments to elven_adornments, buys back and mends only self-made charms and earrings, refuses outside metals, and delivers no prose-granted crafting; service semantics unchanged | accepted: revised to r2 with full actor utterances, lively artistic persona, and grounded valley details |
| `dialogue_table` | `ciaran_hailiel_home` | 2026-10-26 | 海莉爾‧斯塔爾法爾 cools a freshly quenched blade in water amidst the low hearth glow, welcoming the guest to the anvil by the drill field while checking their dominant hand and grip | four multi-line scenes cover shadowsteel forging with a human_guest race variant, the paired off-hand shadow blade quenched in first frost, valley iron sand panning with self-forged blade buyback, and practical blade balance watched over by Teliel without wuxia terms | bounds arms to elven_crafted_arms, buys back only self-forged shadow blades in pairs, refuses outside iron ore, and delivers no prose-granted services; service semantics unchanged | accepted: revised to r2 with full actor utterances, quiet craftsman register, and human race variant priority 10 |
| `dialogue_table` | `ciaran_lareneth_home` | 2026-10-26 | 拉瑞內斯‧妮特布倫 stirs the honey pot in the stone home beside the stream and offers a candied blossom on a fresh thick leaf, inviting the guest to taste before conversing | four multi-line scenes with full actor-first exchanges cover candied blossom preparation and preservation, seasonal valley gathering and returning unopened jars, stream-side hospitality and sturdy travel packaging, and mild valley dietary palate | trades elven candied blossom for copper coins and accepts back unopened undamaged jars; hospitality taste and tea grant no free gameplay items or stat buffs; service semantics unchanged | accepted: multi-line actor-first scenes meet all style and lore standards; revision r2 declared across all fallbacks |
| `dialogue_table` | `ciaran_nireth_home` | 2026-10-26 | 妮瑞斯‧米斯特瓦勒 damps the medicinal stove in her home by the herb garden, examining the visitor's posture and shoulder for injuries before offering available bottled remedies | four multi-line scenes with full actor-first exchanges cover low-heat garden herb brewing and universal wound/mana needs, greater healing potion usage for critical trauma, mana potion restoring depleted pools, and refusal of outside herbs while accepting intact return of unused remedies | provides greater healing potion and mana potion for copper coins; buys back unopened intact potion jars and refuses outside herbs; does not heal by narration; service semantics unchanged | accepted: multi-line actor-first scenes meet all style and lore standards; revision r2 declared across all fallbacks |
| `dialogue_table` | `ciaran_teliel_home` | 2026-10-26 | 泰莉爾‧菲溫德 finishes her set at the field edge, checks stance, rejects student status and points to wooden blades by the door | four conversational turns cover blade intent and body momentum with basic_swordplay variant, solitary practice discipline, open day-night drill ground and firm refusal to spar | teaches no classes, grants no techniques, refuses casual duels, and directs practice to wooden blades and trees | accepted: rewritten r2 YAML with skill_owned variant; attendant instructor semantics hold |
| `dialogue_table` | `ciaran_valwyn_home` | 2026-10-26 | 瓦爾溫‧斯蒂爾瓦特爾 threads sea shells onto a leather cord beneath the northern elder tree and turns in delight, welcoming the guest and offering to share histories of her gathered curios | four multi-line scenes with full actor-first exchanges cover path-side hoarded curios and tagged keepsakes, resilient elven spider silk cordage, crescent earrings crafted by Gwenaera with an affinity-at-least familiar variant recognizing a known visitor, and trading travel stories while accepting intact silk returns | offers elven spider silk for copper coins and buys back intact unused bundles; trades stories without free gifts; earrings are display keepsakes directing guests to Gwenaera; service semantics unchanged | accepted: multi-line actor-first scenes meet all style and lore standards; priority 10 familiar variant is possession-safe; revision r2 declared across all fallbacks and variants |
| `dialogue_table` | `ciaran_vethiel_home` | 2026-10-26 | 維特希爾‧威爾德布瑞亞爾 pauses her wooden shuttle among warp threads, bare-chested with purple silk around her fingers, asking the guest's favored color and inviting them to feel the cloth | four multi-line scenes cover solitary loom weaving from dawn to starlight, agile ink-black battle dress for forest hunting, sheer ritual spider-silk robes and morning dew veils with open elven body pride, and taking back worn self-woven garments to re-spin threads | bounds clothing to elven_attire, buys back only self-woven garments to unpick threads, refuses outside clothing, and delivers no prose-granted tailoring; service semantics unchanged | accepted: revised to r2 with full actor utterances, gentle weaver persona, and complete turns |

## guild and companion, occupant and import sources

| kind | key | reviewed | greeting | responses | service-semantics | disposition |
| --- | --- | --- | --- | --- | --- | --- |
| `dialogue_table` | `guild_staff` | 2026-10-26 | 葛里安‧衛登 sets down the quill and looks up from the heavy register, greeting the adventurer and outlining branch registration, picking contracts from the board, and returning to report | four newly authored scenes with full two-turn exchanges cover registering at F rank without fees, taking commissions from the central board with safety advice, guild neutrality across three nations with an E-rank senior variant, and the formal turn-in settlement process verifying vouchers and vouchers before payout | preserves the 回報 native service turn-in and summary listing semantics, registration/board/exam authority remain unchanged, and topic_04 serves as the informational fallback | accepted: greeting is the sole source and service semantics hold |

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
