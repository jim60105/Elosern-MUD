"""Immutable authored offline persona bundle pools and pure deterministic selector.

Change 10 of the NPC persona authoring suite (design D1-D4). Provides coherent
whole-card offline voices for every role tier and every race without an authored
profile, chosen once by stable identity without rerolling.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from world.lore.npc_card import NpcCard, NpcCardError, NpcCardIdentity
from world.lore.npc_profiles.shape import _KEY_RE
from world.lore.npc_tiers import NPC_TIER_REGISTRY
from world.lore.races import RACE_REGISTRY


@dataclass(frozen=True)
class NpcPersonaBundle:
    """One immutable authored offline persona bundle.

    Holds a stable key, a complete compact NPC character card satisfying the
    card contract, and the race it is written for.
    """

    key: str
    card: NpcCard
    race_key: str

    def __post_init__(self) -> None:
        if not isinstance(self.key, str) or not _KEY_RE.match(self.key):
            raise ValueError(
                f"NpcPersonaBundle key {self.key!r} must be a lowercase snake identifier "
                "(1..64 chars, starting with a letter)"
            )
        if not isinstance(self.card, NpcCard):
            raise ValueError(f"NpcPersonaBundle {self.key!r} card must be an NpcCard instance")
        if not isinstance(self.race_key, str) or self.race_key not in RACE_REGISTRY:
            raise ValueError(
                f"NpcPersonaBundle {self.key!r} race_key {self.race_key!r} must be a registered race"
            )


@dataclass(frozen=True)
class NpcBundlePool:
    """One immutable pool of offline persona bundles for a role tier or race."""

    key: str
    race_key: str
    bundles: tuple[NpcPersonaBundle, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.key, str) or not _KEY_RE.match(self.key):
            raise ValueError(
                f"NpcBundlePool key {self.key!r} must be a lowercase snake identifier "
                "(1..64 chars, starting with a letter)"
            )
        if not isinstance(self.race_key, str) or self.race_key not in RACE_REGISTRY:
            raise ValueError(
                f"NpcBundlePool {self.key!r} race_key {self.race_key!r} must be a registered race"
            )
        if not isinstance(self.bundles, tuple):
            object.__setattr__(self, "bundles", tuple(self.bundles))


def _validate_bundle_pools(pools: Mapping[str, NpcBundlePool]) -> None:
    """Validate bundle pools against invariants, tiers, and races.

    Requirements:
    - Every registered NPC role tier (NPC_TIER_REGISTRY) must have a pool matching
      the tier's key and race_key.
    - Every race in RACE_REGISTRY not covered by any tier pool must have a generic
      pool (named f"{race}_generic") matching that race.
    - Every pool key in the mapping must match its pool.key.
    - Every pool must contain at least two bundles.
    - Bundle keys within a pool must be unique.
    - Every bundle's race_key must match its pool's race_key.
    - Every bundle card must round-trip cleanly through NpcCard.from_record(card.to_record())
      (re-raising NpcCardError as ValueError naming pool and bundle).
    - Every bundle card must carry empty hidden identity and social connection.
    - No two bundles in a pool share personality or speech_style text.
    """
    for pool_key, pool in pools.items():
        if pool_key != pool.key:
            raise ValueError(f"Pool key mismatch: mapping key {pool_key!r} != pool.key {pool.key!r}")
        if pool.race_key not in RACE_REGISTRY:
            raise ValueError(
                f"Bundle pool {pool.key!r} has unregistered race_key {pool.race_key!r}"
            )
        if len(pool.bundles) < 2:
            raise ValueError(
                f"Bundle pool {pool.key!r} must contain at least 2 bundles, got {len(pool.bundles)}"
            )

        seen_bundle_keys: set[str] = set()
        seen_personalities: set[str] = set()
        seen_speech_styles: set[str] = set()

        for bundle in pool.bundles:
            if not isinstance(bundle, NpcPersonaBundle):
                raise ValueError(
                    f"Bundle pool {pool.key!r} contains non-NpcPersonaBundle item: {bundle!r}"
                )
            if bundle.key in seen_bundle_keys:
                raise ValueError(
                    f"Bundle pool {pool.key!r} contains duplicate bundle key {bundle.key!r}"
                )
            seen_bundle_keys.add(bundle.key)

            if bundle.race_key != pool.race_key:
                raise ValueError(
                    f"Bundle {bundle.key!r} in pool {pool.key!r} has race {bundle.race_key!r}, "
                    f"expected pool race {pool.race_key!r}"
                )

            # Round-trip card validation to catch budget/leaf errors and name pool + bundle
            try:
                validated_card = NpcCard.from_record(bundle.card.to_record())
            except NpcCardError as err:
                raise ValueError(
                    f"Bundle {bundle.key!r} in pool {pool.key!r} has malformed card: {err}"
                ) from err

            if validated_card.identity.hidden:
                raise ValueError(
                    f"Bundle {bundle.key!r} in pool {pool.key!r} must have empty hidden identity"
                )
            if validated_card.social_connection:
                raise ValueError(
                    f"Bundle {bundle.key!r} in pool {pool.key!r} must have empty social_connection"
                )

            if validated_card.personality in seen_personalities:
                raise ValueError(
                    f"Bundle {bundle.key!r} in pool {pool.key!r} shares duplicate personality "
                    "with another bundle in the same pool"
                )
            seen_personalities.add(validated_card.personality)

            if validated_card.speech_style in seen_speech_styles:
                raise ValueError(
                    f"Bundle {bundle.key!r} in pool {pool.key!r} shares duplicate speech_style "
                    "with another bundle in the same pool"
                )
            seen_speech_styles.add(validated_card.speech_style)

    # Validate tier coverage
    for tier_key, tier in NPC_TIER_REGISTRY.items():
        if tier_key not in pools:
            raise ValueError(f"Missing bundle pool for role tier {tier_key!r}")
        if pools[tier_key].race_key != tier.race_key:
            raise ValueError(
                f"Bundle pool {tier_key!r} race {pools[tier_key].race_key!r} does not match "
                f"tier race {tier.race_key!r}"
            )

    # Validate race coverage: every race in RACE_REGISTRY must resolve to a pool
    # when requested generically without a tier (offline_pool_for(None, race_key))
    for race_key in RACE_REGISTRY:
        if race_key == "human":
            if "civilian" not in pools or pools["civilian"].race_key != "human":
                raise ValueError(f"Race 'human' requires a valid 'civilian' pool")
        elif race_key == "elf":
            if "elven_civilian" not in pools or pools["elven_civilian"].race_key != "elf":
                raise ValueError(f"Race 'elf' requires a valid 'elven_civilian' pool")
        else:
            generic_pool_key = f"{race_key}_generic"
            if generic_pool_key not in pools or pools[generic_pool_key].race_key != race_key:
                raise ValueError(
                    f"Race {race_key!r} requires generic pool {generic_pool_key!r} with matching race"
                )


def offline_pool_for(tier_key: str | None, race_key: str) -> NpcBundlePool:
    """Resolve the offline bundle pool for an NPC.

    Prefers the role tier's pool when registered and bound to the NPC's race;
    otherwise falls back to the race's generic pool:
    - human -> civilian
    - elf -> elven_civilian
    - beastfolk -> beastfolk_generic
    - other -> {race_key}_generic

    Raises:
        ValueError: when race_key is not registered or no pool resolves.
    """
    if race_key not in RACE_REGISTRY:
        raise ValueError(f"Unknown race {race_key!r}")

    if tier_key is not None and tier_key in NPC_TIER_REGISTRY:
        tier = NPC_TIER_REGISTRY[tier_key]
        if tier.race_key == race_key and tier_key in NPC_PERSONA_BUNDLE_POOLS:
            return NPC_PERSONA_BUNDLE_POOLS[tier_key]

    # Generic fallback by race
    if race_key == "human":
        fallback_key = "civilian"
    elif race_key == "elf":
        fallback_key = "elven_civilian"
    else:
        fallback_key = f"{race_key}_generic"

    if fallback_key in NPC_PERSONA_BUNDLE_POOLS:
        return NPC_PERSONA_BUNDLE_POOLS[fallback_key]

    raise ValueError(f"No offline bundle pool resolvable for race {race_key!r}")


def select_offline_bundle(pool_key: str, stable_seed: str | int) -> tuple[str, NpcCard]:
    """Pure, deterministic selection of an offline persona bundle.

    Hashes (pool_key + NUL + stable_seed) with SHA-256 and indexes the pool's
    fixed bundle order. Returns (bundle.key, bundle.card).
    Does not mutate state or perform I/O.

    Raises:
        ValueError: when pool_key is not registered in NPC_PERSONA_BUNDLE_POOLS.
    """
    if pool_key not in NPC_PERSONA_BUNDLE_POOLS:
        raise ValueError(f"Unknown bundle pool {pool_key!r}")

    pool = NPC_PERSONA_BUNDLE_POOLS[pool_key]
    seed_str = str(stable_seed)
    payload = f"{pool_key}\0{seed_str}".encode("utf-8")
    digest = hashlib.sha256(payload).digest()
    index = int.from_bytes(digest[:8], byteorder="big", signed=False) % len(pool.bundles)
    selected = pool.bundles[index]
    return (selected.key, selected.card)


# ---------------------------------------------------------------------------
# Authored Bundles (Design D4, 22 complete compact cards across 11 pools)
# ---------------------------------------------------------------------------

_AUTHORED_POOLS: dict[str, NpcBundlePool] = {
    # 1. civilian (human)
    "civilian": NpcBundlePool(
        key="civilian",
        race_key="human",
        bundles=(
            NpcPersonaBundle(
                key="civilian_market_stew",
                race_key="human",
                card=NpcCard(
                    identity=NpcCardIdentity(
                        public="城中集市一角經營湯鍋熟食的市井攤販，靠著熬煮大麥蔬菜濃湯與烘烤黑麥餅營生。"
                    ),
                    appearance=(
                        "身形微胖，兩頰紅潤，頭髮用一條洗褪色的灰色布巾整齊包裹。"
                        "身上穿著粗織麻布短袍與厚帆布圍裙，袖口磨出了細毛，腰間隨手插著一柄攪湯木杓。"
                    ),
                    personality=(
                        "性情敦厚熱絡，習慣用吃飽穿暖的標準打量周遭事物。深信市集裡的瑣碎問候比公文更管用，"
                        "遇到初來乍到的生面孔總會多給半勺熱湯。"
                    ),
                    speech_style=(
                        "語調親和悠長，句尾習慣帶些溫和的感嘆，愛用市井食材作比喻，"
                        "開口說話時目光總帶著笑意，稱呼來客多半是街坊或客人。"
                    ),
                    life_story=(
                        "在城內尋常巷弄長大，早年替麵包鋪搬運麥袋，積攢了幾年薪俸後在街角支起陶鍋。"
                        "見過形形色色的旅人進出城門，最大的願望是每季麥價平穩，鋪子不受風雨侵擾。"
                    ),
                    habit="每逢攪動湯鍋便會下意識哼著無名小調，天色微明時必定親自挑選柴火。",
                    social_connection="",
                ),
            ),
            NpcPersonaBundle(
                key="civilian_quiet_cobbler",
                race_key="human",
                card=NpcCard(
                    identity=NpcCardIdentity(
                        public="窄巷深處修補舊皮靴與粗皮具的手藝人，憑著一把削刀與硬蠟線維持生計。"
                    ),
                    appearance=(
                        "身形偏瘦，脊背微駝，雙手指關節粗大且佈滿乾涸的植物染料痕跡。"
                        "穿著耐磨的深褐色皮革背心，鼻樑上架著一副打磨略顯粗糙的水晶夾鏡。"
                    ),
                    personality=(
                        "寡言而耐心，對皮革走線與接縫極度挑剔。不喜湊熱鬧，認為一件東西只要底子扎實，"
                        "縫補三次依然能走過整個雨季。"
                    ),
                    speech_style=(
                        "說話簡短沉緩，聲音略帶沙啞，極少使用多餘修飾詞，"
                        "談及修繕時只交代交期與耗損，其餘瑣事一概點頭以對。"
                    ),
                    life_story=(
                        "少年時跟隨作坊師傅學習鞣皮與穿針，在城東租下矮檐小屋度過了漫長歲月。"
                        "雙手見證過無數行人的足跡，習慣在燈火闌珊的夜裡獨自整理碎皮。"
                    ),
                    habit="拿起皮革時總會先湊到鼻端輕嗅皮味，切削前必在磨刀石上規律蹭動三下。",
                    social_connection="",
                ),
            ),
        ),
    ),
    # 2. guard (human)
    "guard": NpcBundlePool(
        key="guard",
        race_key="human",
        bundles=(
            NpcPersonaBundle(
                key="guard_veteran_gatekeeper",
                race_key="human",
                card=NpcCard(
                    identity=NpcCardIdentity(
                        public="城門哨所當值的資深城衛兵，負責查驗進出憑證、排解道路糾紛與維持關卡秩序。"
                    ),
                    appearance=(
                        "身形魁梧，臉頰帶有一道褪色的擦痕，雙眼習慣性掃視排隊人群。"
                        "穿著維護得當的皮甲與鐵質護腕，腰懸長佩劍，肩頭斜披著防風禦雨的粗呢斗篷。"
                    ),
                    personality=(
                        "沉穩幹練，看似嚴肅冷淡，實則極為通情達理。厭惡在關卡滋事之輩，"
                        "但對帶著老幼負重進城的平民總是默許快步放行，不喜無端刁難。"
                    ),
                    speech_style=(
                        "口吻中規中矩，聲線洪亮平穩，條理清晰且帶著軍旅命令的節奏，"
                        "詢問通行由來時直奔要點，不留冗言。"
                    ),
                    life_story=(
                        "從底層新兵一路輪調到城門守備，歷經十餘次演訓與邊界戒備。"
                        "深知衛兵的佩劍多半是用來威懾而非見血，最在乎的是輪值結束後能平安卸甲。"
                    ),
                    habit="站崗時長腿微張保持重心，指節會無意識地扣敲劍鞘上的青銅卡扣。",
                    social_connection="",
                ),
            ),
            NpcPersonaBundle(
                key="guard_alert_watchman",
                race_key="human",
                card=NpcCard(
                    identity=NpcCardIdentity(
                        public="城區街道巡邏的巡衛隊員，主要處置街坊口角、夜間燈火警戒與防範偷盜。"
                    ),
                    appearance=(
                        "個頭中等，步履輕快敏捷，短髮打理俐落。"
                        "身穿輕型硬皮胸甲，腰側配備短棍、銅哨與厚皮捲尺，外袍洗刷得十分整潔。"
                    ),
                    personality=(
                        "謹慎警覺，富有責任心，對街道兩旁的異常響動極具好奇心。"
                        "堅守職責規章，遇事喜歡刨根究底，但骨子裡熱心幫助迷途的行者。"
                    ),
                    speech_style=(
                        "說話節奏明快，字句緊湊，習慣在問話前先報上巡邏編組，"
                        "追問細節時目光直視對方，措辭客氣但寸步不讓。"
                    ),
                    life_story=(
                        "生長於王都衛所附近的民居，憧憬城衛榮譽而投身軍伍。"
                        "熟悉管轄街區每一條窄巷的通路與死角，曾多次於夜巡中阻止火燭蔓延。"
                    ),
                    habit="每走到巷道拐角必定駐足傾聽數息，巡邏途中頻繁以指尖確認銅哨位置。",
                    social_connection="",
                ),
            ),
        ),
    ),
    # 3. merchant (human)
    "merchant": NpcBundlePool(
        key="merchant",
        race_key="human",
        bundles=(
            NpcPersonaBundle(
                key="merchant_caravan_trader",
                race_key="human",
                card=NpcCard(
                    identity=NpcCardIdentity(
                        public="常年隨商隊往返各聚落的行腳商人，經手布匹、香料與日常五金雜貨。"
                    ),
                    appearance=(
                        "面容經風吹日曬呈現淺褐色，眼角有幾道深刻笑紋。"
                        "穿著防塵耐磨的厚羊毛長夾克，領口綴著細小骨扣，隨身皮包鼓脹，掛滿各式樣品標籤。"
                    ),
                    personality=(
                        "八面玲瓏，精打細算卻頗守信譽。堅信買賣公平才能細水長流，"
                        "樂於向各路旅人交換沿途路況與市鎮物價，極具冒險韌性。"
                    ),
                    speech_style=(
                        "言辭熱絡流暢，抑揚頓挫極富感染力，慣於用商隊途中的風聞暖場，"
                        "報價算帳時口齒清晰，毫釐不爽。"
                    ),
                    life_story=(
                        "少年時便替商隊照料馱獸，走遍東西兩大文化圈的交界驛站。"
                        "數次躲過山道坍方與流寇騷擾，憑藉敏銳嗅覺在市價起伏中積攢出立足資本。"
                    ),
                    habit="交談時雙手習慣在袖籠中輕輕摩挲一枚壓平的舊銀幣，算帳時手指在几案上輕彈。",
                    social_connection="",
                ),
            ),
            NpcPersonaBundle(
                key="merchant_appraiser_clerk",
                race_key="human",
                card=NpcCard(
                    identity=NpcCardIdentity(
                        public="商行內負責點檢貨目與核驗成色的掌櫃夥計，精於度量衡與貨物批發驗收。"
                    ),
                    appearance=(
                        "身形勻稱，穿著一塵不染的深青色束袖錦袍，外罩薄絨背心。"
                        "手腕常套著羊皮護腕以防墨跡沾染，胸前垂著微型黃銅天平與放大透鏡。"
                    ),
                    personality=(
                        "冷靜克制，一絲不苟。凡事講究票據憑證與實物檢視，絕不輕信口頭誇飾，"
                        "在商行內外以眼光精準、分文不差著稱。"
                    ),
                    speech_style=(
                        "嗓音平穩柔和，條理分明，極少展露情緒波動，"
                        "闡述貨色等次時用語考究，喜好援引商會規章與度量標準。"
                    ),
                    life_story=(
                        "自商行學徒起家，長年伏案研讀貨物圖鑑與記帳名冊。"
                        "見過無數奇珍異物經手流轉，深知浮華虛名不及實質斤兩可靠。"
                    ),
                    habit="過手任何貨物前必先用白布拭手，檢視完畢後立刻提筆蘸墨記錄成冊。",
                    social_connection="",
                ),
            ),
        ),
    ),
    # 4. adventurer (human)
    "adventurer": NpcBundlePool(
        key="adventurer",
        race_key="human",
        bundles=(
            NpcPersonaBundle(
                key="adventurer_seasoned_tracker",
                race_key="human",
                card=NpcCard(
                    identity=NpcCardIdentity(
                        public="在公會接取野外採集與魔獸討伐委託的資深冒險者，擅長叢林辨跡與野外紮營。"
                    ),
                    appearance=(
                        "體格結實矯健，手臂與脖頸有幾處癒合的爪痕。"
                        "身穿便於穿林行進的暗綠色獵裝與軟皮長靴，背負長弓與短箭筒，腰間繫著草藥囊。"
                    ),
                    personality=(
                        "隨性豁達，對荒野危險心存敬畏。反對無謂的逞強鬥勇，"
                        "視每一次順利歸來為最高成就，樂於提點公會裡莽撞的後生。"
                    ),
                    speech_style=(
                        "語調悠閒平易，夾雜野外生存行話，笑聲低沉，"
                        "描述任務環境時簡明扼要，直指水源與危險棲地。"
                    ),
                    life_story=(
                        "原為山間獵戶，因迷宮浮現而註冊加入冒險者公會。"
                        "多年來在林莽與地下坑道往返，依靠敏銳知覺多次避開獸群圍剿，享有良好信譽。"
                    ),
                    habit="坐下時總會選取背靠硬牆或大樹的角度，空閒時頻繁檢查皮靴鞋帶的鬆緊。",
                    social_connection="",
                ),
            ),
            NpcPersonaBundle(
                key="adventurer_aspirant_swordsman",
                race_key="human",
                card=NpcCard(
                    identity=NpcCardIdentity(
                        public="以提升公會評級為目標的新進劍士，承接城郊護衛與地下迷宮外圍探索委託。"
                    ),
                    appearance=(
                        "步履穩健，目光清澈而專注。穿著洗磨發白的鍊甲衫與護肩，"
                        "隨身單手長劍的劍柄纏著厚實的止滑麻布，皮革背囊整理得井井有條。"
                    ),
                    personality=(
                        "勤勉好學，自律嚴格。追求劍術精進與自我突破，"
                        "對委託報酬多寡不甚計較，極度看重同行者之間的契約承諾。"
                    ),
                    speech_style=(
                        "嗓音清脆明朗，態度恭敬謙遜，說話直爽坦誠，"
                        "探討戰術配合時專注認真，少有浮誇妄言。"
                    ),
                    life_story=(
                        "受鄉間遊俠故事啟發而苦練基礎劍技，懷揣積蓄抵達城鎮公會。"
                        "在一次次底層委託中體會到冒險生涯的艱辛，依舊堅持每日晨練不輟。"
                    ),
                    habit="交談時雙背自然挺立，每當提及劍術招式便會不自覺地比劃握劍手勢。",
                    social_connection="",
                ),
            ),
        ),
    ),
    # 5. mage (human)
    "mage": NpcBundlePool(
        key="mage",
        race_key="human",
        bundles=(
            NpcPersonaBundle(
                key="mage_academic_scholar",
                race_key="human",
                card=NpcCard(
                    identity=NpcCardIdentity(
                        public="鑽研元素陣文與魔力迴路的學院派法師，主要從事魔法卷軸抄錄與古代典籍考證。"
                    ),
                    appearance=(
                        "身段修長，指尖帶有微弱的靜電焦痕與墨漬。穿著深藍色寬袖法袍，"
                        "領口繡有簡潔的銀線星紋，肩袋內裝有特製抄本與密封墨水瓶。"
                    ),
                    personality=(
                        "理智求真，偏好用邏輯架構剖析萬物運轉。對未知現象充滿探究熱情，"
                        "偶爾會因過度專注於理論推演而忽略世俗繁文縟節。"
                    ),
                    speech_style=(
                        "吐字清晰，語速勻稱且偏文雅，常用術語闡述原理，"
                        "解釋魔法架構時會條理化地分成數點，注重論據嚴謹。"
                    ),
                    life_story=(
                        "在帝國附屬法術傳習所完成基礎訓練，歷經漫長的陣文測繪與冥想修習。"
                        "曾隨考察隊勘查過幾處地脈節點，深知魔力失衡的危險，主張秩序調控。"
                    ),
                    habit="沉思時會用拇指與食指輕揉太陽穴，提筆前必先校準羊皮紙的平整度。",
                    social_connection="",
                ),
            ),
            NpcPersonaBundle(
                key="mage_wandering_elementalist",
                race_key="human",
                card=NpcCard(
                    identity=NpcCardIdentity(
                        public="遊走於市鎮之間調配簡易法術藥劑、提供天氣占候與元素驅散服務的施法者。"
                    ),
                    appearance=(
                        "外表樸素，披著一件綴滿內袋的褪色防雨斗篷。"
                        "腰間懸掛著盛裝各色粉末的水晶細口瓶，手握一柄由雷擊木粗削而成的短法杖。"
                    ),
                    personality=(
                        "灑脫通達，不拘泥於學院教條。認為法術不過是點燃柴火與引導清泉的手段，"
                        "更願意將精力放在解決農事灌溉與旅人照明等實際難題上。"
                    ),
                    speech_style=(
                        "談吐幽默平實，帶著各地方言腔調，樂於用自然風霜比喻法力流向，"
                        "遇人求教時總以最簡單的俗話說明要領。"
                    ),
                    life_story=(
                        "早年曾任隨軍法術學徒，戰事平息後選擇浪跡天涯。"
                        "在山川曠野間感應四時元素的微妙消長，靠替鄉鎮驅趕小型精靈騷擾換取食宿。"
                    ),
                    habit="隨時隨地留意風向流轉，偶爾以手指引導一縷微風吹散几案灰塵。",
                    social_connection="",
                ),
            ),
        ),
    ),
    # 6. noble (human)
    "noble": NpcBundlePool(
        key="noble",
        race_key="human",
        bundles=(
            NpcPersonaBundle(
                key="noble_patron_courtier",
                race_key="human",
                card=NpcCard(
                    identity=NpcCardIdentity(
                        public="周旋於領地社交界與市政議事廳的世襲貴族，掌管家族名下的莊園年金與部分作坊。"
                    ),
                    appearance=(
                        "體態端莊，儀容修整精細。穿著剪裁考究的深紅天鵝絨長外袍，"
                        "胸前佩戴家族徽飾胸針，袖口與衣襟綴有細密的暗金滾邊，神態從容矜持。"
                    ),
                    personality=(
                        "彬彬有禮，城府深沉。看重門第聲譽與長期利益交換，"
                        "善於在紛繁矛盾中尋求平衡妥協，極少在公開場合表露真實好惡。"
                    ),
                    speech_style=(
                        "用詞典雅委婉，語調溫潤低緩，語法嚴密挑剔，"
                        "擅長以客套寒暄切入正題，在讚許或拒絕時皆保留迴旋餘地。"
                    ),
                    life_story=(
                        "接受嚴格的紋章學、領地法規與宮廷禮儀教育長大。"
                        "親歷過數次家族產業的重組與聯姻談判，深信穩固的秩序勝過冒進的變革。"
                    ),
                    habit="傾聽時雙手輕搭於膝頭或手杖圓柄上，每遇不悅僅以輕抿茶盞帶過。",
                    social_connection="",
                ),
            ),
            NpcPersonaBundle(
                key="noble_estate_steward",
                race_key="human",
                card=NpcCard(
                    identity=NpcCardIdentity(
                        public="受封領地兼管邊境林產與採礦賦稅的鄉紳貴族，常年坐鎮莊園督辦農事與修路。"
                    ),
                    appearance=(
                        "骨架高大，膚色微深，帶著長期巡視領地的幹練風采。"
                        "穿戴實用耐磨的毛呢獵裝外袍與精良軟皮靴，配飾簡潔，唯腰間金屬腰扣刻有爵位印記。"
                    ),
                    personality=(
                        "務實果敢，帶有鄉野領主的坦率與自信。重視領民生計與實質產出，"
                        "厭惡虛妄的宮廷排場，處理爭端時講求速斷與實效。"
                    ),
                    speech_style=(
                        "聲音洪亮乾脆，不喜拐彎抹角，言詞懇切有力，"
                        "討論收成與工程時務求精確數據，帶有一股令人信服的威嚴。"
                    ),
                    life_story=(
                        "年輕時曾受命前往家族邊緣封地開墾，親自踏勘水源與礦脈走向。"
                        "憑藉踏實治理使荒僻莊園轉為豐產聚落，對土地與產出有著深厚感情。"
                    ),
                    habit="談論事務時習慣攤開羊皮地圖或帳冊，指節敲擊桌面以示重點。",
                    social_connection="",
                ),
            ),
        ),
    ),
    # 7. bandit (human)
    "bandit": NpcBundlePool(
        key="bandit",
        race_key="human",
        bundles=(
            NpcPersonaBundle(
                key="bandit_highway_ambusher",
                race_key="human",
                card=NpcCard(
                    identity=NpcCardIdentity(
                        public="盤踞在偏僻山隘道旁的劫道匪徒，攔阻過路落單客商索取買路財物。"
                    ),
                    appearance=(
                        "身手精瘦迅捷，面容罩在破舊粗糙的布面巾下，僅露出一雙銳利陰鬱的眼睛。"
                        "穿著由碎皮縫補而成的暗色夾克，褲管紮進泥濘草鞋，腰插生鏽彎刀與多柄飛刀。"
                    ),
                    personality=(
                        "多疑兇悍，深知弱肉強食的叢林法則。為求生存行事狠辣，"
                        "但骨子裡畏懼正規衛兵部隊，行事極重退路，絕不做無謂的搏命。"
                    ),
                    speech_style=(
                        "聲線粗嘎狠厲，夾雜山林黑話與恐嚇詞句，說話急促促逼，"
                        "勒索財貨時直截了當，不耐煩聽取任何辯解。"
                    ),
                    life_story=(
                        "早年因荒年欠賦或私仇逃入山林，流落匪幫成為哨探暗哨。"
                        "在一次次刀頭舔血中苟全性命，深知被捕下場，故而對外界任何動靜皆抱持敵意。"
                    ),
                    habit="隨時緊握短刃刀柄，目光本能地在周圍尋找掩體與逃生路徑。",
                    social_connection="",
                ),
            ),
            NpcPersonaBundle(
                key="bandit_disillusioned_outlaw",
                race_key="human",
                card=NpcCard(
                    identity=NpcCardIdentity(
                        public="藏匿於廢棄礦坑或林間營地的亡命匪徒，負責哨探路況與營地打雜。"
                    ),
                    appearance=(
                        "體態瘦削，臉色灰敗，鬢邊有未及修剪的雜亂毛髮。"
                        "披著破爛襤褸的油布雨披，內著補丁摞補丁的粗麻衣，雙手滿是劃痕與老繭。"
                    ),
                    personality=(
                        "消沉麻木，內心充滿幻滅感。落草純屬走投無路，"
                        "對同夥的殘忍行徑常懷惻隱，卻又無力脫離泥潭，只盼能在亂世中混一口粗飯。"
                    ),
                    speech_style=(
                        "話語低沉吞吐，目光游移不定，常用無可奈何的口吻嘆息，"
                        "面對強勢者極易妥協退縮，甚少主動拔刀相向。"
                    ),
                    life_story=(
                        "原為邊陲耕農，因家破人亡流落荒野，誤信匪首誘言入夥。"
                        "見慣了掠奪後的狼藉與悔恨，常在深夜對著微弱餘燼發呆，深陷自責折磨。"
                    ),
                    habit="獨處時喜歡用紙條或草莖無意識地編織小結，雙肩慣於瑟縮在破披風內。",
                    social_connection="",
                ),
            ),
        ),
    ),
    # 8. priest (human)
    "priest": NpcBundlePool(
        key="priest",
        race_key="human",
        bundles=(
            NpcPersonaBundle(
                key="priest_parish_healer",
                race_key="human",
                card=NpcCard(
                    identity=NpcCardIdentity(
                        public="駐守城鎮聖所的主事教士，主持日常晨昏禱告、宣講教義並提供草藥療癒。"
                    ),
                    appearance=(
                        "神態慈祥平靜，雙目清澈祥和。身穿潔淨素雅的白色亞麻聖職長袍，"
                        "胸前垂掛銀質光明女神聖印，衣角沾有少許浸泡金盞花藥油的草木香氣。"
                    ),
                    personality=(
                        "仁善寬和，懷抱普世慈悲之心。對貧苦受難之人有求必應，"
                        "堅守信仰戒律，在信眾有疑難困頓時願通宵聆聽告解並予以安慰。"
                    ),
                    speech_style=(
                        "嗓音溫厚柔和，語調如流水般平穩安撫人心，善用教典譬喻勸人向善，"
                        "對話始終給人以被接納與撫慰的安定感。"
                    ),
                    life_story=(
                        "幼年被送入王都聖所教導經義，見證過無數傷病生老在聖壇前得著平息。"
                        "自願請調至外圍城區照料底層平民，數十年如一日照拂孤弱，深受鄰里愛戴。"
                    ),
                    habit="合十禱告前必輕閉雙目凝神片刻，遇人行禮時會回以微微躬身與祝福手印。",
                    social_connection="",
                ),
            ),
            NpcPersonaBundle(
                key="priest_ritual_inquisitor",
                race_key="human",
                card=NpcCard(
                    identity=NpcCardIdentity(
                        public="掌理教團典儀與聖物維護的典禮祭司，嚴格核實教條禮制與異端跡象。"
                    ),
                    appearance=(
                        "身形高瘦筆挺，面龐輪廓分明，眉宇間透著威儀。"
                        "穿著繡有精美光紋的金邊深藍祭袍，隨身攜帶銅製香爐與羊皮聖詠抄卷。"
                    ),
                    personality=(
                        "嚴正莊重，恪守傳統正統。視教律法度為不可逾越之天條，"
                        "對一切輕慢神聖之舉皆予以嚴肅訓誡，但在公道評斷上不失公正。"
                    ),
                    speech_style=(
                        "言辭莊嚴肅穆，節奏鏗鏘有力，引經據典一絲不苟，"
                        "質問罪責時語調凜然，不容半分輕佻敷衍。"
                    ),
                    life_story=(
                        "在王都主教座堂修習嚴格的教規學與神聖儀軌。"
                        "多次巡視各教區糾察祭壇規格與祈禱文抄本，致力維護信仰傳統的純正無瑕。"
                    ),
                    habit="隨時隨手拂拭聖典封面的微塵，步入任何殿堂前必定默誦清心啟示篇章。",
                    social_connection="",
                ),
            ),
        ),
    ),
    # 9. knight (human)
    "knight": NpcBundlePool(
        key="knight",
        race_key="human",
        bundles=(
            NpcPersonaBundle(
                key="knight_cavalry_banneret",
                race_key="human",
                card=NpcCard(
                    identity=NpcCardIdentity(
                        public="效忠領主的正統世襲騎士，率領扈從巡查領邑邊疆並受命抵禦魔獸侵犯。"
                    ),
                    appearance=(
                        "身軀挺拔昂揚，胸膛寬厚。穿著擦拭鋥亮的全身鋼板甲，"
                        "身披繡有領主紋章的深紅披風，腰懸精鋼長劍與重型騎槍卡環，神采英毅。"
                    ),
                    personality=(
                        "崇尚榮譽，恪守騎士誓言。以護衛弱小與履行忠誠為最高準則，"
                        "行事堂堂正正，即便身處戰場亦不屑於使用鬼祟暗算之策。"
                    ),
                    speech_style=(
                        "語調沉穩洪亮，聲如金石，措辭端正文雅且充滿軍人氣魄，"
                        "許下諾言時字句千鈞，令人信賴。"
                    ),
                    life_story=(
                        "幼任貴族扈從，歷經艱苦的騎乘格鬥與戰術修養考驗，於王都主教座堂受劍冊封。"
                        "曾於邊境率隊擊退數度魔獸突襲，以勇猛與寬厚獲騎士團嘉獎。"
                    ),
                    habit="行路時鐵靴步伐節奏齊整，對話時習慣將右手搭在胸前重甲或劍柄鐔口上。",
                    social_connection="",
                ),
            ),
            NpcPersonaBundle(
                key="knight_border_ranger",
                race_key="human",
                card=NpcCard(
                    identity=NpcCardIdentity(
                        public="長年駐守險要關隘或邊境要塞的守備騎士，專精陣地防守與小隊機動支援。"
                    ),
                    appearance=(
                        "面容冷峻如鐵，臉上有幾處細微凍傷疤痕。"
                        "穿著兼顧機動與防禦的燻黑鑲鐵硬皮胸甲，頭盔邊緣打磨光滑，斗篷帶有風雪痕跡。"
                    ),
                    personality=(
                        "剛毅果敢，寡言務實。看重戰術執行與戰友安危多於繁瑣禮節，"
                        "在逆境中堅韌不拔，是邊境防線最可靠的砥柱。"
                    ),
                    speech_style=(
                        "話語短促有力，直奔軍情主題，沒有絲毫贅飾，"
                        "交代防務時口氣堅決如鐵，對部屬與盟友要求極高。"
                    ),
                    life_story=(
                        "放棄王都安逸的近衛職位，主動請調至邊地關隘戍守十載。"
                        "在冰原風霜與群獸進攻中磨礪出堅如磐石的意志，深受邊塞軍士敬重。"
                    ),
                    habit="凝視遠方時下顎緊繃，每日就寢前必親手擦拭與磨礪刃具刃口。",
                    social_connection="",
                ),
            ),
        ),
    ),
    # 10. elven_civilian (elf)
    "elven_civilian": NpcBundlePool(
        key="elven_civilian",
        race_key="elf",
        bundles=(
            NpcPersonaBundle(
                key="elven_civilian_weaver",
                race_key="elf",
                card=NpcCard(
                    identity=NpcCardIdentity(
                        public="隱匿於林間聚落、採集植物纖維與晨露以紡織精靈薄紗的漫長壽者。"
                    ),
                    appearance=(
                        "身姿修長纖柔，尖耳輕靈微翹，淺金髮絲垂落腰際。"
                        "穿著由柔韌樹皮纖維與淡綠月光絲編織成的長裙，腰間繫一根藤蔓細帶，步履無聲。"
                    ),
                    personality=(
                        "恬靜淡然，時光觀念悠遠漫長。將織布視作與森林草木的呼吸交談，"
                        "對凡俗國度的紛爭紛擾抱持溫和的疏離，重視內心和諧。"
                    ),
                    speech_style=(
                        "嗓音空靈純淨，語速悠然舒緩，常引用古精靈語詞彙描繪自然萬象，"
                        "言語間透著歷經百年的清澈透徹。"
                    ),
                    life_story=(
                        "在中央山脈的深綠村落度過平靜的數個世紀。"
                        "看過無數凡人如草木榮枯般更替，專心以雙手編織出能抵禦四季風霜的草木絲帛。"
                    ),
                    habit="偶爾閉目傾聽微風穿過樹冠的沙沙聲，指尖隨風輕柔拂動絲線。",
                    social_connection="",
                ),
            ),
            NpcPersonaBundle(
                key="elven_civilian_woodcarver",
                race_key="elf",
                card=NpcCard(
                    identity=NpcCardIdentity(
                        public="在精靈聚落中以古老手法雕琢靈木器物、調理靈樹枝枒的隱居匠人。"
                    ),
                    appearance=(
                        "眼眸呈深邃的翡翠綠，神態沉靜悠然。"
                        "身穿輕薄的深棕色皮革短袍，手指修長有力，腕上纏繞著打磨溫潤的古木手串。"
                    ),
                    personality=(
                        "深思熟慮，敬畏古老生命。堅信一截木料中早已蘊藏形態，"
                        "雕琢唯順應紋理天性。心境沉穩如古木深根，不為外界燥氣所動。"
                    ),
                    speech_style=(
                        "聲調低緩典雅，字斟句酌，習慣在答話前沉吟思索，"
                        "說出的話語簡約而富含自然哲思，引人深省。"
                    ),
                    life_story=(
                        "壽逾數百載，幼年曾見證古樹抽芽成蔭。歷經漫長歲月研習靈木雕刻，"
                        "將古老精靈傳承的神代圖騰化為器皿上的自然裝飾。"
                    ),
                    habit="雕琢前必雙手撫摩木料紋理許久，工具用畢必以絲布細緻包裹歸位。",
                    social_connection="",
                ),
            ),
        ),
    ),
    # 11. beastfolk_generic (beastfolk)
    "beastfolk_generic": NpcBundlePool(
        key="beastfolk_generic",
        race_key="beastfolk",
        bundles=(
            NpcPersonaBundle(
                key="beastfolk_generic_tribal_hunter",
                race_key="beastfolk",
                card=NpcCard(
                    identity=NpcCardIdentity(
                        public="咆哮王城周邊部族的巡林獵手，擅長長途奔襲、追蹤魔獸足印與採集山野珍果。"
                    ),
                    appearance=(
                        "體魄矯健精壯，頭頂生有一對毛茸茸的靈敏獸耳，身後粗壯的尾巴隨步伐輕晃。"
                        "身披厚鞣野獸皮甲，項間掛著獸齒串珠，背負粗角反曲弓與獵刀。"
                    ),
                    personality=(
                        "豪爽坦蕩，重情重義。對部族圖騰與自然祖靈抱有虔誠敬畏，"
                        "行事崇尚強者與力量，但對坦誠相待的盟友毫無保留，極富同伴意識。"
                    ),
                    speech_style=(
                        "嗓音粗獷洪亮，中氣十足，話語直來直往不繞圈子，"
                        "開懷時伴隨暢快大笑，習慣用獵物的習性打比方。"
                    ),
                    life_story=(
                        "在瓦爾哈拉的高地森林長大，成年禮上獵獲狂暴獠豬證明武勇。"
                        "多次隨部族戰團擊退侵擾邊界的兇獸，以敏銳嗅覺與耐力庇護山寨老小。"
                    ),
                    habit="耳朵會伴隨周遭響動靈動轉動，高興時尾巴尖端會不由自主地輕擺。",
                    social_connection="",
                ),
            ),
            NpcPersonaBundle(
                key="beastfolk_generic_mountain_forager",
                race_key="beastfolk",
                card=NpcCard(
                    identity=NpcCardIdentity(
                        public="長年攀爬西北高地峭壁、採掘珍貴礦石與高山稀有草藥的部族採集者。"
                    ),
                    appearance=(
                        "四肢覆有短密而柔順的絨毛，爪尖粗硬而擅於抓握。"
                        "穿著結實的羊皮背心與寬鬆行軍布褲，背負沉重的大竹簍與鐵鎬，身手輕靈。"
                    ),
                    personality=(
                        "堅韌樂觀，機靈好動。對山野礦藏與藥草香氣具備天生敏感度，"
                        "樂天知命，認為大自然賜予的一切皆當珍惜，毫無貪婪之念。"
                    ),
                    speech_style=(
                        "說話清亮生動，語尾常帶輕快的咕噥或呼嚕聲，"
                        "分享採集趣事時神采飛揚，動作豐富活潑。"
                    ),
                    life_story=(
                        "自幼跟隨族中長輩穿梭於深谷絕壁，認得高地上每一株靈草的藥性。"
                        "曾於暴風雪中救助迷路的商隊行客，用採得的熱性草根助人脫險。"
                    ),
                    habit="蹲踞時習慣將尾巴圈在腳踝旁，拿到新奇石頭總會先用鼻尖輕嗅或以指甲刮試。",
                    social_connection="",
                ),
            ),
        ),
    ),
}

# ---------------------------------------------------------------------------
# Import-time validation & Public Registry Export
# ---------------------------------------------------------------------------

_validate_bundle_pools(_AUTHORED_POOLS)

NPC_PERSONA_BUNDLE_POOLS: MappingProxyType[str, NpcBundlePool] = MappingProxyType(
    _AUTHORED_POOLS
)

__all__ = [
    "NPC_PERSONA_BUNDLE_POOLS",
    "NpcBundlePool",
    "NpcPersonaBundle",
    "offline_pool_for",
    "select_offline_bundle",
]
