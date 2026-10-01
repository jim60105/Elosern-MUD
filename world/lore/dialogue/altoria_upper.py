"""聖潔王都 (capital_altoria) UPPER-terrace authored dialogue rows.

The temple, sanctum, noble watch, drill yard and academy tables, keyed
exactly as the UPPER-terrace place rows in ``places_altoria_upper.py``
author them. Each table is written against its host's persona card in
``world/lore/npc_profiles/altoria_upper.py``.

Every line is spoken in character: a host knows only its own world, so no
line names a command, a game mechanic or an interface element. The priest,
the noble-quarter captain and the dean speak formally; the deacon behind the
shop counter and the drill instructor on the yard speak colloquially. The
sanctum's ministry is common knowledge in this world, so no line frames it
as hidden (altoria-sanctum).

Four keyword answers at most: the dialogue panel ships
``DIALOGUE_MAX_CHOICES`` entries and silently drops the rest, so each row
here carries exactly four.
"""

from world.lore.dialogue.shape import DialogueDefinition, KeywordResponse

# 艾莉安娜·寒水 — the 主祭 of the 光明神殿. Her counter is the dais: worship,
# blessing, the rite of joining the church, and straight answers about what
# this building is. The source document binds her register
# (docs/lore/settlement-locations.md §神殿／聖所): worship, the sanctum's
# ministry and its shop are one building's three open counters, common
# knowledge everywhere. She trades nothing, so she sends shoppers to the
# 執事's counter and never offers goods herself.
TEMPLE_RESPONSES: tuple[KeywordResponse, ...] = (
    KeywordResponse(
        "禮拜",
        "「日課在晨鐘之後與日落之前，都在講台前舉行，任何人都有座位。不必受洗"
        "，也不必報上身家，進門坐下就算參與。想聽講道，就留到鐘響；想單獨說話"
        "，光明聽得見，我也聽得見。」",
    ),
    KeywordResponse(
        "祝禱",
        "「祝禱、祝福，為遠行的人祈求平安，都在講台邊進行，不收分文。若身上沾"
        "了邪氣，可以用受洗聖水洗淨，聖水擺在聖所的櫃上，由執事經手。想正式入"
        "教的人，也可以在這裡向我請求入教儀式。」",
    ),
    KeywordResponse(
        "聖所",
        "「聖所就在這棟建築裡，左手邊，同一片屋頂、同一排窗。本會以性愛為修道"
        "之途，聖所公開服事，這件事在大陸上無人不知，和酒館供酒一樣平常。禮拜"
        "、聖所與商店是同一份信仰生活的三處櫃檯，你想問哪一處，我都照實回答。"
        "」",
    ),
    KeywordResponse(
        "商店",
        "「商店在裡廳，由聖所執事羅海西亞·芬威克看管。受洗聖水、禮儀器物與修"
        "道用的物件，都在她的櫃上。挑選物品請問她，祝禱的事再回來問我。」",
    ),
)

# 羅海西亞·芬威克 — the 聖所執事. Her remit is the sanctum's ministry
# arrangements and the shop that supplies it, and her voice is a friendly
# shopkeeper's: what is it for, who is it for, here is how to use it. The
# goods are the sanctum_wares bundle (the intimacy goods plus 受洗聖水); she
# names them plainly, because in this world they are ordinary merchandise.
# She buys back only what her own counter stocks.
SANCTUM_RESPONSES: tuple[KeywordResponse, ...] = (
    KeywordResponse(
        "賣什麼",
        "「架上分兩邊喔。戴在身上的有花蒂銀夾、暖蜜魔導珠、恆溫魔法卵、尖銳觸"
        "感之飾；貼身藏著的有恆振晶；拿來用的有催情浴鹽、女神之吻聖霧、情欲香"
        "爐、史萊姆潤滑凝膠、熱吻藥水，還有纏枝魔藤和微電跳蛋糖。受洗聖水也在"
        "這裡。看上哪樣，拿到櫃上來就好。」",
    ),
    KeywordResponse(
        "聖水",
        "「受洗聖水是主祭親自祝禱過的水，能洗淨身上沾的邪氣，用法寫在瓶標上喔"
        "。要的話，拿到櫃上來就好。」",
    ),
    KeywordResponse(
        "禮器",
        "「香爐、聖霧、祝禱掛飾這些，是禮儀正經用的東西，信眾買回家自己用，拿"
        "來送禮也很體面呢。用料寫在籤上，價錢看牌子。櫃上有的東西，用舊了洗乾"
        "淨拿來，我也收。」",
    ),
    KeywordResponse(
        "聖所事務",
        "「聖所的事呀，進門左轉就有修女接待。房間、時段、你想要什麼樣的服事，"
        "都當面講好，雙方都願意才開始。要祝禱就回大殿找艾莉安娜主祭，要買東西"
        "就留在我這兒。」",
    ),
)

