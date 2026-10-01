"""暗影谷村 (ciaran) authored dialogue rows.

Each merchant place's ``dialogue_key`` must ship its table in the same change
(load-time resolution rejects an authored host that cannot speak). Each table
is written against its host's persona card in
``world/lore/npc_profiles/ciaran_homes_a.py`` or ``ciaran_homes_b.py``.

The register rule the settlement's premise establishes (merchant-dialogue
design: 「對這位精靈而言這是分享興趣與互助，不是營業」) binds these tables:

- No proprietor voice. The makers are villagers sharing what they make, not
  shopkeepers running a business: no 「本店」, no quoted hours, no goods
  spoken of as stock.
- Every line is spoken in character: a villager knows only the village's
  world, so no line names a command, a game mechanic or an interface
  element. Villagers speak in everyday colloquial register.
- Four keyword answers at most (the panel truncates).

Host mapping (keys travel in the place rows; the slice assembles into
DIALOGUE_ROWS unchanged): 海莉爾·斯塔爾法爾 forges the village's shadow
steel; 拉瑞內斯·妮特布倫 keeps the candied blossom larder; 瓦爾溫·斯蒂爾瓦特爾
is the collector whose kept things line the old tree's house; 維特希爾·
威爾德布瑞亞爾 weaves at the loom on the slope; 格威娜拉·希爾維爾莉夫 makes
the village's ornaments on 銀葉坡; 妮瑞斯·米斯特瓦勒 tends herbs and remedies
by the 藥草園. Two voices converse without trading: 泰莉爾·菲溫德, the
village's sword instructor on 練刀場, who grants nothing (skill comes from
the trainee's own practice), and 艾莉妮斯·達恩斯特瑞德爾, the elder, whose
dwelling is memory rather than office. Neither asks, permits, or decides
anything. The shelter between them is host-less on purpose.
"""

from world.lore.dialogue.shape import DialogueDefinition, KeywordResponse

# 格威娜拉·希爾維爾莉夫 — the adornment maker (暗影谷村綴飾者).
# elven_adornments: 三稜晶符, 月牙耳環. Chatty and delighted by pretty things;
# ornament is a love, not a trade, and she mends broken pieces for free. She
# takes back only the pieces her own line carries.
GWENAERA_RESPONSES: tuple[KeywordResponse, ...] = (
    KeywordResponse(
        "綴飾",
        "「銀絲我自己絞，貝殼在溪邊撿，晶砂要磨一整晚才會亮。做好的都掛在窗邊"
        "那條繩上，族人喜歡就拿去戴。你喜歡哪件就跟我說，看著給點什麼都好嘛。"
        "」",
    ),
    KeywordResponse(
        "晶符",
        "「三稜晶符用族裡傳下來的老方法磨，光照進去，會分成三種顏色跑出來，很"
        "漂亮對吧？欸，戴在脖子上就是好看而已，沒有什麼神奇的力量喔。村裡的孩"
        "子成年時，常來跟我討一枚。」",
    ),
    KeywordResponse(
        "耳環",
        "「月牙耳環是我最常做的東西，一對接一對地絞，絞到閉著眼睛都會。瓦爾溫"
        "耳朵上那對也出自我手，跟我身上這幾枚同一批。合不合眼緣要你自己挑，我"
        "幫你舉著鏡子嘛。」",
    ),
    KeywordResponse(
        "舊飾",
        "「斷掉的耳勾、鬆掉的絲結，拿來我幫你修，不用錢。東西壞了就丟，太可惜"
        "了嘛。用不到的晶符或耳環也可以拿回來，我會看銀的成色，回你一點東西。"
        "」",
    ),
)

