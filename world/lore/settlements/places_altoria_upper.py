"""聖潔王都 (capital_altoria) UPPER-terrace place rows (settlement-shops design §6.1).

The upper terrace is the higher ground of the noble quarter, the great temple
and the academy (docs/lore/settlement-locations.md). The sanctum change
altoria-sanctum lands this terrace's first rows: 聖潔王都光明神殿 and its
attached 聖潔王都聖所, two place records sharing the one 大神殿前 exterior
under two doorway names — worship, the sanctum's open ministry and the shop
that supplies it are one building's three counters, and the map shows that
as one square with two doors.

altoria-crown-and-watch lands the terrace's seat of government and its two
arms: 聖潔王都王宮 off 王宮前庭 — the first real use of hostless-places, a
host-less throne approach, because a caretaker whose only line is 「the King
is not seeing anyone」 is filler a later questline would have to write around
and an empty room is honest about being the edge of what is built; the
貴族區衛所 off 貴族區前 and the 校場 off 校場外, two attendant hosts whose
tables teach commands that already work everywhere. None of the three
carries a lock: the document's 限制進入 is a story device for a questline
that does not exist yet, and a gate on an empty room is a wall, not a mystery.

altoria-learning-and-exchange appends this terrace's academy here: 聖潔王都
王立魔法學院 off 學院前, the document's 全大陸唯二真正夠格稱作『學院』的設施
and the capital's designated lore-reveal room — the dean's table answers on
the magic-rank ladder and the element vocabulary instead of teaching a
command, because 「拜師習得新技能」 stays 〔提案〕 and this change ships no
apprenticeship mechanism.

The assembled tuple order is load-bearing (see the assembly comment in
``places.py``): this slice follows the capital's lower and middle terraces,
so its rows reach the derived roster after them and before the village's.

Merchant rows here carry a ``dialogue_key`` beside their ``shop_key``
like every other capital merchant (merchant-dialogue); the tables live in
``world/lore/dialogue/altoria.py`` under the same keys. The 主祭's row is the
capital's second ``attendant`` host — her service is conversation, so she
authors a ``dialogue_key`` and no goods.
"""

from world.lore.settlements.places import PlaceDefinition, PlaceKind

