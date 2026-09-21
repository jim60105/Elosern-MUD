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
            "The eatery of 聖潔王都, steam rising from its kitchen over "
            "南大道's foot traffic (settlement-shops design §6.1)."
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
            "The 醉月酒館 of 聖潔王都 sits where the inn lane earns its "
            "name: low amber light, sawdust and hops, and a counter worn "
            "bright where a decade of travellers have leaned. Tables "
            "crowd toward the hearth, each its own conversation, and the "
            "room's one rule is the tavern keeper's — talk here, about "
            "anything, and nobody overheard is the worse for it. Word, "
            "rumour and companions are what this room trades in; the cups "
            "are scenery. Nothing on the tables does more than sit in them."
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
            "The 爐火旅店 of 聖潔王都 keeps its common room around a "
            "firebank built into the party wall it shares with the "
            "tavern, so the lane's two doors warm one long room between "
            "them. Up the stair the guest doors stand in a row, each "
            "room beyond them private: a bed, a basin, a latch that "
            "holds. This is where the city sleeps off its travel — "
            "resting, sleeping it through, or spending the quiet hours "
            "at practice — and the stairs ask nothing of anyone who "
            "uses them."
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
            "The 公共浴場 of 聖潔王都 breathes steam over the curb of "
            "浴場前 before you even reach its doors. Inside, the floor "
            "runs in two: a men's side and a women's side, each with its "
            "own deep river-water pools and its own shouting, splashing "
            "regulars, divided by a high wall the manager's voice walks "
            "the length of all day. Here the capital's human and beastfolk "
            "custom of covered privacy rules — undress is a private act, "
            "and this building is the one place it is done in the open, "
            "among strangers, behind a wall. An elf bathing with them "
            "would see nothing worth a wall; that disagreement is the "
            "bathhouse's other landmark, and 伊莎貝爾 has opinions about "
            "it she delivers on request."
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
            "The 衛兵駐所 of 聖潔王都 stands inside the 南門's shadow, "
            "one warm room against the arch's own cold passage: bench and "
            "rack along one wall, a brazier smoked black at the ceiling, "
            "and a shuttered window over the gate tunnel so the oncoming "
            "hour can be watched from the stove's side. Boots come in and "
            "out of here on the hour, and the wall charts show every road "
            "out of the city named. It is a working post, and everything a "
            "post would hang beside the charts — notices, postings, price "
            "on a head — is simply not here; work in this city walks in "
            "through the guild's door, not this one."
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
