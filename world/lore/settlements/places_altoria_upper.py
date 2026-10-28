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
``world/lore/dialogue/altoria_upper.py`` under the same keys. The 主祭's row is the
capital's first ``clergy`` host (implement-church-foundation): an attendant
blueprint plus the ChurchHost ministry capability, authored through the
``church`` venue kwarg and the ``initial_arousal`` spawn-data seed — her
service is conversation, so she authors a ``dialogue_key`` and no goods. The
聖所執事's row is a plain ``merchant`` (owner decision: ministry is the
celebrant's office alone) — she authors the ``church`` venue kwarg so the
building stays in the derived venue set, but carries no ChurchHost and no
arousal seed.
"""

from world.lore.settlements.places import PlaceDefinition, PlaceKind
from world.lore.settlements.capability_declarations import (
    capability,
    place_bound,
)
from elosern_map_core.references import interior_room_ref

ROWS: tuple[PlaceDefinition, ...] = (
    PlaceDefinition(
        key="altoria_temple",
        settlement_key="capital_altoria",
        kind=PlaceKind.TEMPLE,
        room=interior_room_ref("altoria_temple", "altoria_temple"),
        host_name="艾莉安娜‧寒水",
        host_race="human",
        host_subrace=None,
        host_sex="female",
        host_profile_key="altoria_high_priestess",
        assortment_keys=(),
        components=(
            capability(
                "scripted_dialogue",
                binding=place_bound("altoria_temple"),
                dialogue_key="altoria_temple",
            ),
            # implement-church-foundation: the venue joins the derived
            # church-place set, and the host carries the ChurchHost
            # ministry capability; the raised initial arousal is the clergy
            # spawn-data seed the sync applies at host creation (§5.3).
            capability(
                "church_host",
                binding=place_bound("altoria_temple"),
                service_id="altoria_high_priestess",
                church="light_church",
                initial_arousal="微興奮",
            ),
        ),
        church=True,
    ),
    PlaceDefinition(
        key="altoria_sanctum",
        settlement_key="capital_altoria",
        kind=PlaceKind.SANCTUM_SHOP,
        room=interior_room_ref("altoria_sanctum", "altoria_sanctum"),
        host_name="羅海西亞‧芬威克",
        host_race="human",
        host_subrace=None,
        host_sex="female",
        host_profile_key="altoria_sanctum_deacon",
        assortment_keys=("sanctum_wares",),
        components=(
            capability(
                "merchant",
                binding=place_bound("altoria_sanctum"),
                service_id="altoria_sanctum_deacon",
                shop_key="altoria_sanctum_shop",
            ),
            capability(
                "scripted_dialogue",
                binding=place_bound("altoria_sanctum"),
                dialogue_key="altoria_sanctum",
            ),
        ),
        # The sanctum itself is the church venue (the derived set reads this
        # place flag); its host stays a plain merchant by owner decision.
        church=True,
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
        room=interior_room_ref("altoria_palace", "altoria_palace"),
    ),
    # 聖潔王都貴族區衛所 — the noble quarter's watch post. The document's
    # 守門衛兵隊長 belongs to a restriction this change deliberately does not
    # ship, so the captain's table says the quarter is open and there is
    # simply nothing to petition for yet.
    PlaceDefinition(
        key="altoria_noble_watch",
        settlement_key="capital_altoria",
        kind=PlaceKind.WATCH_POST,
        room=interior_room_ref("altoria_noble_watch", "altoria_noble_watch"),
        host_name="古利安‧鷹守",
        host_race="human",
        host_subrace=None,
        host_sex="male",
        host_profile_key="altoria_noble_watch_captain",
        assortment_keys=(),
        components=(
            capability(
                "scripted_dialogue",
                binding=place_bound("altoria_noble_watch"),
                dialogue_key="altoria_noble_watch",
            ),
        ),
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
        room=interior_room_ref("altoria_drill_yard", "altoria_drill_yard"),
        host_name="伊沃‧高丘",
        host_race="human",
        host_subrace=None,
        host_sex="male",
        host_profile_key="altoria_drill_instructor",
        assortment_keys=(),
        components=(
            capability(
                "scripted_dialogue",
                binding=place_bound("altoria_drill_yard"),
                dialogue_key="altoria_drill_yard",
            ),
        ),
    ),
    # 聖潔王都王立魔法學院 — the capital's academy, off 學院前 (5,5), the
    # square the map already carries. The document's 魔法學院與圖書館 is 〔有〕
    # for 都城 and 〔無〕 for every other archetype, and the Kingdom's is
    # 薇歐蕾特‧阿爾托利亞's old school. The dean is the capital's attendant
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
        room=interior_room_ref("altoria_academy", "altoria_academy"),
        host_name="奧德溫‧薩契",
        host_race="human",
        host_subrace=None,
        host_sex="male",
        host_profile_key="altoria_academy_dean",
        assortment_keys=(),
        components=(
            capability(
                "scripted_dialogue",
                binding=place_bound("altoria_academy"),
                dialogue_key="altoria_academy",
            ),
        ),
    ),
)
