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
# 強效治療藥水, 魔力藥水. Her knowledge exists because elves get hurt too;
# she fusses over wounds first and takes back only her own jars.
NIRETH_RESPONSES: tuple[KeywordResponse, ...] = (
    KeywordResponse(
        "調藥",
        "「藥草從園裡採，方子是族裡老一輩傳下來的方法，一爐小火從早熬到晚。精"
        "靈不會生病，可是傷口和用光的魔力，不管哪一族都一樣。常備的就兩種，強"
        "效治療藥水和魔力藥水。」",
    ),
    KeywordResponse(
        "重傷",
        "「紅色那罐是強效治療藥水，傷得重才開，小傷用清水和草灰就夠了，別浪費"
        "喔。要帶幾罐防身，留幾枚銅幣給我就好。」",
    ),
    KeywordResponse(
        "魔力",
        "「藍色那罐是魔力藥水，施法的人累了，喝一口就能緩過來，精靈喝也一樣有"
        "效。聽說外頭把這東西當寶，在谷裡只是多熬一爐的事啊。」",
    ),
    KeywordResponse(
        "藥草",
        "「園裡的藥草我自己採，外頭的我不收，誰知道藥性有沒有走掉。我熬的藥你"
        "要是用不到，原封不動拿回來，我收下就是。」",
    ),
)

# 瓦爾溫·斯蒂爾瓦特爾 — the collector (暗影谷村蒐羅者). elven_sundries:
# 精靈蛛絲. Her home is full of kept things, each with a story; she trades
# stories for stories, wears a 月牙耳環 from 格威娜拉's batch, and takes back
# only the silk she hangs out.
VALWYN_RESPONSES: tuple[KeywordResponse, ...] = (
    KeywordResponse(
        "蒐羅",
        "「這些呀，路上撿到、林子裡換來、溪水沖上岸，全都在這兒。哎，你看那根"
        "羽毛，三百年前一隻大鳥掉下來，那天下了好大的雨……啊，又扯遠了。這些"
        "都是我的寶貝，不拿出來換，你看就好。」",
    ),
    KeywordResponse(
        "蛛絲",
        "「精靈蛛絲是林子裡的蛛吐的絲，韌得很，編成繩子，風雨都扯不斷。村裡每"
        "個人都會編，我編得多一點，就掛出來給大家取用。你要幾束就跟我說，我替"
        "你從繩上解下來。」",
    ),
    KeywordResponse(
        "耳環",
        "「這對月牙耳環？格威娜拉的手藝，我跟她換來，戴了好多年了。哎，要是你"
        "也喜歡，去銀葉坡找她，她窗邊掛著一整排呢。我這對可不給喔，上面有故事"
        "。」",
    ),
    KeywordResponse(
        "以物易物",
        "「我最喜歡換東西了！不過我換的是故事，你說一段路上的見聞，我就講一段"
        "這屋裡哪樣東西的來歷。蛛絲要是用不完，原封不動拿回來，我收下，回你幾"
        "枚銅幣。」",
    ),
)

# 泰莉爾·菲溫德 — the sword instructor (暗影谷村刀術導師). She shares the
# 練刀場 with 海莉爾 the blade-smith: the forge and the teaching, on one
# clearing. She grants nothing and spars with nobody: skill comes from the
# trainee's own repetition, and her lines say so in the village's terms.
TELIEL_RESPONSES: tuple[KeywordResponse, ...] = (
    KeywordResponse(
        "刀術",
        "「基亞蘭的孩子先認刀柄，再認刀鋒。舞刀是谷裡人說話的另一種方式，用來"
        "守護的時候，比用來殺敵的時候多。你看林邊樹幹上那些刀痕，一代人留一片"
        "。想學，學的是這個，我的名聲不重要。」",
    ),
    KeywordResponse(
        "練習",
        "「谷裡沒有拜師這回事，本事也沒辦法從誰手上交給你。想練，就自己來場上"
        "反覆練，練到手記得為止。我站在這裡，只是讓你知道場子怎麼用。」",
    ),
    KeywordResponse(
        "練刀場",
        "「場子日夜都在。清晨給孩子，日頭偏西換輪值的獵隊，入夜以後，誰想一個"
        "人練，誰就自己來。木刀擱在場邊，借還都不用說。想要真刀，去找住在場子"
        "另一頭的海莉爾。」",
    ),
    KeywordResponse(
        "比劃",
        "「想找人對打？谷裡沒有人陪外人動刀，我也不陪。我的手留給還不會收刀的"
        "孩子。想試身手，樁子在那邊，先對著它練。」",
    ),
)