# 古利安·鷹守 — the 貴族區衛所 captain, on duty and formal. The document's
# 守門衛兵隊長 belongs to a restriction the capital deliberately does not ship
# (a lock on an empty room is a wall, not a mystery), so his whole office is
# the open door: the quarter is walkable to anyone and there is nothing to
# petition for yet. He sends route questions to the south-gate captain and
# work-seekers to the adventurer guild's board; the watch posts no work.
NOBLE_WATCH_RESPONSES: tuple[KeywordResponse, ...] = (
    KeywordResponse(
        "貴族區",
        "「貴族區對所有人開放，衛所只巡街，不盤查來人。各府邸的門關著，那是各"
        "家自己的門；街道本身，任何人都可以走。請自便。」",
    ),
    KeywordResponse(
        "謁見",
        "「目前沒有任何謁見的安排，也沒有需要遞交的文書。沿著街走到盡頭就是王"
        "宮前庭，王宮的門開著，訪客可以自行進去。裡面很安靜，安靜到連我都覺得"
        "冷清。」",
    ),
    KeywordResponse(
        "衛所",
        "「本衛所負責三件事，巡邏的班次、防火的水源，以及各家報來的瑣事。下城"
        "的街道與城門歸南門的衛兵隊長托瓦德·鄧堡管，我們換班時會互通消息；這"
        "一區的街面，我可以回答。」",
    ),
    KeywordResponse(
        "委託",
        "「衛所不發委託，牆上也不貼告示，這句話我對每位訪客都說一遍。若想找事"
        "做，冒險者公會在中央廣場東邊，大廳裡有任務板。若有府邸私下託付差事，"
        "那是府裡的人與訪客之間的約定，與衛所無關。」",
    ),
)

# 伊沃·高丘 — the 校場 instructor, colloquial and blunt. The yard adds no
# mechanism: practice works wherever a person stands, and the yard is simply
# where the city comes to drill where the standard is visible. He promises
# no drill bonus, no sparring partner and no exam of his own; rank trials
# belong to the adventurer guild.
DRILL_YARD_RESPONSES: tuple[KeywordResponse, ...] = (
    KeywordResponse(
        "修煉",
        "「想練本事哪？場子隨你用，樁子隨你打，練不練在你啦。我這場子的好處就"
        "兩樣，打樁沒人嫌吵；旁邊有人在練，你看得到別人練到什麼程度。」",
    ),
    KeywordResponse(
        "考核",
        "「想升階哪？那是公會的事啦，考官會當面試你的本事，報名要去公會大廳。"
        "我這裡不代考，也不保證你過。底子練紮實了再去，比較不丟臉。」",
    ),
    KeywordResponse(
        "切磋",
        "「想找人對打？我這裡沒有陪練的人，我也不替你拉人。真要動手，城外多的"
        "是魔物，那可是會要命的事。這片場子的好處只有一樣，摔下去是軟土，不會"
        "摔在街石上啦。」",
    ),
    KeywordResponse(
        "教頭",
        "「教頭？我沒有什麼特別的訣竅好教，也不發證書啦。你會什麼、練到哪裡，"
        "你自己心裡有數。我能給的就這片場子跟一句話，每天都要練，站在場中羨慕"
        "樁子上的刀痕，一點用也沒有。」",
    ),
)

