"""聖潔王都 (capital_altoria) LOWER-terrace authored dialogue rows.

These rows moved verbatim from the former ``altoria.py`` so each terrace
slice is owned by one content change: the eatery, tavern, lodging,
bathhouse and guardhouse tables, keyed exactly as the LOWER-terrace place
rows in ``places_altoria_lower.py`` author them.

The hospitality tables (altoria-hospitality) belong to ``attendant`` hosts
who sell nothing, so they ship no trade verb at all: the innkeeper's
greeting names ``rest``/``sleep``/``practice``, the tavern keeper's names
``talk``/``invite``, and the bathhouse keeper's explains the separated
sides — the commands each location exists to host, taught by the person
standing in it. None of them quotes a price or promises an unimplemented
effect (lodging fees, drink effects and bathing mechanics stay 〔提案〕).

Four keyword answers at most: the dialogue panel ships
``DIALOGUE_MAX_CHOICES`` entries and silently drops the rest, so each row
here carries exactly four.
"""

from world.lore.dialogue.shape import DialogueDefinition, KeywordResponse

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
                "餐館的老闆西格瑪·庫柏從灶後探出半個身子，圍裙上還沾著麵粉："
                "「餓了吧？熱食、乾糧、湯品，灶上都溫著。"
                "`shop stock` 還剩幾份瞞不了你，要就 `buy`；"
                "獵得的好料想換錢，帶來我 `sell` 收。先坐，先坐。」"
            ),
            responses=EATERY_RESPONSES,
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
)
