"""聖潔王都 (capital_altoria) MIDDLE-terrace authored dialogue rows.

The general store, forge, tailor, jeweller, alchemist and merchant hall
tables, keyed exactly as the MIDDLE-terrace place rows in
``places_altoria_middle.py`` author them. Each table is written against its
host's persona card in ``world/lore/npc_profiles/altoria_trade.py``.

Every line is spoken in character: a host knows only its own world, so no
line names a command, a game mechanic or an interface element. The
shopkeepers talk about what THAT shop actually carries, in their own voice,
and point at the shelf, the counter and the price board, never at how a
player trades. The five shops speak in everyday colloquial register; the
merchant guild master receives callers as an office-holder and speaks
formally. Lines never state a fixed price, a stock count or an opening
hour: live shop data owns those.

聖潔王都市集棚 (``altoria_market_stalls``) has no entry here: the
host-less place authors no dialogue_key, so it has nothing to key.

Four keyword answers at most: the dialogue panel ships
``DIALOGUE_MAX_CHOICES`` entries and silently drops the rest, so each row
here carries exactly four.
"""

from world.lore.dialogue.shape import DialogueDefinition, KeywordResponse

# 瑪爾特·金秤 — the general store (sex ``other``: no gendered pronoun in
# narration). Brisk, lists goods like a stock check, asks whether the
# visitor is heading out or just back. The shelf is the sundries bundle:
# light, compass, camp gear, raw materials and the dungeon drops it buys.
# Accessories and remedies belong to the jeweller and the alchemist, and the
# baptismal holy water to the sanctum up the 聖階.
GENERAL_STORE_RESPONSES: tuple[KeywordResponse, ...] = (
    KeywordResponse(
        "賣什麼",
        "「出城用的都在這。魔法燈、附魔羅盤、迷宮探照符、通訊法螺，還有粗鐵礦"
        "、魔獸結晶這些料。價錢寫在牆上那塊板子，自己看，我不講價。就這樣。」",
    ),
    KeywordResponse(
        "材料",
        "「迷宮裡帶回來的哥布林耳朵、史萊姆黏液、巨魔尖牙、地龍鱗片，我都收。"
        "擱上櫃檯，我看過就報數，錢當場點給你。要買也有，魔導晶核、龍鱗碎片、"
        "精靈蛛絲，在架子最上層。」",
    ),
    KeywordResponse(
        "行頭",
        "「第一次出城？好，照我說的帶。燈一定要帶，迷宮裡黑到看不見自己的手。"
        "羅盤防迷路，探照符撕開能把四周照亮一小段時間，露營魔導具一打開就是個"
        "小帳篷，風雨蟲子都進不來。通訊法螺留著走散的時候喊人用。嗯，大概就這"
        "些。」",
    ),
    KeywordResponse(
        "飾品藥水",
        "「那兩樣不在我這了。飾品去隔壁首飾坊找艾蓮娜，藥水往東市的鍊金坊找希"
        "碧拉，都是老街坊。報我的名字也沒用，她們一樣不講價。要受洗聖水的話，"
        "得爬聖階上去，大神殿前的聖所有自己的櫃檯。」",
    ),
)

# 維爾登·黑潭 — the forge. Terse to the bone: few words, no particles,
# asks what the visitor fights with first. common_arms is his wall, from the
# plain sword up to the knight blade he is proudest of. He buys back only
# what he hangs on that wall, and there is no repair service to promise.
FORGE_RESPONSES: tuple[KeywordResponse, ...] = (
    KeywordResponse(
        "兵器",
        "「牆上那排。普通劍、鐵短刀、狩獵擲斧。弓和法杖在左邊，獵手長弓、見習"
        "術師法杖。價錢看門邊木牌。拿下來試手感，別揮到人。」",
    ),
    KeywordResponse(
        "好貨",
        "「最裡面那把。騎士制式長劍，我親手打，校場的見習騎士都用它。旁邊那把"
        "魔導長劍，刃裡導過元素，貴。錢夠再看。」",
    ),
    KeywordResponse(
        "賣鐵",
        "「我只收牆上掛著那幾樣。用不著的劍、斧、弓拿回來，還能用，我就收。礦"
        "石、碎鐵別往這擱，拿去市場街的雜貨店。」",
    ),
    KeywordResponse(
        "保養",
        "「磨刀石自己帶。鈍了就磨，別拿去砍石頭。收劍前擦乾，上油。斷了就換一"
        "把，接回去的劍不可靠。」",
    ),
)

