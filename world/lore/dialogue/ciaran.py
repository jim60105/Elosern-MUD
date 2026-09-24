"""暗影谷村 (ciaran) authored dialogue rows.

Each merchant place's ``dialogue_key`` must ship its table in the same change
(load-time resolution rejects an authored host that cannot speak): the
village's four homes arrive with the merchant-dialogue change, and every
later Ciaran content change appends its rows to ``ROWS`` here.

The register rule the settlement's premise establishes (merchant-dialogue
design: 「對這位精靈而言這是分享興趣與互助，不是營業」) binds these tables:

- No proprietor voice. The four are villagers sharing what they make, not
  shopkeepers running a business: no 「本店」, no quoted hours, no goods
  spoken of as stock.
- Four keyword answers at most (the panel truncates); the commands a visitor
  still needs — ``shop stock``, ``buy``, ``sell`` — ride inside what the
  villager would say about their own craft, the way the guild clerk's row
  folds guidance into character.

Host mapping (keys travel in the place rows; the slice assembles into
DIALOGUE_ROWS unchanged): 海莉爾·斯塔爾法爾 forges the village's shadow
steel; 拉瑞內斯·妮特布倫 keeps the candied blossom larder; 瓦爾溫·斯蒂爾瓦特爾
is the collector whose kept things line the old tree's house; 維特希爾·
威爾德布瑞亞爾 weaves at the loom on the slope.

ciaran-village-crafts adds the two the document names: 格威娜拉·希爾維爾莉夫
makes the village's ornaments on 銀葉坡, and 妮瑞斯·米斯特瓦勒 tends herbs
and remedies by the 藥草園.

ciaran-village-commons adds the two voices that converse without trading:
泰莉爾·菲溫德, the village's sword instructor on 練刀場, whose table speaks
of the branch's blade culture and points training at `rest` and `practice`
(she grants nothing — proficiency comes only from the trainee's own hours),
and 艾莉妮斯·達恩斯特瑞德爾, the elder, whose dwelling is memory rather than
office: the branch, the forest, the village's past. Neither asks, permits,
or decides anything. The shelter between them is host-less on purpose.
"""

from world.lore.dialogue.shape import DialogueDefinition, KeywordResponse

# 格威娜拉·希爾維爾莉夫 — the adornment maker (暗影谷村綴飾者).
# elven_adornments: 三稜晶符, 月牙耳環. Ornament is a love, not a trade;
# the village simply asked her to hang things up.
GWENAERA_RESPONSES: tuple[KeywordResponse, ...] = (
    KeywordResponse(
        "綴飾",
        "「銀絲是我自己絞的，貝殼是溪邊撿的，磨一整晚才亮得起來。"
        "完成的都曬在窗邊繩上，讓人看的，`shop stock` 報此刻掛著的；"
        "谷裡的人喜歡，我才多做一些。」",
    ),
    KeywordResponse(
        "晶符",
        "「三稜晶是族裡老辦法磨的，光進去、三條色出來，孩子各分著玩。"
        "掛在頸上也是這個用法——好看而已，不是什麼神器。"
        "想帶一枚走，`shop stock` 看看繩上還有沒有。」",
    ),
    KeywordResponse(
        "耳環",
        "「月牙那對本就是做給自己戴的，戴過一季洗淨了，"
        "瓦爾溫掛出去也是該的——飾物在谷裡不算稀罕，合眼緣要自己挑。"
        "在不在，`buy` 加名之前先 `shop stock` 問一聲。」",
    ),
    KeywordResponse(
        "舊飾",
        "「斷了的耳勾、鬆了的絲結，拿來我修，不計錢——器物壞了可惜。"
        "真要脫手什麼舊飾，`sell` 一聲，我掂著銀的成色回你；"
        "谷裡東西總該有第二條命，瓦爾溫也這樣講。」",
    ),
)

# 海莉爾·斯塔爾法爾 — the blade-smith (暗影谷村鑄刃者). elven_crafted_arms:
# 暗影鋼刀, 暗影鋼刀·影. She shares the blade, not trade talk.
HAILIEL_RESPONSES: tuple[KeywordResponse, ...] = (
    KeywordResponse(
        "鍛刀",
        "「谷底的鐵砂性子烈，鍛得溫順了才配叫鋼刀。砧邊擱著的是讓人帶走的，"
        "`shop stock` 報此刻的數；看中哪柄，同我說一聲便是——"
        "谷裡不興吆喝那一套。」",
    ),
    KeywordResponse(
        "影刀",
        "「『影』是我留手的名字：刃身淬過谷底第一道霜，靜看是黑的，"
        "舞起來才有那道影。一季出不了幾柄，想請它走，"
        "先 `shop stock` 看看它在不在砧邊。」",
    ),
    KeywordResponse(
        "鐵料",
        "「你手上有多餘的鐵料、磨壞的舊刃？擱這兒，爐子吃得下。"
        "同我說一聲 `sell`，我掂過分量回你銅幣——"
        "谷裡往來本來這樣，你來我往。」",
    ),
    KeywordResponse(
        "用刀",
        "「獵熊有獵熊的刀，剝皮有剝皮的刀，別拿一柄應所有事。"
        "要挑就 `shop stock` 看現下的；不合適我直說——"
        "刀跟人一樣，講緣分，不講體面。」",
    ),
)

