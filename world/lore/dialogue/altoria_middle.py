"""聖潔王都 (capital_altoria) MIDDLE-terrace authored dialogue rows.

These rows moved verbatim from the former ``altoria.py`` so each terrace
slice is owned by one content change: the general store, forge, tailor,
jeweller, alchemist and merchant hall tables, keyed exactly as the
MIDDLE-terrace place rows in ``places_altoria_middle.py`` author them.

Guidance rides inside what the person behind the counter would actually
say — each shopkeeper answers about what THAT shop actually carries, in its
own voice, pointing the player at ``shop stock``, ``buy`` and ``sell``.

聖潔王都市集棚 (``altoria_market_stalls``) has no entry here: the
host-less place authors no dialogue_key, so it has nothing to key.

Four keyword answers at most: the dialogue panel ships
``DIALOGUE_MAX_CHOICES`` entries and silently drops the rest, so each row
here carries exactly four.
"""

from world.lore.dialogue.shape import DialogueDefinition, KeywordResponse

# 瑪爾特·金秤 — the general store. Her shelf is what a general store sells
# once the specialists have taken theirs: tools and raw materials. 受洗聖水
# left with altoria-sanctum, on its way to the counter the world document
# says it belongs to. A merchant who has been weighing copper since the
# guild economy landed, and who sends accessory hunters to the jeweller,
# potion buyers to the alchemist and sanctum-shopper pilgrims up the 聖階
# without missing a beat.
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
        "鍊金坊找希碧拉，都是老街坊。受洗聖水先前暫放我櫃上，如今歸位了——"
        "要上大神殿前，聖所自己開櫃了；淨化負面狀態那一回用得到，"
        "他們的櫃檯比我齊全。」",
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
# general store's shelf with her change; 受洗聖水 has since gone up the
# 聖階 to its own counter (altoria-sanctum), and she says so.
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
        "「受洗聖水不在我這兒——那是聖所的東西，如今聖所自己開櫃，"
        "上了大神殿前就買得到。我這裡賣的是調出來的藥：空瓶破瓶拿來我 `sell` 收，"
        "好料換新藥，進出都清爽。」",
    ),
)

# 尤斯汀·柯德溫 — the 商會會長. The document's 商會與貿易行 is the designated
# future source of escort commissions, and `guild request` already tells every
# registered adventurer that escort work is closed. He is the refusal made
# flesh: a guild master with a whole wall of route charts and not one posting
# on it. He speaks of caravans, roads and tariffs as substance — the trade of
# 東市 really is coordinated from his desk — and when asked for work he sends
# the enquirer honestly to the guild board, naming that the hall posts nothing
# because the work its name anticipates has no quest type behind it yet.
MERCHANT_HALL_RESPONSES: tuple[KeywordResponse, ...] = (
    KeywordResponse(
        "商隊",
        "「本季出城的隊子都擱我牆上那張程表裡：東市上船的玻璃、糧食、布疋，"
        "走哪條官道、幾時回門，寫得清楚。你要搭商隊的行腳捎貨，"
        "認的是車頭本人，我這裡只登帳、不攬事——公所替行會間調利益，"
        "不替過路人保貨。」",
    ),
    KeywordResponse(
        "商路",
        "「東門出去是官道南段，東市本就是老城牆邊長起來的貨棧街。"
        "往來的大宗就那幾樣：糧、玻璃器、布疋、礦材；工匠巷打的鐵器"
        "走市場街出城，鍊金坊的藥走東市上船。你要問哪條路通哪裡，"
        "喊 `前往` 加街名，路自會領你過去；"
        "我這牆上掛的是誰家幾時走哪條。」",
    ),
    KeywordResponse(
        "委託",
        "「接活？我公所牆上無單、門邊無榜，護衛商隊那一類事如今根本無處接——"
        "不是端著架子不給你，是那樣的活路目前還立不起來，"
        "你問 `guild request` 也問得一樣：公會明講護衛未開。"
        "要尋事做，往公會大廳的板子上找；這裡只有帳，沒有活。」",
    ),
    KeywordResponse(
        "會務",
        "「公所的會務就三樣：行會間的利益調停、關稅章程的評議、"
        "季底各家欠帳的清算。你要入行會，帶引薦人上門當面談；"
        "要問稅則，窗下那張桌自己看，抄一份不攔。"
        "其餘的——我這裡管的是人跟人簽字的事，別的管不著。」",
    ),
)

# One entry per MIDDLE-terrace place that authors a dialogue_key, keyed
# exactly as the place row authors it: the general store, forge, tailor,
# jeweller and alchemist merchants, plus the merchant hall attendant
# (altoria-learning-and-exchange) — the keys travel in the rows, so the
# slice assembles into DIALOGUE_ROWS unchanged.
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
    (
        "altoria_merchant_hall",
        DialogueDefinition(
            greeting=(
                "商會公所的尤斯汀·柯德溫會長從關稅桌後抬起眼，把你當貨單估了一遍："
                "「東市往來的都歸這屋調度。問商隊、問商路、問規矩，我答；"
                "有一樣你開口也是白問，我先替你省了——我牆上沒有單，"
                "公所不發委託。」"
            ),
            responses=MERCHANT_HALL_RESPONSES,
        ),
    ),
)
