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
``world/lore/dialogue/altoria_lower.py`` under the same keys.

altoria-crown-and-watch adds this terrace's 衛兵駐所 off 南門 — the gates
already existed and the guardhouse behind them did not. Its captain is the
document's 衛兵隊長: an attendant whose table orients the traveller coming
through the arch, and who explicitly posts no work of his own (the document
rules a parallel bounty system out at its line 410; the guild board and
``npc:`` private commissions already carry that road).
"""

from world.lore.settlements.places import PlaceDefinition, PlaceKind
from world.lore.settlements.capability_declarations import (
    capability,
    place_bound,
)
from elosern_map_core.references import interior_room_ref

ROWS: tuple[PlaceDefinition, ...] = (
    PlaceDefinition(
        key="altoria_eatery",
        settlement_key="capital_altoria",
        kind=PlaceKind.EATERY,
        room=interior_room_ref("altoria_eatery", "altoria_eatery"),
        host_name="西格瑪‧庫柏",
        host_race="human",
        host_subrace="human_plains",
        host_sex="male",
        host_profile_key="altoria_eatery_owner",
        assortment_keys=("staple_meals",),
        components=(
            capability(
                "merchant",
                binding=place_bound("altoria_eatery"),
                service_id="altoria_eatery_owner",
                shop_key="altoria_eatery",
            ),
            capability(
                "scripted_dialogue",
                binding=place_bound("altoria_eatery"),
                dialogue_key="altoria_eatery",
            ),
        ),
    ),
    # 蘿溫‧古橡's tavern is the lane's information room: the document's
    # designated place for 招募同伴 and 打聽情報, so her table names the
    # commands that already work (talk, invite) and promises no drink
    # effect or gamble the source document leaves 〔提案〕.
    PlaceDefinition(
        key="altoria_tavern",
        settlement_key="capital_altoria",
        kind=PlaceKind.TAVERN,
        room=interior_room_ref("altoria_tavern", "altoria_tavern"),
        host_name="蘿溫‧古橡",
        host_race="human",
        host_subrace=None,
        host_sex="female",
        host_profile_key="altoria_tavern_keeper",
        assortment_keys=(),
        components=(
            capability(
                "scripted_dialogue",
                binding=place_bound("altoria_tavern"),
                dialogue_key="altoria_tavern",
            ),
        ),
    ),
    # 溫弗蕾德‧古林's inn shares the lane and its doorstep with the tavern.
    # Her rooms host rest, sleep and practice exactly as those commands
    # work anywhere else — the room is narrative, never a mechanism, and
    # the lodging fee the document marks 〔提案〕 stays un-invented.
    PlaceDefinition(
        key="altoria_lodging",
        settlement_key="capital_altoria",
        kind=PlaceKind.LODGING,
        room=interior_room_ref("altoria_lodging", "altoria_lodging"),
        host_name="溫弗蕾德‧古林",
        host_race="human",
        host_subrace=None,
        host_sex="female",
        host_profile_key="altoria_innkeeper",
        assortment_keys=(),
        components=(
            capability(
                "scripted_dialogue",
                binding=place_bound("altoria_lodging"),
                dialogue_key="altoria_lodging",
            ),
        ),
    ),
    # 伊莎貝爾‧葦沼's bathhouse is the document's contrast scene standing
    # ready: the human and beastfolk ethic of covered privacy against the
    # elven absence of shame, made visible in the room itself. No mechanic
    # (the document keeps 小幅恢復 as 〔提案〕); the keeper's job is the
    # two sides and the order between them.
    PlaceDefinition(
        key="altoria_bathhouse",
        settlement_key="capital_altoria",
        kind=PlaceKind.BATHHOUSE,
        room=interior_room_ref("altoria_bathhouse", "altoria_bathhouse"),
        host_name="伊莎貝爾‧葦沼",
        host_race="human",
        host_subrace=None,
        host_sex="female",
        host_profile_key="altoria_bathhouse_keeper",
        assortment_keys=(),
        components=(
            capability(
                "scripted_dialogue",
                binding=place_bound("altoria_bathhouse"),
                dialogue_key="altoria_bathhouse",
            ),
        ),
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
        room=interior_room_ref("altoria_guardhouse", "altoria_guardhouse"),
        host_name="托瓦德‧鄧堡",
        host_race="human",
        host_subrace=None,
        host_sex="male",
        host_profile_key="altoria_guard_captain",
        assortment_keys=(),
        components=(
            capability(
                "scripted_dialogue",
                binding=place_bound("altoria_guardhouse"),
                dialogue_key="altoria_guardhouse",
            ),
        ),
    ),
)
