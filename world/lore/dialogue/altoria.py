"""聖潔王都 (capital_altoria) authored dialogue rows.

Each merchant place's ``dialogue_key`` must ship its table in the same change
(load-time resolution rejects an authored host that cannot speak): the
general store, forge, eatery and tailor rows arrive with the
merchant-dialogue change, and every later capital content change appends its
rows to ``ROWS`` here.

The voice rules the guild clerk's row established bind these tables too:

- Four keyword answers at most. The dialogue panel ships
  ``DIALOGUE_MAX_CHOICES`` entries and silently drops the rest, so a fifth
  keyword is a keyword the player can never press. Each row carries exactly
  four.
- Guidance rides inside what the person behind the counter would actually
  say. Each shopkeeper answers about what THAT shop actually carries —
  the goods of its own assortment, in its own voice — and points the player
  at ``shop stock``, ``buy`` and ``sell``. No shared template with the nouns
  swapped: four shopkeepers, four distinct counters.
"""

from world.lore.dialogue.shape import DialogueDefinition, KeywordResponse

# 瑪爾特·金秤 — the general store. Her shelf is what a general store sells
# once the specialists have taken theirs: tools and raw materials, with 受洗
# 聖水 still sitting there until the sanctuary change moves it
# (altoria-adornments-and-remedies). A merchant who has been weighing copper
# since the guild economy landed, and who sends accessory hunters to the
# jeweller and potion buyers to the alchemist without missing a beat.
GENERAL_STORE_RESPONSES: tuple[KeywordResponse, ...] = (
    KeywordResponse(
        "賣什麼",
        "「粗鐵礦、魔獸結晶、附魔羅盤、迷宮探照符——出城要的行頭和要賣的"
        "素材，我這裡都有。要買，`shop stock` 先看看我架上剩多少，決定了喊 "
        "`buy` 加品名；手上多了哥布林耳朵、史萊姆黏液這類貨，也儘管擱上櫃檯，"
        "我喊 `sell` 收。」",
    ),
    KeywordResponse(
        "材料",
        "「礦石、鱗片、尖牙、結晶——地城裡揀回來的，我收得最勤；要買新的，"
        "止血藥草、永夜碎片、魔導晶核也都擱架上。兩頭都走同一個規矩："
        "`shop stock` 報實數，買喊 `buy`，賣喊 `sell`，銅幣當場點清。」",
    ),
    KeywordResponse(
        "行頭",
        "「魔法燈、附魔羅盤、通訊法螺、露營魔導具——少了這些，地城裡就是條命。"
        "想挑就 `shop stock`，看中了 `buy`，我這裡不講價，講的是信得過。」",
    ),
    KeywordResponse(
        "飾品藥水",
        "「那兩樣我早不做了——飾品往市場街口的首飾坊找艾蓮娜，藥劑往東市的"
        "鍊金坊找希碧拉，都是老街坊。我櫃上留的只有受洗聖水，"
        "淨化負面狀態那一回用得到；要就 `shop stock` 看看，`buy` 提貨。」",
    ),
)

# 維爾登·黑潭 — the forge. His voice is the anvil: short, practical, proud of
# the blade. common_arms is his axis — plain blades up to the knight blade.
FORGE_RESPONSES: tuple[KeywordResponse, ...] = (
    KeywordResponse(
        "兵器",
        "「普通劍、鐵短刀、擲斧、長弓，連術師的法杖都有，牆上掛的都是打得過的貨。"
        "要幾時看好，"
        "`shop stock` 報數量；定了 `buy` 加品名，我從架上取，你從袋裡掏銅。」",
    ),
    KeywordResponse(
        "好貨",
        "「最鋒的我掛最裡頭——騎士制式長劍，鍛打的工錢就在刃口上。"
        "再上頭那柄魔導長劍，價錢漂亮，錢包也得漂亮。"
        "想看清單喊 `shop stock`，我念得比你讀得還熟。」",
    ),
    KeywordResponse(
        "賣鐵",
        "「礦石、廢刃、拆下來的破甲——往我這邊擱。`sell` 加品名，"
        "我掂一掂報個數，銅幣當場點清。回爐的東西我不殺你的價，"
        "爐子吃料，我吃工。」",
    ),
    KeywordResponse(
        "保養",
        "「刃口鈍了就回來，別拿它去砍石頭。護甲破了也別硬穿，"
        "修繕的錢省下來，遲早要連本帶利還給鐵鎚。買新刃先 `shop stock`，"
        "看準了 `buy`，舊的擱櫃檯上 `sell`，一進一出最划算。」",
    ),
)

