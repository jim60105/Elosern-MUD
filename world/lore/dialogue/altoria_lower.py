"""聖潔王都 (capital_altoria) LOWER-terrace authored dialogue rows.

The eatery, tavern, lodging, bathhouse and guardhouse tables, keyed exactly
as the LOWER-terrace place rows in ``places_altoria_lower.py`` author them.
Every greeting and response is written against the host's authored card in
``world/lore/npc_profiles/altoria_lower.py`` (npc-persona-content-altoria-
lower); the keyword identifiers are the dialogue panel's choice labels and
stay fixed.

Every line is spoken in character: a host knows only its own world, so no
line names a command, a game mechanic or the interface. A table teaches
what its place is for in the world's own terms (the innkeeper speaks of
resting, sleeping and quiet practice; the tavern keeper of talking to the
room and inviting a companion; the bathhouse keeper of the separated
sides). The hospitality hosts are ``attendant`` hosts who sell nothing;
none of the tables quotes a price or promises an unimplemented effect
(lodging fees, drink effects and bathing mechanics stay 〔提案〕).

Four keyword answers at most: the dialogue panel ships
``DIALOGUE_MAX_CHOICES`` entries and silently drops the rest, so each row
here carries exactly four.
"""

from world.lore.dialogue.shape import DialogueDefinition, KeywordResponse

# 西格瑪‧庫柏 — the eatery (staple_meals). A cooper's son who started by
# cooking for barge crews; plain, short sentences, asks whether you have
# eaten. He names the goods he deals in and leaves prices and counts to
# the counter's list (merchant-dialogue: live stock owns those facts).
EATERY_RESPONSES: tuple[KeywordResponse, ...] = (
    KeywordResponse(
        "餐點",
        "「最基本的就是一碗熱湯配麵包，吃完保證有力氣。黑麥硬麵包很耐放，攜行"
        "口糧放進背包剛好。今天有什麼，看單子就知道，要什麼跟我講。」",
    ),
    KeywordResponse(
        "招牌",
        "「招牌喔？當然是龍蝦濃湯啊！做法是港灣來的老船工教我，我熬了二十年都沒改"
        "過。想吃甜的就拿帝國的蜜漬果乾，精靈的蜜漬花蕊有時候也有，有沒有貨看"
        "單子吧。」",
    ),
    KeywordResponse(
        "乾糧",
        "「要出城？那攜行口糧跟燻肉乾一定要帶幾份。肉乾鹹是鹹了點，放好幾天都"
        "不會壞。等肚子餓了才想到要吃，就來不及囉。要幾份先算好，我一次幫你包"
        "起來。」",
    ),
    KeywordResponse(
        "收食",
        "「打到的肉、採到的東西，拿來讓我瞧一下嘛。乾淨新鮮的我就收，價錢照我店裡"
        "的規矩算。臭掉或說不出是哪來，我可不收，誰拿來都一樣。」",
    ),
)

# 蘿溫‧古橡 — the 醉月酒館, the lane's information room (招募同伴、打聽情報).
# Teasing, unhurried, answers with a question. Her table points at what
# already works here (talking to anyone in the room, inviting a traveller
# met out in the world to come along) and sells nothing: the cups are scenery, no drink does anything, no gamble pays
# out (docs/lore/settlement-locations.md keeps both 〔提案〕). The people
# behind her counter are settled and cannot be invited, and no authored
# row delivers rumours or commissions on its own.
TAVERN_RESPONSES: tuple[KeywordResponse, ...] = (
    KeywordResponse(
        "傳聞",
        "「消息？我這兒可沒貼告示喔，都在客人嘴裡。誰剛從迷宮出來、誰熟東門外"
        "的路，聊了才知道嘛。挑個順眼的坐過去，聊得來的話，人家下次還會記得你"
        "。我呢，頂多告訴你該往哪桌走。」",
    ),
    KeywordResponse(
        "同伴",
        "「想找人一起走？那得先碰得到人啊，路上也好、店裡也好。坐下來聊一聊，"
        "合得來再開口約，人家要不要是人家的事。我跟店裡的人就別想啦，我們有家"
        "有店，不出城。」",
    ),
    KeywordResponse(
        "委託",
        "「正經的委託去公會看板找啦，我這兒不貼單子，也不幫人找人手。公會前那"
        "棟大廳就是。在外面認識了靠得住的人，帶回來這兒坐，事情談好了再一起出"
        "發。放心，這屋裡講的話，出了門沒人會提。」",
    ),
    KeywordResponse(
        "歇腳",
        "「走到天都黑了吧？隔壁就是溫弗蕾德的旅店，床乾淨，門也鎖得牢。只是想"
        "坐一下的話，壁爐旁邊還有位子，我這兒比外面暖，也熱鬧多啦。」",
    ),
)