# 妮絲塔·狐溪 — the tailor. Warm, chatty, sizes people up while she talks
# and asks where they are headed. common_outfits is her rack: leathers,
# robes, mail and plate for the road, and the vestments the upper city and
# the cathedral order from her.
TAILOR_RESPONSES: tuple[KeywordResponse, ...] = (
    KeywordResponse(
        "衣甲",
        "「要護身的話，皮甲最輕、最好動，鎖子甲擋得住刀，就是重了點喲。想再穩"
        "一點，騎士全套板甲和鐵盾也有，不過那要有力氣撐得住呢。會施法的人，穿"
        "術師長袍就好，袖口我都改得很順手。」",
    ),
    KeywordResponse(
        "旅裝",
        "「走遠路呀，衣服合身最要緊，磨肩又磨腳，走三天就受不了。錢不多就先挑"
        "件皮甲，一件合身，勝過三件湊合著穿。常施法的話，大術師補綴長袍的內裡"
        "縫滿了符文，施法比較不累喔，就是貴了點。」",
    ),
    KeywordResponse(
        "禮服",
        "「上城的貴族小姐常來訂禮服，大神殿那邊會送修女聖袍的單子來，那件我縫"
        "得最仔細呢。聖女聖袍聽說最早是聖女親手繡，我這幾件照老樣子仿，可不敢"
        "說一模一樣喲。還有……咳，那套誘蠱蕾絲內衣嘛，有客人特地來問過，想看"
        "我就拿出來，不用不好意思喲。」",
    ),
    KeywordResponse(
        "收衣",
        "「穿不下的、不合身的拿回來吧，我這裡做的衣甲都收，記得先洗乾淨喲。破"
        "成布條的就算了，我也縫不回來呢。收回來的我會拆線重縫，再給下一個人穿"
        "。」",
    ),
)

# 艾蓮娜·鴉丘 — the jeweller. Slow, soft and exacting; addresses the
# visitor plainly with few particles and starts from whatever they are already wearing.
# capital_adornments is her glass case: everyday pieces, the blessed and
# hunter's work, and the two rare enchanted carry-alls.
JEWELLER_RESPONSES: tuple[KeywordResponse, ...] = (
    KeywordResponse(
        "飾品",
        "「這一櫃全是隨身戴的飾品。銀髮簪是平原的老手藝，狼牙項鍊是獸王國部族"
        "的樣式，朝聖者銅符，走聖階的信眾幾乎都戴一枚。防禦戒指鑲著一顆結晶，"
        "難得一見。身上別掛太多，挑幾件真用得上的就好。」",
    ),
    KeywordResponse(
        "鑲工",
        "「看鑲工要看爪，別看光。這枚淨化吊墜的銀用聖水反覆洗過，聽說擋得住瘴"
        "氣；無懼胸針用赤鐵打成，是獵魔人戴的東西。光輝聖徽的徽面用整塊料雕成"
        "，你摸一下邊緣就知道了。」",
    ),
    KeywordResponse(
        "奇物",
        "「儲物袋是帝國那邊的空間魔法，袋子不大，裡頭卻比看起來大得多。滑翔斗"
        "篷用蛛絲織成，從高處跳下去能托住人。這兩件都難得，價錢在櫃上的小牌子"
        "，我就不唸了。」",
    ),
    KeywordResponse(
        "收飾",
        "「舊飾件可以拿來，我櫃上有的樣式都收。缺爪、斷鏈也請先說一聲。藥師珠"
        "串、迷情絲頸環這類有點來歷，我會多問兩句從哪裡來，別介意。」",
    ),
)

# 希碧拉·灰沼 — the alchemist. Flat, orderly, asks about symptoms first and
# never oversells an effect (capital_remedies). The baptismal holy water is
# the sanctum's, up the 聖階, and she says so.
ALCHEMIST_RESPONSES: tuple[KeywordResponse, ...] = (
    KeywordResponse(
        "藥劑",
        "「治療藥水，小傷用。強效治療藥水，傷得重才用，別拿來治擦傷，浪費。魔"
        "力藥水是藍色，施法施到頭昏的時候喝。瓶標上都有寫，看不懂再問我。」",
    ),
    KeywordResponse(
        "外敷",
        "「獸王國藥草膏，部族薩滿熬成，抹在腫痛的地方。王國礦工提神湯很辣，礦"
        "工下坑前灌一碗，有沒有用，看你自己撐不撐得住。這兩樣算不上正經藥水，"
        "塞在行囊底備著就好。」",
    ),
    KeywordResponse(
        "特殊",
        "「迷情藥？有。不過我得先問，要用在誰身上，對方知道嗎？藥效不強，意志"
        "硬一點的人抵擋得住。想清楚了再來跟我說。還有，紅標那排別自己伸手拿喔"
        "。」",
    ),
    KeywordResponse(
        "聖水",
        "「受洗聖水不在我這。那是聖所的東西，爬上聖階到大神殿前，聖所有自己的"
        "櫃檯。我這裡只有調出來的藥，祝福要找神官，不歸我管。」",
    ),
)