# 西格瑪·庫柏 — the eatery. Barrel-maker's family trade turned kitchen;
# he talks food the way coopers talk casks: warm and plain. staple_meals.
EATERY_RESPONSES: tuple[KeywordResponse, ...] = (
    KeywordResponse(
        "餐點",
        "「熱食、黑麥硬麵包、行軍口糧，後頭灶上一直溫著。`shop stock` "
        "看得見還剩幾份，餓了就 `buy` 加品名，端走就吃。」",
    ),
    KeywordResponse(
        "招牌",
        "「濃湯是招牌，颳風下雨的天，一碗下肚半條命回來。甜食櫃檯邊有，"
        "精靈那邊的蜜漬花蕊我也進了一小罐——那是稀罕物，賣完算完。"
        "清單 `shop stock`，要了喊 `buy`。」",
    ),
    KeywordResponse(
        "乾糧",
        "「要出城進地城，帶足攜行口糧和燻獸肉乾。餓到一半才想起吃，"
        "就晚了。`shop stock` 看看存量，`buy` 多屯幾份，"
        "銅幣花在肚裡總比花在醫館便宜。」",
    ),
    KeywordResponse(
        "收食",
        "「獵得的好肉好料，拿來我收，`sell` 加品名折價給你。"
        "講好了再提現成的：飯食過櫃不候，入口的東西我只要乾淨貨——"
        "廚子的規矩，也是你我的規矩。」",
    ),
)

# 妮絲塔·狐溪 — the tailor. Fox fur and streamside fulling in her surname;
# she speaks of cloth by its hand-feel. common_outfits: leathers, robes,
# mail, plate, and the finer vestments.
TAILOR_RESPONSES: tuple[KeywordResponse, ...] = (
    KeywordResponse(
        "衣甲",
        "「皮甲穩當，法袍飄逸，鎖子甲沉實——穿在身上的，我這裡都有。"
        "`shop stock` 報的是實數，看中哪件 `buy` 加品名，試穿不收費。」",
    ),
    KeywordResponse(
        "旅裝",
        "「出遠門的人講究輕便合身。皮甲、術師長袍，我一針一線都盯過。"
        "銅幣不多就先從皮件起；`shop stock` 裡挑一件合身的，"
        "勝過三件將就的。」",
    ),
    KeywordResponse(
        "禮服",
        "「修女聖袍、聖女聖袍，北大道那頭的訂貨我接得下，現貨也有幾件。"
        "貴不貴？`shop stock` 一報你就知道了——好布好工，瞞不了人。」",
    ),
    KeywordResponse(
        "收衣",
        "「穿膩的、不合身的小件，洗淨了拿來，`sell` 加品名我收。"
        "破成布條的就免了——布有布的體面。舊衣我翻新再賣，"
        "新主穿舊衣，總比新衣壓箱底體面。」",
    ),
)

# 艾蓮娜·鴉丘 — the jeweller. Crow-quill polish and an eye for settings: she
# answers about gemwork and settings, and names the pieces off her own case
# (capital_adornments). altoria-adornments-and-remedies took these eleven
# accessory-slot goods off the general store's shelf, verbatim in price.
JEWELLER_RESPONSES: tuple[KeywordResponse, ...] = (
    KeywordResponse(
        "飾品",
        "「銀髮簪、狼牙項鍊、朝聖者銅符——櫃檯後這排玻璃櫃，全是能掛在身上的。"
        "飾品槽有件數上限，挑你要的那幾件。`shop stock` 報的是現貨，"
        "看中哪件喊 `buy` 加品名。」",
    ),
    KeywordResponse(
        "鑲工",
        "「鑲工好壞，看爪不看光。淨化吊墜、無懼胸針是我手上最講工的兩件，"
        "光輝聖徽的徽面則是一整塊料雕出來的。細節你來櫃前我攤開給你瞧，"
        "價錢 `shop stock` 一報瞞不了人。」",
    ),
    KeywordResponse(
        "奇物",
        "「要說佩著有用的——儲物袋肚裡另有一層空間，滑翔斗篷能托住墜落的人。"
        "這兩樣在我櫃上壓箱底：不便宜，關鍵時刻值回銅幣。"
        "清單 `shop stock`，要了喊 `buy`。」",
    ),
    KeywordResponse(
        "收飾",
        "「舊飾件洗淨了拿來，`sell` 加品名我估價；缺了爪、斷了鏈的要先說清，"
        "熔金重鑄是另一筆工錢。藥師珠串、迷情絲頸環這類有來路的，"
        "認得下家的我不殺你的價。」",
    ),
)