# 海莉爾·斯塔爾法爾 — the blade-smith (暗影谷村鑄刃者). elven_crafted_arms:
# 暗影鋼刀, 暗影鋼刀·影, forged as a pair. Measured and plain; she looks at a
# visitor's hands before talking blades, and takes back only her own blades.
HAILIEL_RESPONSES: tuple[KeywordResponse, ...] = (
    KeywordResponse(
        "鍛刀",
        "「谷底的鐵砂性子烈，要反覆鍛打，打到鋼性均勻才叫暗影鋼。砧邊那對暗影"
        "鋼刀剛完成。外人難得來，你要是真用得上，拿銅幣來換，我也肯割愛。」",
    ),
    KeywordResponse(
        "影刀",
        "「暗影鋼刀·影是副手刀，跟主手刀成對打。刃身淬過谷底的第一道霜，靜止"
        "時看起來一片黑，揮起來才看得到那道影子。我一次只做一對，砧邊還有沒有"
        "，你自己去瞧吧。」",
    ),
    KeywordResponse(
        "鐵料",
        "「鐵料就不用了，鐵砂我自己去谷底挖。我打的刀用舊了、用不到了，拿回來"
        "給我，還能用的我收下。」",
    ),
    KeywordResponse(
        "用刀",
        "「打獵有打獵的刀，剝皮有剝皮的刀，別想拿一把刀應付所有事。暗影鋼刀當"
        "主手，影刀當副手，兩把一起用最順。合不合你的手，我會直說。」",
    ),
)

# 拉瑞內斯·妮特布倫 — the fare-keeper (暗影谷村花饌好手). elven_fare:
# 精靈蜜漬花蕊. Soft and unhurried; she feeds a guest before anything else and
# takes back only her own jars.
LARENETH_RESPONSES: tuple[KeywordResponse, ...] = (
    KeywordResponse(
        "花饌",
        "「這是春末收的花蕊，用谷裡採的蜜漬上三個月才封罐……甜，可是不膩口吧"
        "？想帶幾罐上路，拿銅幣來換就好。比乾糧好吃，也比鮮果耐放。」",
    ),
    KeywordResponse(
        "山產",
        "「谷裡每一季都有好東西……雨季有菌子，秋天有果子，春末有花。我做點心"
        "只用自己採的料，哪一季採到什麼，就做什麼。我漬的花蕊要是吃不完，原封"
        "不動拿回來，我收下就是。」",
    ),
    KeywordResponse(
        "茶點",
        "「走累了先坐下吧，花茶請你喝……今天的茶點擺在窗邊的矮凳上，路過的人"
        "都能拿。想帶花蕊上路，跟我說一聲，我用兩層葉子幫你包好。」",
    ),
    KeywordResponse(
        "口味",
        "「谷裡的口味清淡，甜多鹹少……想吃重口味，大概要到外頭的大城去了吧。"
        "我連蜜都不敢多放，怕蓋住花香。喜歡甜，就挑蜜漬花蕊吧。」",
    ),
)

# 妮瑞斯·米斯特瓦勒 — the hedge-healer (暗影谷村調藥者). elven_remedies:
# 強效治療藥水, 魔力藥水. Her knowledge exists because elves get hurt
# too; the jars are simply what she keeps enough of to share.
NIRETH_RESPONSES: tuple[KeywordResponse, ...] = (
    KeywordResponse(
        "調藥",
        "「藥草是園裡長的，方子是族裡傳的，製藥這一爐小火從早熬到晚。"
        "強效治療藥水與魔力藥水是兩爐常備的，`shop stock` 報此刻罐裡的數；"
        "精靈不害病歸不害病，傷口與空掉的魔力可不認種族。」",
    ),
    KeywordResponse(
        "重傷",
        "「紅的這罐救急，傷重才舍得開封，輕傷用清水與草灰就夠。"
        "要帶幾罐備著，`buy` 加名便是；擱藥園邊晒著的那批，"
        "下個月才熬得新一輪——急不來。」",
    ),
    KeywordResponse(
        "魔力",
        "「藍的是魔力藥水，給施法的人回氣用的，魔法種族一樣喝得，效用不打折。"
        "外頭賣得金貴，谷裡不過是多熬一爐的事，`shop stock` 有就提走。」",
    ),
    KeywordResponse(
        "藥草",
        "「園裡採得多、你尋得的料好，我都收：曬乾的根、開花的頂葉都要。"
        "`sell` 喊一聲我過秤回銅，藥性壞了的請帶回去——"
        "那類東西我擱不下手。」",
    ),
)

