"""聖潔王都 (capital_altoria) UPPER-terrace authored dialogue rows.

These rows moved verbatim from the former ``altoria.py`` so each terrace
slice is owned by one content change: the temple, sanctum, noble watch,
drill yard and academy tables, keyed exactly as the UPPER-terrace place
rows in ``places_altoria_upper.py`` author them.

Four keyword answers at most: the dialogue panel ships
``DIALOGUE_MAX_CHOICES`` entries and silently drops the rest, so each row
here carries exactly four.
"""

from world.lore.dialogue.shape import DialogueDefinition, KeywordResponse

# 艾莉安娜·寒水 — the 主祭 of the 光明神殿. Her counter is the dais: worship,
# blessing, and straight answers about what this building is. The source
# document's register binds her table (docs/lore/settlement-locations.md
# §神殿／聖所): 聖所、神殿、教堂、禮拜堂 are one building, its ministry is
# 社會常識, and a priest who speaks of it coyly is the misreading the
# document names. She answers a question about the sanctum the way an
# innkeeper answers a question about rooms — and she trades nothing, so her
# table ships no trade verbs: the shop counter belongs to the 執事.
TEMPLE_RESPONSES: tuple[KeywordResponse, ...] = (
    KeywordResponse(
        "禮拜",
        "「日課在晨鐘後與日落前，都在講台前，誰來都有位子——不洗禮、不查身家，"
        "進門坐著便是參與。想聽講道就留到鐘響，想單獨說說話，聖光聽得見，"
        "我也聽得見。」",
    ),
    KeywordResponse(
        "祝禱",
        "「祝禱、祝福、為遠行的人祈風向，都在講台邊進行，不收銅板。"
        "要淨化負面狀態那一類，用的是受洗聖水——那是聖所櫃上的貨，"
        "你從講台左手邊走過去就是；我這裡管祝禱，執事櫃上管提貨。」",
    ),
    KeywordResponse(
        "聖所",
        "「就在這棟建築裡，左手邊，同一片屋頂同一排窗。本會以性愛為修道之途，"
        "聖所公開經營，這是舉世皆知的規矩，跟酒館賣酒一樣沒什麼瞞人的。"
        "禮拜、聖所、附設商店是同一信仰生活的三個櫃檯——你想問哪一邊，"
        "我就答哪一邊，沒有不能問的。」",
    ),
    KeywordResponse(
        "商店",
        "「聖所附設的櫃檯在裡廳，羅海西亞·芬威克執事坐櫃——聖水、禮器、"
        "修道用的物件都在她架上。買賣的事我外行，你問她，她報數不清場；"
        "祝禱的事她外行，你回來問我。」",
    ),
)

# 羅海西亞·芬威克 — the 聖所執事. Her remit is the sanctum's administered
# ministry and the shop that supplies it, and her voice is a shopkeeper's
# from the first syllable: measure, stock, price. The goods are the twelve
# intimacy tools plus 受洗聖水 (sanctum_wares); she names them the way the
# jeweller names settings, because in this world that is exactly what they
# are — merchandise. Nothing in her table whispers.
SANCTUM_RESPONSES: tuple[KeywordResponse, ...] = (
    KeywordResponse(
        "賣什麼",
        "「禮儀與貼身兩類都有現貨：花蒂銀夾、暖蜜魔導珠、恆溫魔法卵這些配戴的，"
        "催情浴鹽、女神之吻聖霧、情欲香爐這些用的，外加受洗聖水。"
        "清單 `shop stock` 報實數，看中 `buy` 加品名；跟外頭櫃檯一個規矩，不另立。」",
    ),
    KeywordResponse(
        "聖水",
        "「受洗聖水如今在我櫃上——先前寄放雜貨店，是聖所沒開張的時候。"
        "移除身上負面狀態，效果寫在瓶標；`shop stock` 看剩幾瓶，要就 `buy`。」",
    ),
    KeywordResponse(
        "禮器",
        "「香爐、聖霧、祝禱掛飾這一路，是禮儀正經用的物件，信眾買來自用、"
        "送禮都有。料工寫在籤上，价钱 `shop stock` 一報瞞不了人；"
        "舊禮器洗淨要換錢，擱櫃檯上 `sell` 我估。」",
    ),
    KeywordResponse(
        "聖所事務",
        "「聖所的事，你進門左轉自然有人接——床位、時辰、願不願意，都當面問清，"
        "這裡不做猜的地方。要祝禱就回大殿找艾莉安娜主祭；要買東西就現在站著，"
        "`shop stock`、`buy`、`sell`，我櫃上照規矩走。」",
    ),
)

