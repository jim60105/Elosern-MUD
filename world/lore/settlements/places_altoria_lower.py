"""聖潔王都 (capital_altoria) LOWER-terrace place rows (settlement-shops design §6.1).

The lower terrace is 南門一帶最老也最擁擠的舊城區, the market belt running
along the cleared wall line — the food trade's ground (docs/lore/
settlement-locations.md). The 南大道 eatery is the capital slice's first row;
the hospitality change (altoria-hospitality) adds this terrace's tavern,
lodging and bathhouse here: the three are the capital's first places that
sell nothing — attendant hosts whose whole service is conversation, so each
authors a ``dialogue_key`` and no goods, and the lane's two (客棧巷's tavern
and inn) carry distinct doorway names over the one shared exterior.

The assembled tuple order is load-bearing (see the assembly comment in
``places.py``): this slice leads the capital's three, so its rows reach the
derived roster before the middle terrace's.

Merchant rows carry a ``dialogue_key`` beside their ``shop_key``: the merchant
blueprint answers as well as trades (merchant-dialogue), and a merchant place
without the kwarg fails load naming the place. The tables live in
``world/lore/dialogue/altoria.py`` under the same keys.

altoria-crown-and-watch adds this terrace's 衛兵駐所 off 南門 — the gates
already existed and the guardhouse behind them did not. Its captain is the
document's 衛兵隊長: an attendant whose table orients the traveller coming
through the arch, and who explicitly posts no work of his own (the document
rules a parallel bounty system out at its line 410; the guild board and
``npc:`` private commissions already carry that road).
"""

from world.lore.settlements.places import PlaceDefinition, PlaceKind