# 瓦爾溫·斯蒂爾瓦特爾 — the collector (暗影谷村蒐羅者). elven_sundries:
# 精靈蛛絲 (月牙耳環 rides the adornment maker's shelf since
# ciaran-village-crafts). Her home is full of kept things, each with a story.
VALWYN_RESPONSES: tuple[KeywordResponse, ...] = (
    KeywordResponse(
        "蒐羅",
        "「路上撿的、林裡換的、潮水推上岸的——留得下的都掛在這兒了。"
        "哪件入眼同我說；`shop stock` 報的是此刻還掛著的。"
        "掛出來，就是讓人帶走的。」",
    ),
    KeywordResponse(
        "蛛絲",
        "「林蛛的絲韌得很，編進繩索裡，風雨不斷。一小束一小束繫著，"
        "要幾束同我說，`buy` 加個名便是。這東西村裡人人編得，"
        "我編得多些，就替大夥兒掛出來罷了。」",
    ),
    KeywordResponse(
        "耳環",
        "「月牙那對是銀絲絞的，我自己戴過一季，洗淨就掛出來了。"
        "飾物在谷裡不算稀罕，稀罕的是合眼緣——`shop stock` 看看在不在，"
        "在，就是它與你有緣。」",
    ),
    KeywordResponse(
        "以物易物",
        "「你若捨得什麼，留下同我換，銅錢倒在其次。舊繩結、路上雕的"
        "小木活、外頭帶稀奇的零嘴，都算。要脫手現成的也成，"
        "`sell` 喊一聲，我替你收著。」",
    ),
)

# 泰莉爾·菲溫德 — the sword instructor (暗影谷村刀術導師). She shares the
# 練刀場 with 海莉爾 the blade-smith: the forge and the teaching, on one
# clearing. She teaches nothing directly — training is `rest` plus
# `practice`, and her lines say so without pretending otherwise.
TELIEL_RESPONSES: tuple[KeywordResponse, ...] = (
    KeywordResponse(
        "刀術",
        "「基亞蘭的孩子先認刀柄、後認刀鋒：舞刀是谷裡人說話的另一種聲音，"
        "不是殺人用的手藝。你看見林緣挂的那些刀痕了嗎？一代人補一片，"
        "傷口的帳早就算清了。想學的是這個，不是我的名聲。」",
    ),
    KeywordResponse(
        "練習",
        "「我這邊沒有『拜師』這道門——谷裡不興把功夫鎖在某個人手上。"
        "要練就 `rest` 養足精神，再 `practice 刀術`，一個時辰一個時辰地熬；"
        "熟練度是你自己流汗換來的，我站在這裡只是讓你知道場子怎麼用。」",
    ),
    KeywordResponse(
        "練刀場",
        "「場子日夜都在。清晨是孩子的，日頭偏西是輪值的獵隊，"
        "入夜後誰想獨自走幾遍式子，誰就自己來。木刀擱場邊，借還不用登記；"
        "要買真刀才要找對人——鍛的那位住場子另一頭。」",
    ),
    KeywordResponse(
        "比劃",
        "「想找人過兩手？谷裡人得閒會陪，手上有準頭，點到為止；"
        "`engage` 開口便是，也可以去公會考場按規矩打。"
        "我不同你比——導師的手留給還不會收刀的人，不是留給看熱鬧的。」",
    ),
)