# 希碧拉·灰沼 — the alchemist. Her surname is a peat-bog still, and her
# voice is measure-and-label: what each remedy does, in plain use-terms
# (capital_remedies). The six drinkable and applied remedies came off the
# general store's shelf with this change; 受洗聖水 stays next door until the
# sanctuary lands, and she says so.
ALCHEMIST_RESPONSES: tuple[KeywordResponse, ...] = (
    KeywordResponse(
        "藥劑",
        "「治療藥水壓小傷，強效治療藥水拉回重傷，魔力藥水補的是施法者的氣。"
        "`shop stock` 看得見還剩幾瓶，要哪瓶喊 `buy` 加品名。」",
    ),
    KeywordResponse(
        "外敷",
        "「獸王國藥草膏抹在腫起處，王國礦工提神湯一口下去瞌睡全消——"
        "這兩樣不算藥水，算備在行囊裡的救急。數量 `shop stock` 報得準，"
        "`buy` 了就裝進你的袋子。」",
    ),
    KeywordResponse(
        "特殊",
        "「迷情藥這種東西，我賣之前會先問你一句想清楚了沒有。"
        "Effects 全寫在瓶標上，不藏。想先看單子就 `shop stock`，"
        "決定了再喊 `buy`。」",
    ),
    KeywordResponse(
        "聖水",
        "「受洗聖水不在我這兒——那是聖所的東西，如今暫放雜貨店櫃檯，"
        "等聖所開張就歸位。我這裡賣的是調出來的藥：空瓶破瓶拿來我 `sell` 收，"
        "好料換新藥，進出都清爽。」",
    ),
)

# One entry per capital merchant place, keyed exactly as the place rows author
# it (the keys travel in the rows; the slice assembles into DIALOGUE_ROWS
# unchanged).
ROWS: tuple[tuple[str, DialogueDefinition], ...] = (
    (
        "altoria_general_store",
        DialogueDefinition(
            greeting=(
                "櫃檯後的瑪爾特·金秤從帳簿抬起眼，秤桿還捏在手裡："
                "「要什麼直說。材料、行頭、雜七雜八，雜貨店雜就雜在"
                "該有的都有；飾品請走首飾坊，藥劑請走鍊金坊，我這裡不搶"
                "街坊的生意。想先看清楚，`shop stock` 我報實數；"
                "決定了 `buy`，地城裡揀回來的想脫手，擱櫃檯上 `sell`。"
                "說罷，她又低頭撥她的算盤。」"
            ),
            responses=GENERAL_STORE_RESPONSES,
        ),
    ),
    (
        "altoria_forge",
        DialogueDefinition(
            greeting=(
                "鍛造鋪的維爾登·黑潭把鉗子裡的刃翻了個面，火星濺了一地："
                "「買兵刃還是賣廢鐵？牆上掛的都是打得過的貨。"
                "清單 `shop stock`，定了 `buy`；礦石破刃要脫手，"
                "櫃邊擱下喊 `sell`。問完邊站著，別擋爐口。」"
            ),
            responses=FORGE_RESPONSES,
        ),
    ),
    (
        "altoria_eatery",
        DialogueDefinition(
            greeting=(
                "餐館的老闆西格瑪·庫柏從灶後探出半個身子，圍裙上還沾著麵粉："
                "「餓了吧？熱食、乾糧、湯品，灶上都溫著。"
                "`shop stock` 還剩幾份瞞不了你，要就 `buy`；"
                "獵得的好料想換錢，帶來我 `sell` 收。先坐，先坐。」"
            ),
            responses=EATERY_RESPONSES,
        ),
    ),
    (
        "altoria_tailor",
        DialogueDefinition(
            greeting=(
                "裁縫坊的妮絲塔·狐溪捏著一段染好的細布迎出來，針腳在她指間翻飛："
                "「看看合不合身再說——皮甲法袍、鎖甲禮服，現貨訂貨都接得成。"
                "實數在 `shop stock` 上，看中 `buy`；穿膩的小件洗淨帶來，"
                "`sell` 我收。來，手伸出來我比一比。」"
            ),
            responses=TAILOR_RESPONSES,
        ),
    ),
    (
        "altoria_jeweller",
        DialogueDefinition(
            greeting=(
                "首飾坊的艾蓮娜·鴉丘放下拋光布，把玻璃櫃裡那盞小燈撥亮了些："
                "「眼睛先挑，錢包隨後——髮簪項鍊、吊墜胸針，能佩的都在這櫃裡。"
                "現貨 `shop stock` 報得清楚，看中喊 `buy`；"
                "家傳的舊飾件要估要賣，戴進來，`sell` 我收。」"
            ),
            responses=JEWELLER_RESPONSES,
        ),
    ),
    (
        "altoria_alchemist",
        DialogueDefinition(
            greeting=(
                "鍊金坊的希碧拉·灰沼從一整牆瓶罐之間探出半張臉，指尖夾著一張瓶標："
                "「說症狀還是說藥名，兩邊我都聽得懂。藥水、提神的、外敷的都有現貨，"
                "`shop stock` 報剩餘，要了 `buy`；空瓶好料想換錢，擱櫃上 `sell`。"
                "問藥效可以，別碰櫃檯上那排紅標的。」"
            ),
            responses=ALCHEMIST_RESPONSES,
        ),
    ),
)