# 溫弗蕾德‧古林 — the 爐火旅店. Gentle, orderly, calls the young 「孩子」.
# Her rooms are the narrative home of resting, sleeping and quiet practice,
# and she speaks of them as a landlady would, never as commands. Resting
# works here as anywhere; she quotes no rate, no bill and no stay entitlement
# (the lodging fee stays 〔提案〕).
LODGING_RESPONSES: tuple[KeywordResponse, ...] = (
    KeywordResponse(
        "房間",
        "「房間在樓上，一張床、一個臉盆，門閂一拉，裡面就是你自己的地方了。要"
        "歇一下，在房裡或樓下火塘邊都行。我這裡沒什麼了不起，就是牆厚、門關"
        "得緊。」",
    ),
    KeywordResponse(
        "過夜",
        "「累壞了吧？那就上樓睡個好覺。樓下也有人靠著火塘打瞌睡，不過聽我一句，上樓睡"
        "，安靜多了。睡路邊跟睡床上，隔天起來的精神差很多呢。」",
    ),
    KeywordResponse(
        "修煉",
        "「光坐著發呆多可惜呀。很多冒險者會待在房裡，一邊歇一邊練劍、溫習咒文"
        "，我這裡夠安靜，不會有人吵你。先想一下要練哪樣吧。」",
    ),
    KeywordResponse(
        "澡堂",
        "「浴場啊？出了巷子往東走就到了，伊莎貝爾在顧。男女分兩邊，池子燒的是河水。"
        "睡覺的事找我，洗澡的事找她。洗乾淨再回來睡，床單也比較乾淨嘛。"
        "」",
    ),
)

# 伊莎貝爾‧葦沼 — the 公共浴場管理員. Fast, loud, exclamatory; curious
# about the elven custom, never contemptuous. Her job is the two sides and
# the order between them (docs/lore/settlement-locations.md), and the
# room's content is the contrast the document keeps for story. She runs no
# mechanism: no soak restores anything, and she says so herself.
BATHHOUSE_RESPONSES: tuple[KeywordResponse, ...] = (
    KeywordResponse(
        "規矩",
        "「就一條啦，男左女右，中間一道牆，各走各的門！今天我已經叫回來好幾個"
        "走錯的了，大多剛進城，被水氣熏到眼花。走錯也沒關係，聽到我喊就轉"
        "回來嘛！」",
    ),
    KeywordResponse(
        "精靈",
        "「精靈喔！他們覺得那道牆根本多餘。人類跟獸人進來都要先脫外衣，還要互"
        "相別過頭去，覺得遮起來才有禮貌。精靈從小就不覺得身體需要遮，看"
        "你遮著身子，他們反而覺得怪。到底誰比較對？我顧了二十年櫃檯還是搞不懂"
        "。反正牆在那裡，分開洗，大家都相安無事啦！」",
    ),
    KeywordResponse(
        "泡湯",
        "「水夠熱喔，泡到臉紅再起來，沖一桶冷水，整個人都鬆了！有人說泡完傷好"
        "了一半，我才不信呢，那是他前一晚睡得好啦。傷口痛就去找治療師，別指望"
        "我的池子。洗乾淨再走，別帶一身灰回旅店！」",
    ),
    KeywordResponse(
        "歇息",
        "「洗完想坐一下？外面有長椅。我這邊水氣暖，坐沒多久就想睡了。真的想睡個好覺"
        "，去客棧巷找溫弗蕾德，那邊有床啦！」",
    ),
)

