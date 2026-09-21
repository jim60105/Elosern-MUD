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
- The hospitality tables (altoria-hospitality) belong to ``attendant`` hosts
  who sell nothing, so they ship no trade verb at all: the innkeeper's
  greeting names ``rest``/``sleep``/``practice``, the tavern keeper's names
  ``talk``/``invite``, and the bathhouse keeper's explains the separated
  sides — the commands each location exists to host, taught by the person
  standing in it. None of them quotes a price or promises an unimplemented
  effect (lodging fees, drink effects and bathing mechanics stay 〔提案〕).
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

# 蘿溫·古橡 — the 醉月酒館. The lane's information room: the document's
# designated place for 招募同伴 and 打聽情報, so her table names the commands
# that already work here (`talk` with anyone in the room, `invite` to the
# party) and sells nothing — the cups are scenery: no drink does anything,
# no gamble pays out (docs/lore/settlement-locations.md line 285 keeps both
# 〔提案〕). Her voice is a hostess's: warm, ears open, mouth shut.
# Post-implementation review cut the promises this change does not ship:
# the synchronised tavern holds only plain-NPC hosts (invite is reserved
# for recruitable travellers met out in the world, never the people behind
# this counter), and no authored row auto-delivers rumours or commissions —
# information-gathering here is the player opening their mouth, `talk`.
TAVERN_RESPONSES: tuple[KeywordResponse, ...] = (
    KeywordResponse(
        "傳聞",
        "「我這店裡最不缺的就是話。你要打聽什麼，開口找人問——"
        "店裡誰都能 `talk`，問得投緣，人家記得上你。傳聞這東西"
        "我這裡不掛板也不賣，都在人嘴上，你得自己開口。」"
    ),
    KeywordResponse(
        "同伴",
        "「想招人同行，得先遇得上人：路上、店裡，看哪位是能同行的，"
        "`talk` 聊幾句，聊得好了當場 `invite` 一句，願不願意人家自己答。"
        "我這兒櫃檯後站的、灶前燒火的，都是安了家的，邀不走。」",
    ),
    KeywordResponse(
        "委託",
        "「公會單子在公會的板上，我這兒不掛板，也不代人招工。"
        "你要尋活路，去公會看板；要在外頭結識了能共事的，回我這裡"
        "`talk` 說上話、`invite` 定下來，都行。"
        "酒館裡談事有個好處：出了這門，誰也不認得誰。」"
    ),
    KeywordResponse(
        "歇腳",
        "「趕路趕晚了？巷底就是爐火旅店，溫弗蕾德那兒床乾淨；"
        "不過夜就在我這兒坐著，`rest` 在哪兒都能歇，我這兒爐子暖、"
        "話又多，歇得比客棧巷外頭體面。要走了記得把話帶上，別把東西落下。」",
    ),
)

# 溫弗蕾德·古林 — the 爐火旅店. Her rooms are the narrative home of the
# rest/sleep/practice commands, and her table's job is exactly that
# discoverability (altoria-hospitality design: dialogue carries the
# affordance). She states the commands work here as anywhere — and quotes
# no rate, no bill, no stay entitlement: the lodging fee the document marks
# 〔提案〕 at line 308 stays un-invented, and a landlady who promises a free
# night is inventing a policy the change refuses to ship.
LODGING_RESPONSES: tuple[KeywordResponse, ...] = (
    KeywordResponse(
        "房間",
        "「樓上房間一排，各有門閂，關上門就是你自己的人。"
        "要歇就在樓下爐邊或樓上房間裡 `rest`，`rest` 這指令本不挑地方，"
        "只是我這兒牆厚門實，歇得住。要怎麼用，你開口問，我指給你。」",
    ),
    KeywordResponse(
        "過夜",
        "「要睡就 `sleep`，睡到精神全回那種；樓上靜，樓下爐邊也有人打盹。"
        "同一句話我講在前頭：`sleep` 本不挑地方，在哪裡都是睡，"
        "我這裡不過是床比街邊好——要睡個完整覺，我勸你上樓。」"
    ),
    KeywordResponse(
        "修煉",
        "「坐著乾歇可惜，可以邊歇邊練：`rest` 加時數，再掛一句 `practice` 加技能名，"
        "練的進帳按整小時結算。你尚未學會的、練到頂的，喊了也白喊，"
        "我勸你別白坐。要試就挑個空房，門閂一落，沒人打擾。」"
    ),
    KeywordResponse(
        "澡堂",
        "「出巷往東走，浴場前那間公共浴場就是——男女兩邊、深池河水，"
        "伊莎貝爾守著。`rest` `sleep` 的事我這兒管，泡澡的事她管，"
        "兩條腿走路，別錯過了街口。」",
    ),
)

# 伊莎貝爾·葦沼 — the 公共浴場管理員. Her whole job is the two sides and the
# order between them (docs/lore/settlement-locations.md line 354), and the
# room's content is the contrast the document keeps for story: human and
# beastfolk cover up, elves have no concept of shame. She runs no mechanism
# — no soak restores anything (line 352 keeps that 〔提案〕), and she says
# so in her own terms.
BATHHOUSE_RESPONSES: tuple[KeywordResponse, ...] = (
    KeywordResponse(
        "規矩",
        "「這地方只有一條規矩：男左女右，一邊一道牆，各進各門。"
        "泡的是河水燒的深池，洗的是趕路一身的塵。看順了眼要闖錯邊，"
        "我喊你回來——這一天我要喊幾百回，習慣了就好。」"
    ),
    KeywordResponse(
        "精靈",
        "「精靈客人？她們不覺得要牆。人跟獸人進這門先脫外袍、"
        "再彼此避開眼光，覺得遮著才禮貌；精靈從小就是那麼過的，"
        "你遮反而是你看不自然。到底誰怪，我守了廿年櫃檯也沒守出答案，"
        "反正牆在，各洗各的，相安無事。」",
    ),
    KeywordResponse(
        "泡湯",
        "「池子深水熱，泡到臉紅耳熱再上來衝一桶涼的，渾身鬆快——"
        "舒坦是舒坦，不是藥。有人說泡完連傷都好了一半，那是他昨夜睡得好，"
        "別記在池子帳上。要真講究，洗乾淨了再走，別帶著一身河風進旅店。」"
    ),
    KeywordResponse(
        "歇息",
        "「洗完想坐就外間長椅坐著；`rest` 在哪裡都使得，我這兒不過是"
        "蒸汽熏著容易睡著。睡過頭別怪我——要一覺睡到樓上去，"
        "旅店在巷子底，問溫弗蕾德。」"
    ),
)