# 維特希爾·威爾德布瑞亞爾 — the weaver (暗影谷村織衣者). elven_attire:
# 精靈短袍傳統服飾, 精靈戰鬥服飾, 精靈傳統服飾, 精靈森林輕紗.
VETHIEL_RESPONSES: tuple[KeywordResponse, ...] = (
    KeywordResponse(
        "織衣",
        "「經線是我漿的，緯線是我染的，一塊布從早織到星起。"
        "織成都擱架上讓人挑，`shop stock` 報此刻的數——"
        "短袍、戰衣、禮袍、林紗，各是各的性子。」",
    ),
    KeywordResponse(
        "戰衣",
        "「戰鬥服飾夾了細鏈，輕是真輕，護得住肩背。進林子獵狼穿它正合適；"
        "要哪件同我說，`buy` 加名，我從架上取下來替你拍淨。」",
    ),
    KeywordResponse(
        "禮袍",
        "「祭禮的袍子一季織兩件，花樣是老譜，織的人手生不得。"
        "外鄉人愛那襲森林輕紗，透光像霧——在不在架上，"
        "`shop stock` 一問便知。急不來，織物有自己的時辰。」",
    ),
    KeywordResponse(
        "舊衣",
        "「穿舊的、小了的不必丟，洗淨拿來我改；改不了的拆成布，"
        "布還有布的去處。要連布帶線一併脫手，`sell` 一聲，"
        "我按紗的成色回你——谷裡東西總該有第二條命。」",
    ),
)

# 艾莉妮斯·達恩斯特瑞德爾 — the elder (暗影谷村長老). Her dwelling is a
# keeper's, not an office: no petition, no permission, no council business.
# Memory is her content: the branch, the forest, the village's past. Her
# people's devotions stay where the document leaves them: unshown.
ELENIS_RESPONSES: tuple[KeywordResponse, ...] = (
    KeywordResponse(
        "村子",
        "「嗯……這村子早年不在這裡。古樹長穩了、溪水改了道，族人才跟著搬過來"
        "，一棵樹接一棵樹地認熟。你問村子的來歷，我能說的都是這種小事。精靈不"
        "寫史書，往事都記在記得的人心裡，還有那幾棵老樹下。」",
    ),
    KeywordResponse(
        "基亞蘭",
        "「是啊，基亞蘭這一支愛刀。外頭說我們脾氣硬，我們自己覺得是記性長。刀"
        "柄上刻的名字一代比一代多，刀柄磨舊了，名字還在。那對黑髮的雙生子也在"
        "這裡長大，悠花在練刀場從雨季待到天晴，泰莉爾說，那孩子一握上木刀，整"
        "個場子都安靜下來。」",
    ),
    KeywordResponse(
        "森林",
        "「林子認得村裡每一雙腳。打獵有打獵的路，採集有採集的時節，哪片坡哪一"
        "年該讓它歇著，族裡的老一輩都記得。你要進林子，記住一句就夠，帶走多少"
        "，就還回去多少。森林不計較，可是它會記得。」",
    ),
    KeywordResponse(
        "往事",
        "「往事啊……有一年冬天溪水結了冰，孩子們跑到冰上練刀，摔得滿身是雪，"
        "笑聲一路傳到古樹這裡。族裡的往事多半是這樣的小事，已經很多年沒有什麼"
        "『重要的事』了。常有人來找我做主，可是我不管事，也沒有什麼能准你或攔"
        "你。」",
    ),
)