# 托瓦德‧鄧堡 — the 衛兵駐所 captain behind the 南門. Clipped, orders his
# directions 「第一、第二」, hates being asked twice. His table orients the
# traveller who has just come through the arch with real street names. He
# posts no
# work of his own (docs/lore/settlement-locations.md rules a parallel
# bounty system out) and points work-seekers at the guild board and
# private arrangements.
GUARDHOUSE_RESPONSES: tuple[KeywordResponse, ...] = (
    KeywordResponse(
        "進城",
        "「聽好。第一，腳下這條是南大道，一路往北，過了大道北段就是中央廣場。"
        "第二，廣場東邊是公會前，西邊是市場街，北邊是通往上城的聖階。第三，每"
        "個路口都有路牌，照著走不會迷路。記住了，我不說第二遍。」",
    ),
    KeywordResponse(
        "找活",
        "「找工作，往北到中央廣場，再往東到公會前。大廳裡有看板，委託都貼在那"
        "裡，看中了就向公會的人登記。熟人私下託你的事，屬於你們之間的約定。駐"
        "所不貼委託單，以後也不會貼，不必再問。」",
    ),
    KeywordResponse(
        "治安",
        "「城裡的治安由衛兵負責。白天巡街，夜間輪班守門。在街上遇到麻煩，就找"
        "穿藍色罩袍的人，南門駐所和上城的貴族區衛所都有人值勤。我們管街上的秩"
        "序；你和別人之間的交易糾紛，不歸駐所處理。」",
    ),
    KeywordResponse(
        "過夜",
        "「要找地方睡，趁天黑前沿南大道往北，右手邊的客棧巷有爐火旅店，隔壁是"
        "醉月酒館。累了在哪裡都能靠著打個盹，但這間值房只有長凳，沒有門閂。要"
        "睡在這裡，你自己決定。」",
    ),
)

# One entry per LOWER-terrace place that authors a dialogue_key, keyed
# exactly as the place row authors it: the eatery, and the tavern, lodging,
# bathhouse and guardhouse attendants (altoria-hospitality /
# altoria-crown-and-watch) — the keys travel in the rows, so the slice
# assembles into DIALOGUE_ROWS unchanged.
ROWS: tuple[tuple[str, DialogueDefinition], ...] = (
    (
        "altoria_eatery",
        DialogueDefinition(
            greeting=(
                "餐館老闆西格瑪‧庫柏用圍裙擦著手，從灶後探出頭來：「喔，客人！吃飯了"
                "沒？湯還熱著喔，麵包跟帶出城的乾糧也都有。今天有什麼、還剩幾份，櫃檯"
                "上的單子都寫著，看中哪樣跟我說一聲就好。外面打到什麼好肉，也可以拿來給我瞧一下啦"
                "。來，先坐。」"
            ),
            responses=EATERY_RESPONSES,
        ),
    ),
    (
        "altoria_tavern",
        DialogueDefinition(
            greeting=(
                "醉月酒館的蘿溫‧古橡把抹布往肩上一甩，靠著吧台打量你：「唷，新面孔嘛"
                "。我這兒就一條規矩，在這裡講的話，不會害到講話的人。想打聽什麼就自己"
                "找人聊；路上碰到聊得來、又想一起走的人，開口約就是了。消息啊，都在客人"
                "嘴裡，你不開口問，誰會跟你說？」"
            ),
            responses=TAVERN_RESPONSES,
        ),
    ),
    (
        "altoria_lodging",
        DialogueDefinition(
            greeting=(
                "爐火旅店的溫弗蕾德‧古林從櫃檯後站起來，腰間的鑰匙叮噹作響：「歡迎啊"
                "，孩子，一路辛苦了吧。樓上有房間，每間都有門閂。想歇一下，樓下火塘邊"
                "有椅子；想睡個好覺，床單我才剛換過。要是想趁安靜練個劍、溫習一下咒"
                "文，房裡也很安靜喔。」"
            ),
            responses=LODGING_RESPONSES,
        ),
    ),
    (
        "altoria_bathhouse",
        DialogueDefinition(
            greeting=(
                "公共浴場管理員伊莎貝爾‧葦沼抱著一大疊布巾從水氣裡鑽出來，上下瞄了你"
                "一眼：「新來的吧！男生左邊、女生右邊，各走各的門，這裡就這一條規矩！"
                "池子是燒熱的河水，深的淺的都有。要問什麼快問，我還有一堆布巾沒摺！」"
            ),
            responses=BATHHOUSE_RESPONSES,
        ),
    ),
    (
        "altoria_guardhouse",
        DialogueDefinition(
            greeting=(
                "衛兵隊長托瓦德‧鄧堡從值房的窗邊轉過身，胸前的銅牌映著火盆的光：「剛"
                "從南門進來的？這一帶由我負責。問路，我告訴你；問規矩，我也告訴你。另"
                "外，駐所牆上沒有委託單，要找工作，請到冒險者公會。」"
            ),
            responses=GUARDHOUSE_RESPONSES,
        ),
    ),
)