# 古利安·鷹守 — the 貴族區衛所 captain. The document's 守門衛兵隊長 belongs
# to a 限制進入 this change deliberately does not ship (design: a lock on an
# empty room is a wall, not a mystery), so his table's whole office is the
# open door: the quarter is walkable to anyone, and there is simply nothing
# to petition for yet. He says so plainly — no gate to impress a player
# with, no invented audience to tease them toward.
NOBLE_WATCH_RESPONSES: tuple[KeywordResponse, ...] = (
    KeywordResponse(
        "貴族區",
        "「要進貴族區？請便，沒有要請的意思——就是請便。這一區不設關，"
        "我手底下的人查巡，不查客。各府邸的門關著，那是各家自己的門，"
        "你沿街上走，沒有人攔你。」"
    ),
    KeywordResponse(
        "謁見",
        "「要遞狀？沒有狀可遞。這區裡如今沒有當值的門，也沒有開著的案——"
        "不是我不給你遞，是這府第的戲還沒開鑼。真要說有什麼，"
        "街走到頭是王宮前庭，你想進去自己走進去，裡頭有座空著的王。」"
    ),
    KeywordResponse(
        "衛所",
        "「我這衛所管的是這一區的門前清靜：巡邏班次、防火的水、"
        "各家報上來的雜事。你要問哪條街通哪裡，喊 `地圖`，圖是全城的；"
        "要問我，我答街面上這些。別的沒有，不是隱瞞，是真沒有。」"
    ),
    KeywordResponse(
        "委託",
        "「官面上不發委託，衛所牆上不掛單，這話我對每個進門的人都講一遍。"
        "你要尋事做，公會板在大道那頭；要替哪家府邸跑腿，"
        "那得是府裡人私下找你——總之都不歸我掛牌。」"
    ),
)

# 伊沃·高丘 — the 校場 instructor. His value is the innkeeper's office in
# yard clothes (altoria-crown-and-watch design): the dialogue is where a
# player learns that `rest` plus `practice` is how proficiency is trained and
# that `guild exam` is what grades it. The commands work wherever the player
# stands — he says so himself; the yard is where the city comes to do them
# where the standard is visible. He promises no drill bonus the change does
# not ship, and no sparring service either: `engage` fights a hostile monster
# wherever one stands (post-implementation review caught the shipped draft
# advertising a sparring partner the room does not have), so his table names
# the commands honestly and calls the yard dirt, not an opponent.
DRILL_YARD_RESPONSES: tuple[KeywordResponse, ...] = (
    KeywordResponse(
        "修煉",
        "「練熟練度，靠的不是這片土，是你自己：`rest` 加時數、掛一句 "
        "`practice` 加技能名，整小時結算。這話在哪條街講都一樣，"
        "我這場裡的好處只有兩樣——柱子由你打，沒人嫌吵；"
        "看得見別人怎麼練。要練就現在開始，汗是你自己的。」"
    ),
    KeywordResponse(
        "考核",
        "「問升階？公會的 `guild exam` 考的是你身上那些練習換來的東西，"
        "考場掛在哪條街都行，報名去公會大廳。我這裡不代考，"
        "也不保過——先練夠時數再報名，比較不丟人。」"
    ),
    KeywordResponse(
        "切磋",
        "「打打殺殺不歸這場：`engage` 開的是真生死，對的是街面上"
        "真出沒的魔物，我這場裡沒有陪練的，也不替你拉人。"
        "`combat forfeit` 認輸、`combat actions` 看手頭使得出什麼，"
        "這些指令哪裡都使得。這片土的好處只有一樣——摔的是軟土，"
        "不是街石。」"
    ),
    KeywordResponse(
        "教頭",
        "「我這教頭不傳秘技，也不發證書。會什麼、練到哪裡，"
        "你自己的帳上都有。我能給的是這片場子和一句話：`rest` 掛 `practice`，"
        "整小時地練，比站在場中羨慕柱子上的痕有用。」"
    ),
)