# 尤斯汀·柯德溫 — the 商會會長, an attendant. Formal: 「閣下」 for the
# visitor, 「本人」 for himself, complete sentences. The trade of 東市 is
# coordinated from his desk, and he talks caravans, roads and tariffs as
# substance. The hall posts no work: the escort commissions its name
# anticipates have no arrangement behind them yet, so he says so plainly and
# sends work-seekers to the adventurer guild's board. The table never says
# 賣: the hall trades nothing itself.
MERCHANT_HALL_RESPONSES: tuple[KeywordResponse, ...] = (
    KeywordResponse(
        "商隊",
        "「本季出城的商隊，書記會用粉筆把隊名寫在牆上路線圖的旁邊，只記哪一隊"
        "出發、哪一隊回城。公所負責登錄與協調，不安排旁人同行，也不替任何人擔"
        "保貨物。」",
    ),
    KeywordResponse(
        "商路",
        "「王都的大宗貨物多半從東門出城，沿官道往東。東市原是舊城牆邊發展起來"
        "的貨棧街，穀物與玻璃都在這裡集散，外國的錢幣也從這裡流進城；工匠巷的"
        "鐵器走市場街，鍊金坊的藥材多從東門進城。閣下若要問路，城門的衛兵比本"
        "人清楚。」",
    ),
    KeywordResponse(
        "委託",
        "「公所的牆上沒有委託，門邊也沒有名單。商隊確實需要護衛，但這類工作目"
        "前沒有正式的安排，本人不能讓閣下去做一件沒有著落的差事。若想找事做，"
        "請到公會前的冒險者公會大廳，看他們的任務板。」",
    ),
    KeywordResponse(
        "會務",
        "「公所負責三件事，調停各行會之間的利益、評議關稅章程，以及在季底清算"
        "各家的帳目。若想入會，請帶引薦人當面來談。稅則抄在窗下那張長桌上，閣"
        "下可以自行翻閱，要抄一份也無妨。」",
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
                "櫃檯後的瑪爾特·金秤從帳簿上抬起頭，炭筆還捏在指間：「要出城，還是剛"
                "回來？出城的話，燈、羅盤、露營的東西架上都有；回來的話，帶了什麼先擱"
                "秤上。」"
            ),
            responses=GENERAL_STORE_RESPONSES,
        ),
    ),
    (
        "altoria_forge",
        DialogueDefinition(
            greeting=(
                "鍛造鋪裡砧聲沒停，維爾登·黑潭頭也沒抬：「用什麼兵器？哪隻手？說。」"
            ),
            responses=FORGE_RESPONSES,
        ),
    ),
    (
        "altoria_tailor",
        DialogueDefinition(
            greeting=(
                "裁縫坊的妮絲塔·狐溪從布堆裡探出頭，軟尺還掛在脖子上：「來，進來呀！"
                "讓我瞧一下你這身……嗯，要出遠門對吧？打算往哪裡去呢？」"
            ),
            responses=TAILOR_RESPONSES,
        ),
    ),
    (
        "altoria_jeweller",
        DialogueDefinition(
            greeting=(
                "首飾坊的艾蓮娜·鴉丘放下鹿皮布，目光先停在你的衣領上：「歡迎。你身上"
                "那件……算了，先不提。請隨意看吧，喜歡哪一件，我拿出來讓你對著光瞧。"
                "」"
            ),
            responses=JEWELLER_RESPONSES,
        ),
    ),
    (
        "altoria_alchemist",
        DialogueDefinition(
            greeting=(
                "鍊金坊的希碧拉·灰沼從一整牆瓶罐後面探出頭，指尖還沾著草綠色：「哪裡"
                "受傷了？還是先備著，以防萬一？說吧，我聽著。」"
            ),
            responses=ALCHEMIST_RESPONSES,
        ),
    ),
    (
        "altoria_merchant_hall",
        DialogueDefinition(
            greeting=(
                "商會公所的尤斯汀·柯德溫會長從稅率長桌後起身，向你略一點頭：「歡迎來"
                "到商會公所。閣下若想了解商隊、商路或公所的事務，本人樂意說明。另外請"
                "閣下先知道一件事，公所不發委託。」"
            ),
            responses=MERCHANT_HALL_RESPONSES,
        ),
    ),
)