# One entry per village merchant place, keyed exactly as the place rows author
# it.
ROWS: tuple[tuple[str, DialogueDefinition], ...] = (
    (
        "ciaran_hailiel_home",
        DialogueDefinition(
            greeting=(
                "海莉爾·斯塔爾法爾把剛淬好的刀按進油槽，白煙竄了起來。她抬眼看了一下"
                "你的手：「來看刀吧。砧邊那對剛打好，可以拿起來試。先讓我瞧一下你平常"
                "怎麼握刀。」"
            ),
            responses=HAILIEL_RESPONSES,
        ),
    ),
    (
        "ciaran_lareneth_home",
        DialogueDefinition(
            greeting=(
                "溪畔小徑旁的屋裡飄著糖漬花的甜香，拉瑞內斯·妮特布倫從醃甕後抬起臉，"
                "先遞給你一片葉子，上面擺著一顆蜜漬花蕊：「遠來的客人……先嚐一口吧。"
                "嚐過了，我們再聊。」"
            ),
            responses=LARENETH_RESPONSES,
        ),
    ),
    (
        "ciaran_valwyn_home",
        DialogueDefinition(
            greeting=(
                "古樹下的屋裡，瓦爾溫·斯蒂爾瓦特爾正把一串貝殼掛上繩結；"
                "她抬手環指了一圈：「路上撿的、林裡換的，"
                "掛出來就是讓人帶走的。哪件入眼同我說，"
                "`shop stock` 報此刻還掛著的。你也捨得什麼要留下？"
                "喊 `sell` 便好——你來我往，谷裡本來這樣。」"
            ),
            responses=VALWYN_RESPONSES,
        ),
    ),
    (
        "ciaran_vethiel_home",
        DialogueDefinition(
            greeting=(
                "織機聲在門內停下，維特希爾·威爾德布瑞亞爾從經線間探出半張臉，"
                "手上還捏著梭子：「等等就好——成了。短袍戰衣禮袍林紗，"
                "架上隨你挑，`shop stock` 報此刻的數。要帶走哪件同我說 `buy`；"
                "有舊衣要拿來的，洗淨了擱機邊便是。」"
            ),
            responses=VETHIEL_RESPONSES,
        ),
    ),
    (
        "ciaran_gwenaera_home",
        DialogueDefinition(
            greeting=(
                "銀葉坡頂的屋裡，格威娜拉·希爾維爾莉夫從工作檯後抬起頭，舉起兩朵銀絲"
                "絞花湊到你面前：「欸，你來得正好！這兩朵哪一朵比較好看？左邊這朵嘛…"
                "…算了，我等一下再改。做好的都掛在窗邊繩上，喜歡哪件就跟我說；有東西"
                "壞了要修，也拿過來吧。」"
            ),
            responses=GWENAERA_RESPONSES,
        ),
    ),
    (
        "ciaran_nireth_home",
        DialogueDefinition(
            greeting=(
                "藥草園邊的屋裡滿是苦甜交錯的氣味，妮瑞斯·米斯特瓦勒正替藥爐"
                "壓小火：「來得巧，這輪剛起罐。強效治療藥水與魔力藥水都還有些，"
                "`shop stock` 報罐裡的數；要帶幾罐防身，同我說 `buy`。"
                "園裡採得多的藥草你要脫手，`sell` 一聲，我過秤。」"
            ),
            responses=NIRETH_RESPONSES,
        ),
    ),
    (
        "ciaran_elenis_home",
        DialogueDefinition(
            greeting=(
                "長老古樹下的坐石曬得微溫，艾莉妮斯·達恩斯特瑞德爾抬眼看你，膝上擱著"
                "一縷剛剝下的樹皮：「是啊，坐吧，小傢伙。老人家這裡沒有東西可以給你，"
                "也沒有事情要你辦。想聽村子的事、林子的事，還是這一族為什麼愛刀？記得"
                "的我就說。」"
            ),
            responses=ELENIS_RESPONSES,
        ),
    ),
    (
        "ciaran_teliel_home",
        DialogueDefinition(
            greeting=(
                "場邊的木刀排成一列，泰莉爾·菲溫德剛收最後一組式子，額上的汗"
                "還沒乾；她抱臂看你：「來看練刀的？場子就是這樣用的。"
                "先 `rest` 養好精神，再 `practice 刀術`，一個時辰一個時辰來——"
                "谷裡沒有捷徑，我這裡也沒有要賣你的東西。」"
            ),
            responses=TELIEL_RESPONSES,
        ),
    ),
)