# 奧德溫·薩契 — the 王立魔法學院院長. The capital's one lore-reveal table
# (docs/lore/settlement-locations.md line 453 names the academy as the
# natural reveal scene for the 「魔法等級」 and 「元素」 codex categories,
# triggered by `talk`): he answers the rank ladder and the element roster as
# subject matter rather than as orientation, because the academy has no
# command to teach — 「拜師習得新技能」 stays 〔提案〕 at line 454, and his
# 拜師 keyword is the change's first refusal spoken in his own voice: no
# skill is granted by mentorship, proficiency accumulates on the lineage
# tree, and the title is narrative framing.
ACADEMY_RESPONSES: tuple[KeywordResponse, ...] = (
    KeywordResponse(
        "魔法等級",
        "「魔法的等級梯子有五級：初級、中級、高級、超級、究極，量的是造詣的"
        "深淺。初級使得出火球、水箭、風刃、治癒術、身體強化；中級添了火焰風暴、冰牆、"
        "飛行術；高級有熔岩術、暴風雪、高級治癒、統御術；超級是龍炎術、"
        "地震術、神聖光輝這一路，人類踏得到的寥寥無幾；究極則近乎傳說。"
        "知識圖鑑『魔法等級』一類寫的就是這條梯子，喊 `lore` 就翻得著你已識的。"
        "至於學徒、術師那些位階稱號——那是法術身價的資料標籤，不是你的等級，"
        "學院兩樣都教，從不混著教。」",
    ),
    KeywordResponse(
        "元素",
        "「元素共八個，入門課第一堂就報這八個名字：火，攻勢最強；水，治癒與守；"
        "風，速與範圍；土，防守與控場；雷，高速打擊；冰，控制兼攻伐；"
        "光，治癒與淨化；暗，詛咒與削弱。知識圖鑑『元素』一類寫的就是這八個，"
        "你已識得的，喊 `lore` 就翻得著。課室裡背得再熟，"
        "也換不了你自己手上練過的那幾層。」",
    ),
    KeywordResponse(
        "親和",
        "「親和管的是天生那頭：同一名法術，親和的屬性練來快些，無親和的慢些，"
        "倍率不過一點一與零點九之別。精靈天賦廣，樣樣都快；轉生者天賦深，"
        "只快在指名的那一條路上。稟賦是學院教不出來的東西——"
        "學院能教的，是讓你認清自己該走哪條路。」",
    ),
    KeywordResponse(
        "拜師",
        "「拜師？我這裡沒有『拜師』這道門。技能不從師門領，從系譜樹上練："
        "`rest` 掛一句 `practice` 加技能名，整小時結算熟練度；要考級，"
        "往公會 `guild exam` 報名。師徒名分，學院願意給你，"
        "但那是一段名分，不是捷徑。真開了『拜師即得技能』的門，"
        "這院子百年的練法才算白教。」",
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
                "講台邊的艾莉安娜·寒水主祭合上經册，晨光從她背後的高窗落進大殿："
                "「願平安與你同進這門。日課、祝禱、想問的事，都可以在這裡說。"
                "這棟屋頂下有三個櫃檯——禮拜、聖所、還有助理的商店——"
                "都是明路，你想問哪邊，我答哪邊。」"
            ),
            responses=TEMPLE_RESPONSES,
        ),
    ),
    (
        "altoria_sanctum",
        DialogueDefinition(
            greeting=(
                "裡廳櫃檯後的羅海西亞·芬威克執事把帳頁翻了個面，算盤撥得比嘴快："
                "「來對地方了。聖水、禮器、貼身用的，架上都有現貨，"
                "`shop stock` 報剩餘，看中 `buy`，舊件擱櫃上 `sell`；"
                "聖所的接送安排也在這櫃上問。要祝禱就回大殿找主祭，"
                "各走各的櫃檯，都不打聽。」"
            ),
            responses=SANCTUM_RESPONSES,
        ),
    ),
    (
        "altoria_noble_watch",
        DialogueDefinition(
            greeting=(
                "貴族區衛所的古利安·鷹守抬起下巴看了看你，沒有伸手攔："
                "「這一區不設關，進出請便。我守的是街面清靜，不是門檻。"
                "想問事就問，問不出什麼也別見怪——這一區如今就是沒有事。」"
            ),
            responses=NOBLE_WATCH_RESPONSES,
        ),
    ),
    (
        "altoria_drill_yard",
        DialogueDefinition(
            greeting=(
                "校場的伊沃·高丘從排柱那頭走回來，小臂上還沾著場裡的土："
                "「來看熱鬧還是來練？說在前頭：我這裡沒有秘傳，也沒有捷徑——"
                "只有這片土、那排柱子，還有跟你說清楚怎麼練的幾句話。」"
            ),
            responses=DRILL_YARD_RESPONSES,
        ),
    ),
    (
        "altoria_academy",
        DialogueDefinition(
            greeting=(
                "王立魔法學院的奧德溫·薩契院長從示範坪那頭踱回來，袍袖還沾著"
                "粉筆灰：「來聽課的？課此刻沒有，問答隨時。我這學院不傳秘技、"
                "不授捷徑——你問位階、問元素、問親和，我答得傾囊；"
                "問近路，那我勸你往校場走。」"
            ),
            responses=ACADEMY_RESPONSES,
        ),
    ),
)
