"""聖潔王都 (capital_altoria) UPPER-terrace place rows (settlement-shops design §6.1).

The upper terrace is the higher ground of the noble quarter, the great temple
and the academy (docs/lore/settlement-locations.md). The sanctum change
altoria-sanctum lands this terrace's first rows: 聖潔王都光明神殿 and its
attached 聖潔王都聖所, two place records sharing the one 大神殿前 exterior
under two doorway names — worship, the sanctum's open ministry and the shop
that supplies it are one building's three counters, and the map shows that
as one square with two doors. Learning-and-exchange appends its row here
later.

altoria-crown-and-watch lands the terrace's seat of government and its two
arms: 聖潔王都王宮 off 王宮前庭 — the first real use of hostless-places, a
host-less throne approach, because a caretaker whose only line is 「the King
is not seeing anyone」 is filler a later questline would have to write around
and an empty room is honest about being the edge of what is built; the
貴族區衛所 off 貴族區前 and the 校場 off 校場外, two attendant hosts whose
tables teach commands that already work everywhere. None of the three
carries a lock: the document's 限制進入 is a story device for a questline
that does not exist yet, and a gate on an empty room is a wall, not a mystery.

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
            "The light of the 光明神殿 arrives before the room does: tall "
            "windows up the whole height of the nave, and the morning "
            "through them in bars you could lay hands on. Benches face the "
            "raised dais where the 主祭 reads, blesses and answers; the "
            "air holds a little of the day's incense. Along the near "
            "wall, the nave opens without partition or curtain into the "
            "聖所's own hall — the sanctum where the church's ministry of "
            "love is carried out, its shop counter visible from the "
            "benches. Blessing, ministry and trade are three counters of "
            "one faith, side by side in the same light; nobody in this "
            "city would think to lower their voice about any of them."
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
            "The 聖所 opens off the nave under the same roof and the same "
            "windows: warm light, clean linen, warm water ready in basins, "
            "and along one wall a shop counter fitted out like any other "
            "in the capital — shelves of ritual and comfort ware, glass "
            "bottles, folded vestments of soft cloth, priced and stocked "
            "the way a general store prices and stocks. Attendants move "
            "between the counter and the guest rooms down the hall with "
            "ledgers under their arms, calling the deacon's name in the "
            "same voice they use for blessings. Worship, ministry and "
            "trade in one building, in the open: this is how the Church "
            "of Light keeps house, and everyone on the continent knows it "
            "the way they know a tavern sells wine."
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
            "The throne approach of 聖潔王都 rises under its own roof: "
            "polished stone the colour of the cliff the capital stands on, "
            "standing columns set wide enough for a procession, and at the "
            "far end a low dais of three steps behind which the throne "
            "chair looks out over the whole length of the hall. It is "
            "grand, it is clean, and it is waiting — no guard in the "
            "doorway, no petitioner on the floor, no voice carrying down "
            "the marble. Everything this room would eventually hold, every "
            "story a palace is supposed to contain, has not been written "
            "yet, and the hall makes no attempt to pretend otherwise. "
            "Whoever walks its length will hear only their own footsteps, "
            "which is the truest account of the crown this city wears."
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
            "The 貴族區衛所 of 聖潔王都 is one long room of stacked "
            "shields and folded cloaks, a brazier at either end and a "
            "record desk by the door where arrivals would be written down "
            "if anyone still arrived needing to be. The quarter's patrol "
            "rotates through here on the hour. Nothing on the walls is an "
            "order, and nothing across the room is a barrier: whoever "
            "built the post left the floor open from door to desk, the way "
            "a house leaves its parlour door open in a season without "
            "callers."
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
            "The 校場 of 聖潔王都 is a raked dirt yard under the upper "
            "wall: practice posts set in rows, ring rope worn pale at the "
            "hand-holds, and a long bench of the kind a whole morning of "
            "forms leaves sweating. The capital's levies drill here before "
            "the guild takes its own hours in the evening, and the marks on "
            "the posts came from a hundred different hands. Nothing in the "
            "yard sharpens a blade or grades a rank by itself — it is where "
            "the city comes to do the work any ground would take, done "
            "where everyone can see the standard."
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
)