ROWS: tuple[PlaceDefinition, ...] = (
    PlaceDefinition(
        key="altoria_temple",
        settlement_key="capital_altoria",
        kind=PlaceKind.TEMPLE,
        room_name_zh="聖潔王都光明神殿",
        room_desc_zh=(
            "光明神殿的光比屋子先到，長窗沿中殿一路開到屋頂，晨光從窗格斜斜落下來，亮得幾乎可以用手捧住。長椅對著墊高的臺，主祭在那裡誦讀、祝禱、"
            "回答提問；空氣裡留著一點今日焚香的氣息。近處的牆邊，中殿沒有任何隔斷或簾幔，直接敞進聖所自己的大廳，那裡是教會行愛之工的地方，從長椅"
            "上就看得見那裡的商品櫃。祝禱、事工與買賣是同一份信仰的三座櫃檯，並排站在同一片光裡；這座城市裡沒有人會覺得提起它們其中任何一樣時該壓"
            "低聲音。"
        ),
        exterior_xy=(4, 4),  # 大神殿前
        doorway_key_zh="光明神殿",
        doorway_aliases=("temple", "cathedral", "church"),
        host_name="艾莉安娜·寒水",
        host_title="聖潔王都光明神殿主祭",
        host_race="human",
        host_subrace=None,
        host_sex="female",
        profession="attendant",
        service_id="altoria_high_priestess",
        assortment_keys=(),
        authored_kwargs=(("dialogue_key", "altoria_temple"),),
    ),
    PlaceDefinition(
        key="altoria_sanctum",
        settlement_key="capital_altoria",
        kind=PlaceKind.SANCTUM_SHOP,
        room_name_zh="聖潔王都聖所",
        room_desc_zh=(
            "聖所開在中殿旁邊，同一個屋簷、同一排窗，暖的光、洗淨的亞麻布、臉盆裡備好的溫水，一面牆邊是一張和城裡任何店面沒有兩樣的商品櫃，禮儀與"
            "安養器物的層架、玻璃瓶、軟布祭袍摺得整整齊齊，標價與補貨的方式跟雜貨店一模一樣。執事們手臂下夾著賬簿，在櫃檯與廊底客房之間來回，喊執"
            "事名字的聲調跟喊祝禱時完全一樣。敬拜、事工、買賣在同一棟屋簷下、毫不避人，光明教會就是這樣過日子，這整個大陸都知道，就像大家都知道"
            "酒館賣酒。"
        ),
        exterior_xy=(4, 4),  # 大神殿前
        doorway_key_zh="聖所",
        doorway_aliases=("sanctum", "church sanctum"),
        host_name="羅海西亞·芬威克",
        host_title="聖潔王都聖所執事",
        host_race="human",
        host_subrace=None,
        host_sex="female",
        profession="merchant",
        service_id="altoria_sanctum_deacon",
        assortment_keys=("sanctum_wares",),
        authored_kwargs=(
            ("shop_key", "altoria_sanctum_shop"),
            ("dialogue_key", "altoria_sanctum"),
        ),
    ),
    # 聖潔王都王宮 — the palace, host-less by decision (altoria-crown-and-watch
    # design: the emptiness is the content). The document's 貴族區 value is
    # 劇情門檻, a stage for events nobody has written; a caretaker would make
    # the room look finished. No host fields, no profession, no service id,
    # no goods, no component kwargs — hostless-places' all-or-nothing rule is
    # exactly this shape, and the row still syncs as a complete tagged
    # interior with both doorways.
    PlaceDefinition(
        key="altoria_palace",
        settlement_key="capital_altoria",
        kind=PlaceKind.PALACE,
        room_name_zh="聖潔王都王宮",
        room_desc_zh=(
            "聖潔王都的王座通道在自己屋簷下升起，磨亮的石材正是這座王都立足的崖壁顏色，立柱之間的寬度夠得過一支儀仗，最遠端是三級臺的矮臺，王椅在"
            "臺後俯瞰整座大殿的全長。它宏偉、潔淨，而且正在等待，門口沒有衛兵，地上沒有跪求的人，沒有任何聲音在大理石上迴盪。這間屋子遲早要裝進的"
            "東西、一座王宮該有的每個故事，都還沒有被寫出來，大殿也懶得假裝不是這樣。沿著它走完一趟的人會聽見的唯一聲音是自己的腳步，那才是這座城"
            "市頭上這頂王冠最忠實的描述。"
        ),
        exterior_xy=(4, 6),  # 王宮前庭
        doorway_key_zh="王宮",
        doorway_aliases=("palace", "royal palace"),
    ),
    # 聖潔王都貴族區衛所 — the noble quarter's watch post. The document's
    # 守門衛兵隊長 belongs to a restriction this change deliberately does not
    # ship, so the captain's table says the quarter is open and there is
    # simply nothing to petition for yet.
    PlaceDefinition(
        key="altoria_noble_watch",
        settlement_key="capital_altoria",
        kind=PlaceKind.WATCH_POST,
        room_name_zh="聖潔王都貴族區衛所",
        room_desc_zh=(
            "聖潔王都的貴族區衛所是一間縱長的屋子，堆著盾牌、疊著斗篷，兩頭各一座火盆，門邊一張登記桌，要是還有什麼人到訪需要登記，就會被寫在這張"
            "桌上。街區的巡邏按整點輪過這裡。牆上沒有任何一張是命令，屋裡也沒有任何一樣東西會阻擋人，當初蓋這駐所的人把地面從門到桌留空，像一戶"
            "沒有訪客的人家把客廳的門敞著。"
        ),
        exterior_xy=(3, 5),  # 貴族區前
        doorway_key_zh="貴族區衛所",
        doorway_aliases=("noble watch", "watch post"),
        host_name="古利安·鷹守",
        host_title="聖潔王都貴族區衛隊長",
        host_race="human",
        host_subrace=None,
        host_sex="male",
        profession="attendant",
        service_id="altoria_noble_watch_captain",
        assortment_keys=(),
        authored_kwargs=(("dialogue_key", "altoria_noble_watch"),),
    ),
    # 聖潔王都校場 — the document's 訓練場 landed as an attendant place: the
    # instructor teaches with dialogue only, because rest plus practice and
    # guild exam already work wherever the player stands and the yard adds
    # no mechanism (design: his value is the same discoverability the
    # innkeeper's table carries).
    PlaceDefinition(
        key="altoria_drill_yard",
        settlement_key="capital_altoria",
        kind=PlaceKind.TRAINING_GROUND,
        room_name_zh="聖潔王都校場",
        room_desc_zh=(
            "聖潔王都的校場是上城牆下一片耙平的泥地，練習樁一排排立著，圍繩的握處磨得發白，一條長凳，是那種一整個上午的招式練下來會讓人一身汗的長"
            "凳。王都的徵兵在白天於此操練，公會到傍晚才來用屬於它的時段，樁上的痕跡來自一百雙不同的手。場子裡沒有任何東西會自己磨快一刀或評定一階"
            "，它是這座城市來做「任何地面都肯承接的那種功課」的地方，只因為在這裡，每個人都看得見標準在哪裡。"
        ),
        exterior_xy=(2, 4),  # 校場外
        doorway_key_zh="校場",
        doorway_aliases=("drill yard", "training ground"),
        host_name="伊沃·高丘",
        host_title="聖潔王都訓練場教頭",
        host_race="human",
        host_subrace=None,
        host_sex="male",
        profession="attendant",
        service_id="altoria_drill_instructor",
        assortment_keys=(),
        authored_kwargs=(("dialogue_key", "altoria_drill_yard"),),
    ),
    # 聖潔王都王立魔法學院 — the capital's academy, off 學院前 (5,5), the
    # square the map already carries. The document's 魔法學院與圖書館 is 〔有〕
    # for 都城 and 〔無〕 for every other archetype, and the Kingdom's is
    # 薇歐蕾特·阿爾托利亞's old school. The dean is the capital's attendant
    # whose table carries subject matter instead of a command lesson: the
    # magic-rank ladder and the element vocabulary, the two closed lore
    # vocabularies the document names as this room's natural reveal site
    # (docs/lore/settlement-locations.md line 453). He grants nothing — the
    # 〔提案〕 「拜師習得新技能」 at line 454 stays the lineage tree's, and
    # this row ships no apprenticeship surface beside the room.
    PlaceDefinition(
        key="altoria_academy",
        settlement_key="capital_altoria",
        kind=PlaceKind.ACADEMY,
        room_name_zh="聖潔王都王立魔法學院",
        room_desc_zh=(
            "聖潔王都的學院把講課收在同一個屋簷下，一間長廳，階梯式的長椅面對著示範場，無論幾點都燈光明亮到能讀書，廳旁是一間書庫，王都藏的階級課"
            "本照學生攀登的順序上架。學生在門外的階梯上爭論，裡面的講師回答問題的方式正是一所學校該有的樣子，一路答到底。院長的書桌正對著示範場；"
            "這座城市懂得的每一條魔法階級階梯與八元素的知識，都出自像這樣某個地方，而王國的這一間，正是薇歐蕾特·阿爾托利亞從前坐過的教"
            "室。"
        ),
        exterior_xy=(5, 5),  # 學院前
        doorway_key_zh="王立魔法學院",
        doorway_aliases=("academy", "royal academy", "magic academy"),
        host_name="奧德溫·薩契",
        host_title="聖潔王都魔法學院院長",
        host_race="human",
        host_subrace=None,
        host_sex="male",
        profession="attendant",
        service_id="altoria_academy_dean",
        assortment_keys=(),
        authored_kwargs=(("dialogue_key", "altoria_academy"),),
    ),
)
