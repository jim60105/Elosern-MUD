"""Player-preset card data (first half): the four pack-derived cards.

Contiguous, in-order slice of the former ``PLAYER_PRESET_REGISTRY`` literal in
``world/lore/player_presets.py``: ``elysa_snow``, ``nazka_bloodfang``,
``sylwen_stillwater``, ``violet_altoria`` (authored comments included, verbatim).
Global registry order is observable (creation card listing, data-lint,
key-order contracts), so ``ROWS`` order is frozen.
"""

from world.lore.player_presets.vocab import (
    PlayerPreset,
    PresetAppearance,
    PresetIdentity,
    PresetPersona,
    PresetSexualBaseline,
    StartingCompanion,
)

ROWS: dict[str, PlayerPreset] = {
    "elysa_snow": PlayerPreset(
        # Key drawn from the fantasy-human name corpus (world/lore/names, via
        # world.rules.namegen): Elysa + Snow. The display name is the pack's
        # 正體 rendering of the given name; the full name lives in the
        # identity layers.
        "elysa_snow", "艾莉莎", 24, 24, "human", "human_plains",
        (("hp", 50), ("mp", 50), ("sp", 50), ("atk_phys", 10),
         ("agility", 10), ("defense", 11), ("magic_power", 43)),
        "生命力與魔力均衡的開局配點",
        active_skills=("light_sword_style",),
        passive_skills=("body_enhancement_basic",),
        starting_items=(("plain_sword", 1), ("leather_armor", 1),
                        ("guild_recruit_badge", 1), ("healing_potion", 2),
                        ("healing_herb", 2)),
        sex="female",
        starting_equipment=("plain_sword", "leather_armor", "guild_recruit_badge"),
        persona=PresetPersona(
            identity=PresetIdentity(
                public="南境出身的公會新人冒險者，測繪局抄寫員出身的旅人",
                hidden=(
                    "追尋母親最後一份地圖上那片無名空白的女兒；所有知道那片空白的人，"
                    "都已經失蹤"
                ),
            ),
            personality=(
                "對任何人都能在三句話內熟絡起來，先讓人笑，再讓人卸下戒心，"
                "這是抄寫員的女兒從小學會的本事。她對文字有近乎強迫的忠實，聽過的每句話、"
                "看過的每張地圖，她都要抄進隨身筆記，連自己的謊話也照記。別人眼裡這是怪癖，"
                "對她卻是對付遺忘的方式——母親失蹤以後她才明白，記憶會騙人，抄本不會。"
                "對委託來者不拒，對報酬計較到銅板，但每次掙到一筆大錢都會請路上最窮的人吃一頓。"
                "從不在同一個城鎮睡超過三晚，除了公會公告上出現「空白」兩個字的地方。"
            ),
            life_story=(
                "母親艾黛勒是王國測繪局少見的女性測繪師，六年前帶隊進入南方那片「地圖上沒有名字的空白」，"
                "從此沒有回來。官方檔案裡那支隊伍只存在過一頁，而那一頁也在她十六歲那年悄悄消失了，"
                "她來不及抄下它，這件事她追悔了八年。十八歲起她在測繪局做抄寫員，十年間抄過上萬份文件，"
                "把每一份與「空白」有關的邊注都背了起來。二十歲那年，她從母親歷年報告裡湊齊了十七個座標中的十六個，"
                "每條路線的盡頭都指向同一個不存在的地方。二十四歲，她辭去職位、變賣家當在公會登記，"
                "把筆記翻到新的一頁，這一次由她親自走去那第十七個座標。"
            ),
            habit=(
                "隨身帶著三本筆記、兩支炭筆：一本記人、一本記路、一本只抄與「空白」有關的文字；"
                "睡前會把當天說過的話重讀一遍，確認自己沒有不知不覺撒謊；每次住店都用同一個假名，"
                "但姓氏永遠沿用母親的舊姓。"
            ),
            appearance=PresetAppearance(
                height="168 公分",
                weight="55 公斤",
                measurement="胸圍 88（C 罩杯）、腰 64、臀 90",
                style="小麥膚色的開朗旅人",
                overview=(
                    "深褐長髮綁成實用的低馬尾，綠色眼眸愛笑，鼻梁上有淡淡的曬斑；"
                    "指節與右手中指內側有常年握筆磨出的繭，笑容燦爛，視線卻永遠在讀環境。"
                ),
                attire="磨舊的皮甲與旅人斗篷，腰間掛著一把擦得過分外亮的長劍，背包塞滿筆記。",
                feature=(
                    "右手永遠沾著洗不掉的炭筆污痕；頸上掛著母親測繪隊的銅製羅盤吊墜，"
                    "指針從來不準，她卻從未摘下。"
                ),
            ),
            social_connection=(
                ("艾黛勒·懷特", "母親，失蹤的測繪師；她追隨母親腳步的起點，也是她唯一不敢抄進筆記的話題"),
            ),
            background=(
                "南境出身的公會新人冒險者，測繪局抄寫員出身。母親六年前走入地圖上一片無名空白後失蹤，"
                "官方記錄隨後被人抹去。她帶著十年抄本與一把磨亮的長劍出發，要用自己的腳補上那張缺了一角的地圖；"
                "均衡的劍術與基礎強化，是她敢獨自上路的底氣。"
            ),
        ),
        sexual_baseline=PresetSexualBaseline(
            arousal="平靜",
            virgin=True,
            sensitivity=(("頸項", "高"), ("耳朵", "高"), ("腰腹", "高")),
            shame="中等",
            exposure="低",
        ),
    ),
    "nazka_bloodfang": PlayerPreset(
        # Key drawn from the fantasy-orc name corpus (world/lore/names, via
        # world.rules.namegen): Nazka + Bloodfang.
        "nazka_bloodfang", "娜茲卡", 22, 22, "beastfolk", "foxkin",
        (("hp", 25), ("mp", 10), ("sp", 25), ("atk_phys", 15),
         ("agility", 15), ("defense", 15), ("magic_power", 14)),
        "敏捷與近身作戰優先的斥候配點",
        active_skills=("gale_step",),
        passive_skills=("flash_step",),
        affinity_elements=("wind",),
        starting_items=(("hunters_longbow", 1), ("hunting_throwing_axe", 1),
                        ("leather_armor", 1), ("wolf_fang_necklace", 1),
                        ("healing_potion", 1), ("healing_herb", 3)),
        sex="female",
        starting_equipment=(
            "hunters_longbow", "hunting_throwing_axe", "leather_armor", "wolf_fang_necklace"
        ),
        persona=PresetPersona(
            identity=PresetIdentity(
                public="獸王國瓦爾哈拉出身的信使，公會新人斥候",
                hidden=(
                    "十年間獸王國送信者不敢說出口的每一封密信函，都在她腦子裡。"
                    "她發過誓不說，卻從沒發過誓不記得"
                ),
            ),
            personality=(
                "話多、愛笑、腿快，是獸王國最難纏的聊天對象，三句話內她就能讓人不知不覺說出"
                "本不想說的話，而她連看都不看你一眼。對「送信」有近乎神職的執念——信件在路上是死的，"
                "送到才算活著。她記得經手的每一封信的內容，這是職業病，也是她對寫信人的"
                "最後一種溫柔。收信人死了、搬走了、忘了回信，至少還有人記得那句話說過。"
                "從不賣情報，也從不用情報換好處；但如果有人能讓她笑到岔氣，她可能一不小心說漏半句。"
            ),
            life_story=(
                "出身獸王國瓦爾哈拉的送信世家，從小聽著「信送不到，命就該留在路上」長大。"
                "十二歲通過信使考核，是當時十年來最年輕的正式信使；十七歲那年雪夜連走三個聚落送藥，"
                "右耳尖凍掉一小塊，族裡都說那是信使勳章。十九歲，她送的最後一封信，收信人已經死了三天。"
                "她照規矩把信燒給死人，回家路上第一次想到，除了她還有誰記得那封信寫了什麼。"
                "從那天起，她開始把經手的信逐字背下來。二十一歲，她帶著一紙內容不明的調令離開獸王都，"
                "到人類公會登記成斥候。她說自己是要去「送一封更長的信」，卻怎麼也不肯說是哪一封、送給誰。"
            ),
            habit=(
                "跑步時把經過的地形默背成路線圖；坐下來必先確認出口與至少兩條脫身路線；"
                "聊天時尾巴早就出賣了情緒，她卻堅持自己「表情管理很好」；每晚睡前在腦中"
                "把當天新背起來的信從頭到尾默讀一遍。"
            ),
            appearance=PresetAppearance(
                height="158 公分",
                weight="48 公斤",
                measurement="胸圍 86（D 罩杯）、腰 57、臀 89",
                style="橙白毛色的高馬尾狐人族少女",
                overview=(
                    "橙白色長髮束成高馬尾，琥珀色豎瞳總像在笑，右耳尖少了一小塊，"
                    "那是獸王國信使的勳章；尾巴蓬鬆，情緒一激動就完全藏不住。"
                ),
                attire="斥候皮甲與輕便斗篷，背長弓、腰間別飛斧，胸前掛著磨舊的小皮袋。",
                feature=(
                    "右耳尖缺一角；說謊時蓬鬆的大尾巴會不由自主往左偏——這是她全身上下唯一不會撒謊的地方。"
                ),
            ),
            social_connection=(
                ("布麗", "養大她的白母狼；牙項鍊是她送出的告別禮，布麗卻咬斷項鍊送回她門前"),
            ),
            background=(
                "獸王國瓦爾哈拉出身的狐人族信使，十年間經手的每一封信她都逐字記得，卻從不說出口。"
                "疾風術與瞬步讓她在斥候崗位上幾乎不會被追上；她說離開獸王國是去「送一封信」，"
                "卻拒絕說是哪一封、送給誰。"
            ),
        ),
        sexual_baseline=PresetSexualBaseline(
            arousal="微興奮",
            virgin=True,
            sensitivity=(("耳朵", "極高"), ("頸項", "高"), ("臀部", "高")),
            wetness="微濕",
            shame="輕微",
            exposure="低",
        ),
    ),
    "sylwen_stillwater": PlayerPreset(
        # Key drawn from the fantasy-elf name corpus (world/lore/names, via
        # world.rules.namegen): Sylwen + Stillwater.
        "sylwen_stillwater", "希爾溫", 180, 24, "elf", "fionnen",
        (("hp", 0), ("mp", 0), ("sp", 0), ("atk_phys", 12),
         ("agility", 12), ("defense", 13), ("magic_power", 400)),
        "防禦與均衡戰技優先的守護者配點",
        active_skills=("hardened_skin",),
        passive_skills=("defense_instinct", "elf_longevity"),
        starting_items=(("knight_blade", 1), ("iron_shield", 1),
                        ("chainmail", 1), ("pilgrim_medallion", 1),
                        ("healing_potion", 1)),
        sex="female",
        starting_equipment=("knight_blade", "iron_shield", "chainmail", "pilgrim_medallion"),
        persona=PresetPersona(
            identity=PresetIdentity(
                public="斐歐恩森林出身的精靈族護衛，人族王國的傭兵守護者",
                hidden="守著三道守護誓約的人——前兩道的對象，都已老成土裡的名字",
            ),
            personality=(
                "沉穩、有耐心，像一棵不會因為風彎腰的樹。比起爭勝，她更在意「有沒有任何人活著回來」，"
                "隊伍裡最危險的位置她永遠先站。她對人族的短壽有一種異常的珍視，會記住每個共事過的人"
                "愛吃什麼、怕什麼、說過哪句傻話，然後在對方老去之後，把這些話說給對方的孫輩聽。"
                "不擅長被感謝，被人當面誇獎時會彆扭地低頭擦盾牌。笑容很少，卻從不吝嗇，"
                "對孩子、新兵、以及所有怕死的人格外溫柔；在她眼裡，怕死是把日子過下去的證明。"
            ),
            life_story=(
                "出生在斐歐恩森林，成長禮那天用森林古語立下斐歐恩護衛世代一次的誓約——守護一個自己選定的人族。"
                "第一位守護對象是人族商隊護衛漢斯，她守到他七十一歲在搖椅中安詳過世，子孫在靈前為她留了一杯蜂蜜酒。"
                "第二位是漢斯的曾孫女；她在難產的夜裡為擋住闖進帳篷的野獸失去半截左手小指，卻把母子兩人都救了回來。"
                "如今她守著的是那個孩子留下的血脈。誓約的字面早已超過，她把整條血脈都算進了誓言。"
                "以傭兵護衛的身分流浪在人族王國，公會檔案裡她的年齡寫成一串被職員當成玩笑的數字。"
            ),
            habit=(
                "每年冬至在盾牌背帶上刻一道痕，記下又平安過完的一年；幫人包紮時動作輕得和握盾的手"
                "完全不像同一個人；睡前會把共事過的人的名字在腦中從最年輕唸到最年長，一個都不許忘記。"
            ),
            appearance=PresetAppearance(
                height="174 公分",
                weight="62 公斤",
                measurement="胸圍 92（E 罩杯）、腰 66、臀 94",
                style="銀綠長髮的高挑精靈重甲護衛",
                overview=(
                    "銀綠色長髮束成一條低辮，翠綠眼眸沉靜溫和，臉側有一道從額角延伸到頰的舊疤；"
                    "站姿穩得像面牆，精靈的尖耳收在辮子後頭。"
                ),
                attire="連鎖甲與塔盾在內的護具，胸前掛著斐歐恩森林的銀葉吊墜。",
                feature=(
                    "盾牌背帶上刻著一百多年的歲痕；左手小指缺了半截。那個夜晚她沒來得及把盾牌收進狹窄的帳篷，"
                    "人救回來了，那半截手指卻留了下來。"
                ),
            ),
            social_connection=(
                ("漢斯·懷特", "第一位誓約對象、人族商隊護衛；他活到七十一歲，臨終把兒女托付給她這個精靈"),
            ),
            background=(
                "斐歐恩森林出身的精靈族護衛，用一百八十年的歲月實踐世代一次的守護誓約。"
                "硬化肌膚與防禦直覺讓她成為隊伍最可靠的盾；她守護人族，正因為日子短，"
                "每一天才都值得守。"
            ),
        ),
        sexual_baseline=PresetSexualBaseline(
            arousal="平靜",
            virgin=False,
            sensitivity=(("耳朵", "極高"), ("乳房", "高"), ("私處", "高")),
            shame="輕微",
            exposure="極低",
        ),
    ),
    "violet_altoria": PlayerPreset(
        # Reconverted from tmp/story_settings/character/VioletAltoria.md: age
        # 16, story gauges 150/180/150 exact, pre-buff statics 5/6/6 exact,
        # remaining budget into magic power (story "magic level 30" reads as a
        # moderate-high magic attribute for a prodigy).
        "violet_altoria", "薇歐蕾特", 16, 16, "human", "human_royal",
        (("hp", 50), ("mp", 60), ("sp", 50), ("atk_phys", 4),
         ("agility", 5), ("defense", 4), ("magic_power", 51)),
        "體力與生命力紮實、魔力突出的術師配點",
        active_skills=("fire_ball", "wind_blade"),
        passive_skills=(
            "magic_circle_comprehension", "precise_mana_control", "flight",
        ),
        affinity_elements=("fire", "wind"),
        starting_items=(("elven_traditional_robe", 1), ("royal_signet_ring", 1),
                        ("royal_heirloom_pendant", 1), ("saintess_vestments", 1)),
        sex="female",
        # Story's current equipment: spirit robe worn, signet ring on the right
        # ring finger; the heirloom pendant stays carried (her nervous habit).
        starting_equipment=("elven_traditional_robe", "royal_signet_ring"),
        persona=PresetPersona(
            identity=PresetIdentity(
                public="出行的王國王女、光明教會的聖女、伊洛希雅的弟子、風之術師",
                hidden="王室秘密外交特使，意圖將伊洛希雅·幽月納入王國盟友",
            ),
            personality=(
                "任何場合都維持得體的微笑與禮貌應對，從不失態；深知自己是天才，"
                "也深知天才的上限，對自身能力評價準確。意志堅韌，對羞恥與不適的"
                "耐受力遠超同齡人；對師父伊洛希雅的信任達到盲目程度。被出乎預料的"
                "逗弄時，從容會短暫破防，越是羞恥說話越端正優雅。聖女的公開祝福對她"
                "早已不是宗教經驗而是羞恥耐力測試，祝福的峰值來得不是時候、不在場"
                "合，而她連臉紅的權利都沒有，因為禮儀課教過她「聖女在信眾面前必須從"
                "容」；她回聖殿當例行義務做的傾湧儀式，被伊洛希雅改造成觀眾席上簽名"
                "收門票的公開餘興。表面維持王女矜持，"
                "被充分開發的身體卻早已背叛意志，不合時宜的場合自然濕潤，既羞恥"
                "又興奮；僅在無人在場時才流露普通少女的羞恥與不安。"
            ),
            life_story=(
                "5 歲起接受宮廷禮儀、多國語言與政治史學的全方位教育；7 歲對四階"
                "魔法陣一看即懂，被宮廷冠以「神童」稱號，但她比任何人都明白自己的"
                "天花板在哪裡。8 歲由聖座依王室世襲慣例祝聖接任聖女。阿爾托利亞每代"
                "獻一女為女神的容器，她受訓的第一課就是傾湧祝福，從此「被全城見證的"
                "高潮」寫進行事曆，王女教育則把這份公開教成必須從容完成的公務；她後"
                "來從不在聖殿祝福。出行之後，每一次都發生在她最沒有準備的場合。13 "
                "歲時父王透露精靈族若能成為王國友方，可扭轉對帝國"
                "的軍事劣勢。15 歲以史上最年輕首席身份從王立魔法初等學校畢業，魔法"
                "等級由 10 級升至 30 級。16 歲出行時被伊洛希雅超越人類極限的魔法"
                "震撼，請求拜師，接受了「穿著精靈傳統服飾一同冒險」的條件。第一次"
                "穿上幾近全裸的服飾走上街頭，全身僵硬仍勉強維持微笑。"
            ),
            habit=(
                "無論何種狀況都維持筆直儀態；緊張時習慣以指尖輕觸胸前吊墜。穿上"
                "精靈傳統服飾後胸部全裸，這個習慣反而讓她頻繁觸碰自己的胸口；私下"
                "研讀伊洛希雅給的精靈古籍，對鏡審視自己現在到底像什麼。"
            ),
            appearance=PresetAppearance(
                height="155 公分",
                weight="46 公斤",
                measurement="胸圍 82（B 罩杯）、腰 56、臀 83",
                style="優雅清冷的少女王族",
                overview=(
                    "身形纖細修長，金色長直髮半盤，藍眸清澈沉靜，皮膚白皙，"
                    "五官精緻柔和；人族，沒有長耳朵。"
                ),
                attire="與伊洛希雅同款的精靈傳統服飾，白色半透明、幾近全裸的「文化服飾」。",
                feature=(
                    "右手無名指佩戴嵌王室紋章的細金戒指，是唯一隨身攜帶的身份象徵；"
                    "在精靈傳統服飾下私處完全暴露，長期「訓練」使身體帶著明顯的淫靡痕跡。"
                ),
            ),
            social_connection=(
                ("伊洛希雅·幽月", "師父與主要逗弄對象，被單方面支配，信任近乎盲目；互稱「伊洛」「薇歐」"),
                ("莉茲婭·羅森塔爾", "從小一起長大的玩伴、貼身侍女兼保鏢，如今承擔痴女侍從的職責；她喚我「主人」，我喚她「莉茲」"),
            ),
            background=(
                "阿爾托利亞王國第一王女、光明教會的聖女，「痴女與精靈」小隊隊長。"
                "8 歲接任聖女，誓約只有一條，身體為女神保留。16 歲拜入伊洛希雅"
                "門下，以穿著精靈傳統服飾一同冒險為拜師條件。天才術師的火球與風刃"
                "遠超同齡，飛行術使她習慣從高處俯瞰世界；對外報出隊名時伴隨極度羞恥，"
                "卻無法否認那個名字對自身狀態的描述完全準確。"
            ),
        ),
        sexual_baseline=PresetSexualBaseline(
            arousal="微興奮", virgin=True,
            sensitivity=(("私處", "極高"), ("乳房", "高"), ("耳朵", "高")),
            wetness="濕潤", shame="中等", exposure="高",
        ),
        # The story's party travels together: Violet sets out with her retainer
        # and follows her elven master.
        starting_companions=(
            StartingCompanion("lidzia_rosenthal", 95, "貼身近侍"),
            StartingCompanion("elosia_shadowmoon", 95, "師父"),
        ),
    ),
}
