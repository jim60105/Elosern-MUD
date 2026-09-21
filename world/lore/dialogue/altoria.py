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

# 瑪爾特·金秤 — the general store. Her shelf is the sundries axis: potions and
# accessories up front, materials and curious tools stacked behind. A merchant
# who has been weighing copper since the guild economy landed.
GENERAL_STORE_RESPONSES: tuple[KeywordResponse, ...] = (
    KeywordResponse(
        "賣什麼",
        "「藥水、護身符、材料、行李袋——雜貨店雜就雜在該有的都有。"
        "要買，`shop stock` 先看看我架上剩多少，決定了喊 `buy` 加品名；"
        "手上多了賣相好的貨，也儘管擱上櫃檯，我喊 `sell` 收。」",
    ),
    KeywordResponse(
        "藥水",
        "「小傷小痛，普通藥水壓一壓就過去了；真要進地城，"
        "大瓶的我擱在櫃檯後頭第二層，銅幣夠就來一瓶。"
        "數量我隨時報得準：`shop stock`，報完你喊 `buy` 就能提貨。」",
    ),
    KeywordResponse(
        "收貨",
        "「地城裡揀回來的東西？擺上櫃檯我估個價，`sell` 加品名就成交。"
        "材料類我收得最勤——牙啊鱗啊晶體啊，堆在倉裡也是堆，"
        "折成銅幣總比生鏽好。」",
    ),
    KeywordResponse(
        "行頭",
        "「錢袋、燈、羅盤這類零碎，我櫃上從不缺。別小看小東西——"
        "少了條繩子，地城裡就是條命。想挑就 `shop stock`，"
        "看中了 `buy`，我這裡不講價，講的是信得過。」",
    ),
)

# 維爾登·黑潭 — the forge. His voice is the anvil: short, practical, proud of
# the blade. common_arms is his axis — plain blades up to the knight blade.
FORGE_RESPONSES: tuple[KeywordResponse, ...] = (
    KeywordResponse(
        "兵器",
        "「刀、匕首、斧、長弓，牆上掛的都是打得過的貨。要幾時看好，"
        "`shop stock` 報數量；定了 `buy` 加品名，我從架上取，你從袋裡掏銅。」",
    ),
    KeywordResponse(
        "好貨",
        "「最鋒的我掛最裡頭——騎士用的那柄，鍛打的工錢就在刃口上。"
        "再上頭還有一柄見識品，價錢漂亮，錢包也得漂亮。"
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
        "看准了 `buy`，舊的擱櫃檯上 `sell`，一進一出最划算。」",
    ),
)

# 西格瑪·庫柏 — the eatery. Barrel-maker's family trade turned kitchen;
# he talks food the way coopers talk casks: warm and plain. staple_meals.
EATERY_RESPONSES: tuple[KeywordResponse, ...] = (
    KeywordResponse(
        "餐點",
        "「熱食、黑餅乾、行軍糧，後頭灶上一直溫著。`shop stock` "
        "看得見還剩幾份，餓了就 `buy` 加品名，端走就吃。」",
    ),
    KeywordResponse(
        "招牌",
        "「湯品是招牌，颳風下雨的天，一碗下肚半條命回來。甜食櫃檯邊有，"
        "精靈那邊的蜜漬花蕊我也進了一小罐——那是稀罕物，賣完算完。"
        "清單 `shop stock`，要了喊 `buy`。」",
    ),
    KeywordResponse(
        "乾糧",
        "「要出城進地城，帶足行軍糧和煙肉乾。餓到一半才想起吃，"
        "就晚了。`shop stock` 看看存量，`buy` 多屯幾份，"
        "銅幣花在肚裡總比花在醫館便宜。」",
    ),
    KeywordResponse(
        "收食",
        "「獵得的好肉好料，拿來我收，`sell` 加品名折價給你。"
        "講好了再提現成的：飯食過櫃不候，入口的東西我只要乾淨貨——"
        "厨子的規矩，也是你我的規矩。」",
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
        "「出遠門的人講究輕便合身。斗篷、軟甲、襯袍，我一針一線都盯過。"
        "銅幣不多就先從皮件起；`shop stock` 裡挑一件合身的，"
        "勝過三件將就的。」",
    ),
    KeywordResponse(
        "禮服",
        "「祭服、禮袍、刺繡首飾物件，北大道那頭的訂貨我接得下，現貨也有幾件。"
        "貴不貴？`shop stock` 一報你就知道了——好布好工，瞞不了人。」",
    ),
    KeywordResponse(
        "收衣",
        "「穿膩的、不合身的小件，洗淨了拿來，`sell` 加品名我收。"
        "破成布條的就免了——布有布的體面。舊衣我翻新再賣，"
        "新主穿舊衣，總比新衣壓箱底體面。」",
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
                "「要什麼直說。藥水、護身符、材料、行頭，雜貨店雜就雜在"
                "該有的都有。想先看清楚，`shop stock` 我報實數；"
                "決定了 `buy`，手上有想脫手的，擱櫃檯上 `sell`。"
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
)