# 維特希爾·威爾德布瑞亞爾 — the weaver (暗影谷村織衣者). elven_attire:
# 精靈短袍傳統服飾, 精靈戰鬥服飾, 精靈傳統服飾, 精靈森林輕紗. Slow and
# thoughtful; clothes exist to show the body well (the elves hold no shame
# about it), and she takes back only what she wove.
VETHIEL_RESPONSES: tuple[KeywordResponse, ...] = (
    KeywordResponse(
        "織衣",
        "「經線我自己漿，緯線我自己染，一塊布從清晨織到星光出來。架上有墨黑的"
        "短袍、戰鬥服飾、白色的蛛絲傳統服飾，還有晨露織的森林輕紗，每一件的性"
        "子都不一樣。喜歡哪件，換去穿就是。」",
    ),
    KeywordResponse(
        "戰衣",
        "「精靈戰鬥服飾是墨黑色，貼身、好動，進林子打獵穿它最方便。嗯……它讓"
        "身體動得自在，遮住的地方不多，族裡的人都喜歡。」",
    ),
    KeywordResponse(
        "禮袍",
        "「白色那件是精靈傳統服飾，用蛛絲織成，族裡祭禮時穿。我們覺得身體值得"
        "讓人看，所以它織得很薄……外面的人看了常會臉紅呢。森林輕紗是晨露編的"
        "長裙，透光像霧，只在那一季做得出來。」",
    ),
    KeywordResponse(
        "舊衣",
        "「穿舊或穿不下的衣服不用丟，洗乾淨拿來我改；改不了的就拆成布，布還能"
        "派上別的用場。我織的衣服用不到了，也可以拿回來，換幾枚銅幣回去。」",
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
                "村北古樹下的屋裡，瓦爾溫·斯蒂爾瓦特爾正把一串貝殼掛上繩結，聽見腳步"
                "聲就回頭笑了：「哎，有客人！你從哪裡來呀？路上看到什麼了？先別急著走"
                "，坐下來聊一會兒。這屋裡掛的東西都有故事，想聽哪一樣，我都講給你聽。"
                "」"
            ),
            responses=VALWYN_RESPONSES,
        ),
    ),
    (
        "ciaran_vethiel_home",
        DialogueDefinition(
            greeting=(
                "織機聲在門內停下，維特希爾·威爾德布瑞亞爾從經線間探出身子，手上還捏"
                "著梭子：「嗯……來了啊。你喜歡什麼顏色？架上的衣服隨你看，看上哪件，"
                "我拿下來讓你摸一下料子。」"
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
                "藥草園邊的屋裡滿是苦甜交錯的氣味，妮瑞斯·米斯特瓦勒正替藥爐壓小火，"
                "回頭先把你上下打量了一遍：「沒受傷吧？那就好。這輪藥剛起罐，強效治療"
                "藥水和魔力藥水都還有一些，要帶幾罐上路就跟我說喔。」"
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
                "場邊的木刀排成一列，泰莉爾·菲溫德剛收完最後一組動作，額上的汗還沒乾"
                "。她看了一眼你的站姿：「來看練刀？場子在這裡，木刀在門邊。我這裡沒有"
                "東西要給你，也沒有捷徑。」"
            ),
            responses=TELIEL_RESPONSES,
        ),
    ),
)