# 奧德溫·薩契 — the 王立魔法學院院長, formal and lecturing. The capital's
# lore-reveal table (docs/lore/settlement-locations.md §魔法學院與圖書館): he
# answers the rank ladder (every rung and its example spells) and the eight
# elements as subject matter, matching docs/lore/magic-system.md. His 拜師
# answer is the academy's refusal in his own words: no skill is granted by
# mentorship, skill comes from practice, and rank trials are the guild's.
ACADEMY_RESPONSES: tuple[KeywordResponse, ...] = (
    KeywordResponse(
        "魔法等級",
        "「魔法造詣分為五級，初級、中級、高級、超級、究極。初級能施展火球、水"
        "箭、風刃、治癒術、身體強化；中級多了火焰風暴、冰牆、飛行術；高級有熔"
        "岩術、暴風雪、高級治癒、統御術；超級是龍炎術、地震術、神聖光輝，人類"
        "能走到這一級的極少；究極則近乎傳說。學院的書庫就照這五級排書，你想從"
        "哪一級讀起都可以。」",
    ),
    KeywordResponse(
        "元素",
        "「元素共有八種，入門課的第一堂就會講。火，攻勢最猛；水，牽動魔力的潮"
        "汐；風，兼顧攻擊與身法；土，掌管地形與防護；雷，搶在對手之前出手；冰"
        "，讓對手動彈不得；光，治療與淨化；暗，削弱與侵蝕。課堂上背得再熟，也"
        "比不上自己親手練過的一道咒文。」",
    ),
    KeywordResponse(
        "親和",
        "「問得好，這個問題分兩層。第一層是元素，同一道法術，與你親和的元素學"
        "起來快一些，沒有親和的慢一些。第二層是種族，精靈天生親近魔法，學什麼"
        "都比人類快得多；人類各有偏好，得靠自己摸索。稟賦沒有辦法在學院裡教；"
        "學院能幫你認清自己該往哪條路走。」",
    ),
    KeywordResponse(
        "拜師",
        "「拜師？學院沒有拜師這條路。本事要靠自己日積月累練出來，劍術也好，咒"
        "文也好，都得花時間反覆練習；想知道自己練到什麼程度，可以去冒險者公會"
        "參加階級考核。學院願意給你一個學生的名分，但名分沒有辦法替你練。」",
    ),
)

# One entry per UPPER-terrace place that authors a dialogue_key, keyed
# exactly as the place row authors it: the 光明神殿's 主祭, the 聖所執事,
# and the noble watch, drill yard and academy attendants (altoria-sanctum /
# altoria-crown-and-watch / altoria-learning-and-exchange) — the keys
# travel in the rows, so the slice assembles into DIALOGUE_ROWS unchanged.
ROWS: tuple[tuple[str, DialogueDefinition], ...] = (
    (
        "altoria_temple",
        DialogueDefinition(
            greeting=(
                "講台邊的艾莉安娜·寒水主祭合上經冊，晨光從她背後的高窗落進大殿：「願"
                "平安與你同在，旅人。日課、祝禱，或是想問的事，都可以在這裡說。這座神"
                "殿同時是禮拜堂、聖所與聖所的商店，三處都敞開著，你想問哪一處，我都會"
                "回答。」"
            ),
            responses=TEMPLE_RESPONSES,
        ),
    ),
    (
        "altoria_sanctum",
        DialogueDefinition(
            greeting=(
                "裡廳櫃檯後的羅海西亞·芬威克執事把帳頁翻了個面，抬頭笑了笑：「歡迎喔"
                "！是自己用，還是要送人呢？聖水、禮器、貼身用的都有，價錢寫在櫃邊的牌"
                "子上，隨意挑。聖所那邊的安排，也可以問我。」"
            ),
            responses=SANCTUM_RESPONSES,
        ),
    ),
    (
        "altoria_noble_watch",
        DialogueDefinition(
            greeting=(
                "貴族區衛所的古利安·鷹守隊長從登記桌後抬起頭，推了推眼鏡：「訪客，貴"
                "族區不設關卡，進出無須登記。本衛所負責街面的巡守，若有需要詢問的事，"
                "請說。」"
            ),
            responses=NOBLE_WATCH_RESPONSES,
        ),
    ),
    (
        "altoria_drill_yard",
        DialogueDefinition(
            greeting=(
                "校場的伊沃·高丘從練習樁那頭走回來，小臂上還沾著土：「來看熱鬧，還是"
                "來練的啦？話說在前頭，我這裡沒有捷徑，只有這片土、那排樁子，還有幾句"
                "練法。」"
            ),
            responses=DRILL_YARD_RESPONSES,
        ),
    ),
    (
        "altoria_academy",
        DialogueDefinition(
            greeting=(
                "學院長廳的黑板前，奧德溫·薩契院長擦去一行算式，回頭看見你便放下粉筆"
                "：「歡迎。此刻沒有開課，但隨時可以提問。等級、元素、親和，你想從哪裡"
                "問起？學院傳授的是知識，捷徑這裡沒有。」"
            ),
            responses=ACADEMY_RESPONSES,
        ),
    ),
)