# 拉瑞內斯·妮特布倫 — the fare-keeper (暗影谷村花饌好手). elven_fare:
# 精靈蜜漬花蕊. She feeds guests first and trades second.
LARENETH_RESPONSES: tuple[KeywordResponse, ...] = (
    KeywordResponse(
        "花饌",
        "「花蕊是春尾收的，蜜是自家蜂房的，漬足三個月才封罐。"
        "現下還剩幾罐，`shop stock` 一報你便知——帶幾罐上路，"
        "比乾糧體面，比鮮果耐放。」",
    ),
    KeywordResponse(
        "山產",
        "「雨季的菌、秋深的果，谷裡給什麼我做什麼。你獵採得了好料，"
        "拿來同我換銅，喊一聲 `sell` 便好；我這灶不挑料，只挑新鮮。」",
    ),
    KeywordResponse(
        "茶點",
        "「走累了先坐，粗茶是留客的，不計錢。要帶茶點上路，"
        "`shop stock` 裡現下有什麼便拿什麼，同我說 `buy` 加名字，"
        "我替你包兩層葉子。」",
    ),
    KeywordResponse(
        "口味",
        "「甜口的多，鹹口的少——谷裡口味清淡，旅人擔待。"
        "要濃的，你往王都餐館去，那邊灶氣旺。我這裡連蜜都捨不得多放，"
        "想甜的，`shop stock` 裡挑花蕊就是了。」",
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
# Memory is her content — the branch, the forest, the village's past. Her
# people's devotions stay where the document leaves them: unshown.
ELENIS_RESPONSES: tuple[KeywordResponse, ...] = (
    KeywordResponse(
        "村子",
        "「這谷裡的樹比我記得的事還老一截。早年村子不在這裡，"
        "是樹長穩了、溪改道了，人才跟著搬過來，一棵一棵認臉認熟的。"
        "你問村子的來歷，我能說的都是這種小事——精靈不寫史，"
        "史活在記得的人對著的那棵樹下。」",
    ),
    KeywordResponse(
        "基亞蘭",
        "「基亞蘭這一支是愛舞刀的，外頭傳我們脾氣硬，其實是記性長："
        "刀上刻的名字一代比一代密，磨損的是柄、不是名字。"
        "那對黑髮的雙生子就是這樣長大的：悠花在練刀場從雨季待到天晴，"
        "泰莉爾說她的手一握上木刀，整個場子就安靜下來。精靈的孩子在這裡"
        "長大，要去哪裡，總是自己決定的。」",
    ),
    KeywordResponse(
        "森林",
        "「林子認得村裡每一雙腳。獵有獵的道，採有採的時辰，"
        "哪片坡哪年歇養、哪條溪產什麼魚，族裡老一輩都背得下來。"
        "你要進林，記一句便夠：帶走多少、還回去多少，森林不計較，"
        "但會記得。」",
    ),
    KeywordResponse(
        "往事",
        "「你說要我決定？沒有什麼決定。族裡多年沒有『重要事務』了，"
        "幾棵樹下坐一坐、把話說齊，事情原本就是那個樣子。"
        "我不是管事的，也沒有什麼能准你或擋你的——"
        "要坐就坐，要問往事就問，老人家這裡只有時間。」",
    ),
)

# One entry per village merchant place, keyed exactly as the place rows author
# it.
ROWS: tuple[tuple[str, DialogueDefinition], ...] = (
    (
        "ciaran_hailiel_home",
        DialogueDefinition(
            greeting=(
                "海莉爾·斯塔爾法爾把淬火的刀按進油槽，白煙竄起；她抬眼看你："
                "「來得巧，今早剛出幾柄。砧邊擱著的隨你看，"
                "`shop stock` 報現下的數；要請走哪柄，同我說一聲。"
                "有鐵料舊刃要留這兒的，也儘管留。」"
            ),
            responses=HAILIEL_RESPONSES,
        ),
    ),
    (
        "ciaran_lareneth_home",
        DialogueDefinition(
            greeting=(
                "拉瑞內斯·妮特布倫從醃甕後抬起臉，指尖還沾著蜜，先遞給你一片葉："
                "「先嚐，再說別的。花蕊漬足三個月了，現下剩幾罐，"
                "`shop stock` 報你聽；想帶幾罐上路，同我說 `buy`。"
                "灶上永遠有粗茶，留客的，不計錢。」"
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
                "銀葉坡頂的屋裡，格威娜拉·希爾維爾莉夫從工作台後抬起眼，"
                "指間還捻著一縷銀絲：「來得正好，幫我看看這兩朵絞花哪個順眼。"
                "完成的都曬窗邊繩上，`shop stock` 報此刻掛著的；喜歡哪件同我說"
                "`buy`——谷裡人愛戴，我才多做。有斷了舊了要修的，擱這兒，不計錢。」"
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
                "古樹下的坐石被太陽曬得微溫，艾莉妮斯·達恩斯特瑞德爾抬眼看你，"
                "手裡一縷新剝的樹皮擱在膝上沒動：「坐。老人家這裡不賣東西，"
                "也沒有事情要你辦——你想問什麼，村裡的事、林子的事、"
                "還是這支刀的名字？記得的我說，不記得的我同你一起想。」"
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