# 托瓦德·鄧堡 — the 衛兵駐所 captain behind the 南門. His table's job is
# orientation: a traveller has just come through the arch and has not yet
# seen the city. He names the streets `地圖` and `前往` already resolve, sends
# anyone hunting work up the road to the guild board, and hangs nothing of his
# own — the document rules a parallel bounty system out in as many words
# (docs/lore/settlement-locations.md line 410), and the change's second
# refusal keeps his wall bare. He posts no work; the two roads that exist
# already carry it.
GUARDHOUSE_RESPONSES: tuple[KeywordResponse, ...] = (
    KeywordResponse(
        "進城",
        "「剛過南門的吧？聽一句：正對門這條是南大道，一直走到頭是中央廣場，"
        "廣場再上去三層台——市集、公會、神殿，一路都有門牌。"
        "要看全城的圖喊 `地圖`，要走去哪條街喊 `前往` 加街名，"
        "路是死的，圖上都有，不用問我第二次。」"
    ),
    KeywordResponse(
        "找活",
        "「尋活路上來對了：出門左轉，沿大道走到公會前，大廳裡有看板，"
        "`guild list` 撿單、`guild accept` 簽字，那是正路。"
        "我這牆上不掛單，也不代人掛——城裡委託走公會板，私底下相熟的另約，"
        "沒有一套掛在衛所牆上的懸賞，你別再問。」"
    ),
    KeywordResponse(
        "治安",
        "「城裡治安歸我們：白天查街、夜裡輪門。你在街上遇著事，"
        "找穿這身牌的，南門駐所、貴族區衛所兩處都有人。"
        "不過真話講在前面：我們管的是街，不是你背包裡東西的歸屬——"
        "錢貨糾紛去公會評，那才有條文。」"
    ),
    KeywordResponse(
        "過夜",
        "「天黑前要床？出駐所沿南大道往北，客棧巷底有爐火旅店，"
        "巷裡也有酒館可坐，坐得下趕路人。`rest` `sleep` 不挑地方，"
        "我這兒後頭那間小值房也躺得人，不過沒門閂，睡得睡不睡得看你。」"
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

# One entry per capital place that authors a dialogue_key, keyed exactly as
# the place row authors it: the merchants, the 光明神殿's 主祭, and the three
# hospitality attendants (altoria-hospitality) — attendant places are keyed
# the same way (the keys travel in the rows; the slice assembles into
# DIALOGUE_ROWS unchanged). altoria-crown-and-watch appends the watch's and
# the yard's three attendants; altoria-learning-and-exchange appends the
# academy's and the merchant hall's two after them. The 市集棚 has no entry:
# the host-less place authors no dialogue_key, so it has nothing to key.
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
        "altoria_tavern",
        DialogueDefinition(
            greeting=(
                "醉月酒館的蘿溫·古橡從櫃檯後打量你一眼，把抹布往肩上一搭："
                "「新面孔，坐。先把規矩聽懂：我這兒做的是話的生意——"
                "在店裡誰都能 `talk`；路上遇著投緣、能同行的，`invite` "
                "一聲才算正式邀定。傳聞都在人嘴上，你要打聽就開口問，"
                "坐著等，它是會挑人的。」"
            ),
            responses=TAVERN_RESPONSES,
        ),
    ),
    (
        "altoria_lodging",
        DialogueDefinition(
            greeting=(
                "爐火旅店的溫弗蕾德·古林從櫃檯後迎上來，指間捏著一串門閂鑰匙："
                "「趕路來的？樓上房間一排，各有門閂。我這兒能用的就三樣："
                "歇就 `rest`，睡就 `sleep`，想邊歇邊練就加一句 `practice` 加技能名。"
                "這三樣本不挑地方，我這裡不過是牆厚門實，歇得住。」"
            ),
            responses=LODGING_RESPONSES,
        ),
    ),
    (
        "altoria_bathhouse",
        DialogueDefinition(
            greeting=(
                "公共浴場管理員伊莎貝爾·葦沼抱著一疊乾淨布巾從水氣裡走出來，"
                "把你上下一量：「男邊往左，女邊往右，各進各門，這是這兒唯一的規矩。"
                "池子是河水燒的，深淺兩格。想問什麼儘管問，我手上活多，答得快。」"
            ),
            responses=BATHHOUSE_RESPONSES,
        ),
    ),
    (
        "altoria_guardhouse",
        DialogueDefinition(
            greeting=(
                "衛兵駐所的托瓦德·鄧堡從值房窗後轉出來，胸牌在燭火裡磕了一下："
                "「過門進來的？南門一帶歸我管。你要問路，我指；"
                "要問規矩，我講。牆上沒有你要找的東西——這話我先說在前頭，"
                "省得你繞回來再問。」"
            ),
            responses=GUARDHOUSE_RESPONSES,
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