ROWS: tuple[PlaceDefinition, ...] = (
    PlaceDefinition(
        key="altoria_eatery",
        settlement_key="capital_altoria",
        kind=PlaceKind.EATERY,
        room_name_zh="聖潔王都餐館",
        room_desc_zh=(
            "聖潔王都的餐館，廚房蒸氣從門口漫出去，罩在南大道的人流上頭。"
        ),
        exterior_xy=(3, 1),  # 南大道
        doorway_key_zh="餐館",
        doorway_aliases=("eatery", "restaurant", "diner"),
        host_name="西格瑪·庫柏",
        host_title="聖潔王都餐館老闆",
        host_race="human",
        host_subrace="human_plains",
        host_sex="male",
        profession="merchant",
        service_id="altoria_eatery_owner",
        assortment_keys=("staple_meals",),
        authored_kwargs=(
            ("shop_key", "altoria_eatery"),
            ("dialogue_key", "altoria_eatery"),
        ),
    ),
    # 蘿溫·古橡's tavern is the lane's information room: the document's
    # designated place for 招募同伴 and 打聽情報, so her table names the
    # commands that already work (talk, invite) and promises no drink
    # effect or gamble the source document leaves 〔提案〕.
    PlaceDefinition(
        key="altoria_tavern",
        settlement_key="capital_altoria",
        kind=PlaceKind.TAVERN,
        room_name_zh="聖潔王都醉月酒館",
        room_desc_zh=(
            "聖潔王都的醉月酒館坐落在客棧巷得名的地方，低垂的琥珀燈色、鋸末與蛇麻的氣味，還有那條被十年倚案的旅客磨得發亮的吧台。桌子們朝壁爐擠成"
            "一堆堆各自的談話，而這間屋子唯一的規矩出自酒館老闆，在這裡什麼都可以談，被聽見的人也不會因此吃虧。消息、謠言與同伴才是這間屋子經營的"
            "東西；杯子只是佈景，桌上的東西什麼都不做，只是擱在那裡。"
        ),
        exterior_xy=(4, 1),  # 客棧巷
        doorway_key_zh="醉月酒館",
        doorway_aliases=("tavern", "drinking hall"),
        host_name="蘿溫·古橡",
        host_title="聖潔王都酒館老闆",
        host_race="human",
        host_subrace=None,
        host_sex="female",
        profession="attendant",
        service_id="altoria_tavern_keeper",
        assortment_keys=(),
        authored_kwargs=(("dialogue_key", "altoria_tavern"),),
    ),
    # 溫弗蕾德·古林's inn shares the lane and its doorstep with the tavern.
    # Her rooms host rest, sleep and practice exactly as those commands
    # work anywhere else — the room is narrative, never a mechanism, and
    # the lodging fee the document marks 〔提案〕 stays un-invented.
    PlaceDefinition(
        key="altoria_lodging",
        settlement_key="capital_altoria",
        kind=PlaceKind.LODGING,
        room_name_zh="聖潔王都爐火旅店",
        room_desc_zh=(
            "聖潔王都的爐火旅店把公共大廳圍在一道嵌牆的火塘邊，那面牆正是它與酒館共用的隔牆，巷子裡的兩扇門因此暖著同一間長屋。上了樓梯，客房的門"
            "一字排開，門後各自私密，一張床、一個臉盆、一道扣得住的門閂。這座城市在這裡把旅途睡回去，歇著、一覺到天亮，或是趁著安靜的幾個小時修煉"
            "。樓梯對每個使用它的人都不作任何要求。"
        ),
        exterior_xy=(4, 1),  # 客棧巷
        doorway_key_zh="爐火旅店",
        doorway_aliases=("inn", "lodging"),
        host_name="溫弗蕾德·古林",
        host_title="聖潔王都旅店老闆娘",
        host_race="human",
        host_subrace=None,
        host_sex="female",
        profession="attendant",
        service_id="altoria_innkeeper",
        assortment_keys=(),
        authored_kwargs=(("dialogue_key", "altoria_lodging"),),
    ),
    # 伊莎貝爾·葦沼's bathhouse is the document's contrast scene standing
    # ready: the human and beastfolk ethic of covered privacy against the
    # elven absence of shame, made visible in the room itself. No mechanic
    # (the document keeps 小幅恢復 as 〔提案〕); the keeper's job is the
    # two sides and the order between them.
    PlaceDefinition(
        key="altoria_bathhouse",
        settlement_key="capital_altoria",
        kind=PlaceKind.BATHHOUSE,
        room_name_zh="聖潔王都公共浴場",
        room_desc_zh=(
            "聖潔王都的公共浴場，人還沒走到門口，蒸氣就先漫過浴場前的路緣。屋內的地面一分為二，男側與女側，各有各深的河水池，各有各大喊大潑水的老"
            "主顧，中間隔著一道高牆，管理員的聲音整天沿著牆走來走去。在這裡作主的是王都人族與獸人遮蓋私密的習俗，寬衣是個人的事，而這棟建築是唯一"
            "讓它當眾進行的地方，在陌生人之間、隔著一堵牆。一個精靈若和他們共浴，會覺得沒什麼值得隔牆；這場分歧是浴場另一處地標，而伊莎貝爾對它很"
            "有意見，問起便說給你聽。"
        ),
        exterior_xy=(5, 1),  # 浴場前
        doorway_key_zh="公共浴場",
        doorway_aliases=("bathhouse", "baths"),
        host_name="伊莎貝爾·葦沼",
        host_title="聖潔王都公共浴場管理員",
        host_race="human",
        host_subrace=None,
        host_sex="female",
        profession="attendant",
        service_id="altoria_bathhouse_keeper",
        assortment_keys=(),
        authored_kwargs=(("dialogue_key", "altoria_bathhouse"),),
    ),
    # 聖潔王都衛兵駐所 — the guardhouse behind the south gate. The document
    # keeps its 懸賞任務板 〔提案〕 pointed at the guild board and private
    # commissions instead (line 410), so the room ships no board, the host
    # ships no issuing component, and the change's second refusal is the
    # rule that keeps it that way.
    PlaceDefinition(
        key="altoria_guardhouse",
        settlement_key="capital_altoria",
        kind=PlaceKind.WATCH_POST,
        room_name_zh="聖潔王都衛兵駐所",
        room_desc_zh=(
            "聖潔王都的衛兵駐所站在南門的陰影裡，一間溫暖的屋子對著拱門下冰冷的通道，一面牆上是長凳與兵器架，火盆把天花板燻得黝黑，一扇木窗板半開"
            "的窗俯瞰門洞，值更的人坐在爐邊就能盯著接下來的幾個小時。靴子按整點進出這裡，牆上的輿圖標出每一條出城的路。這是一個當值的場所，而一個"
            "駐所該掛在輿圖旁邊的東西，告示、公文、人頭的金價，這裡一概沒有；這座城市的工作從公會那扇門走進來，這扇門不發活。"
        ),
        exterior_xy=(3, 0),  # 南門
        doorway_key_zh="衛兵駐所",
        doorway_aliases=("guardhouse", "guard house"),
        host_name="托瓦德·鄧堡",
        host_title="聖潔王都衛兵隊隊長",
        host_race="human",
        host_subrace=None,
        host_sex="male",
        profession="attendant",
        service_id="altoria_guard_captain",
        assortment_keys=(),
        authored_kwargs=(("dialogue_key", "altoria_guardhouse"),),
    ),
)
