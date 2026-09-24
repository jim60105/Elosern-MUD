"""Player-preset card data (second half): the four story-reconverted cards.

Contiguous, in-order slice of the former ``PLAYER_PRESET_REGISTRY`` literal in
``world/lore/player_presets.py``: ``lidzia_rosenthal``, ``yuka_darknight``,
``yuna_darknight``, ``elosia_shadowmoon`` (authored comments included, verbatim).
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
    "lidzia_rosenthal": PlayerPreset(
        # Pre-meeting Lidzia: still Princess Violet's travelling retainer, but
        # the devoted-handmaid role the later story gives her never existed
        # yet -- that came with the elven robe. age 14, story statics 8/9/7
        # exact under the noble modifiers; the story's MP 70 sits below the
        # human floor, so MP stays at the floor (her weakest gauge, matching
        # "魔法天賦極差") and the forced remainder lands on the story's
        # strongest gauges, stamina over vitality.
        "lidzia_rosenthal", "莉茲婭", 14, 14, "human", "human_noble",
        (("hp", 80), ("mp", 0), ("sp", 100), ("atk_phys", 6),
         ("agility", 8), ("defense", 7), ("magic_power", 23)),
        "體力最強、劍技敏於防禦的近侍配點",
        active_skills=("light_sword_style",),
        passive_skills=(
            "body_enhancement_basic", "retainer_martial_training",
            "guardian_instinct",
        ),
        starting_items=(("rose_crest_rapier", 1), ("black_maid_dress", 1),
                        ("silver_feather_earring", 1)),
        sex="female",
        # Story's equipment: rapier, maid dress, and the never-removed earring.
        starting_equipment=("rose_crest_rapier", "black_maid_dress",
                            "silver_feather_earring"),
        persona=PresetPersona(
            identity=PresetIdentity(
                public="王女薇歐蕾特的貼身侍女、隨身秘書與保鏢",
                hidden="無可救藥地愛著薇歐蕾特，這份愛不索求回報；她的幸福就是殿下的幸福",
            ),
            personality=(
                "任何場合都維持完美侍從的儀態與效率，把每件事做到極致，是她表達愛"
                "的唯一合法方式。劍術與文書出類拔萃，全力以赴卻在一句稱讚面前臉紅低"
                "頭；對同僚開朗、好人緣，唯獨薇歐蕾特是讓她連呼吸都要練習的人。殿下"
                "面臨危險的瞬間，羞澀像多餘的東西一樣剝落，殺意像死神確認名單那樣淡"
                "定；僅與殿下獨處時才露出真實笑容與撒嬌。這份愛太重，重到需要痛來平"
                "衡，但她從未想過獨佔。如果殿下的幸福需要她消失，她會消失。"
            ),
            life_story=(
                "羅森塔爾家族世代侍奉王室，3 歲起接受嚴格禮儀與武術訓練，「被需要」"
                "本身就足以填滿她。5 歲在王室宴會上對 7 歲的薇歐蕾特一見傾心；7 歲"
                "入宮為初級侍女，端茶燙傷手背時由公主親自包紮，那隻手的溫度至今留在"
                "掌心。10 歲攔截針對公主的毒殺未遂，獲授近侍職位；評估每個靠近公主"
                "之人的威脅等級，是她的安眠藥。12 歲以護衛考核全項第一通過，拒絕近"
                "衛隊延攬，選擇繼續做公主的影子。13 歲意識到心跳不再只因職責，那夜"
                "回味包紮時的觸感而初嘗自慰，高潮後哭著覺得自己褻瀆了某種神聖。14 "
                "歲隨薇歐蕾特出行歷練。哪裡有殿下，哪裡就是家。"
            ),
            habit=(
                "每個動作輕柔而穩定，端茶的角度、關門的音量、站立的間距皆精確如舞"
                "步；在薇歐蕾特身邊保持半步距離，這個距離練習了數年，已是身體記憶；"
                "每晚睡前檢查殿下的裝備與行李，深夜獨處時才敢抱著沾有殿下氣息的手帕"
                "入睡。"
            ),
            appearance=PresetAppearance(
                height="150 公分",
                weight="42 公斤",
                measurement="胸圍 84（C 罩杯）、腰 55、臀 82",
                style="短髮稚氣的文武雙全美少女",
                overview=(
                    "黑色短鮑伯頭配齊瀏海，嬰兒肥臉頰，琥珀色眼眸溫和明亮，看薇歐蕾特"
                    "時瞳孔會不自覺放大；身材豐滿與稚嫩面容形成反差。人族，沒有長耳朵。"
                ),
                attire="黑色女僕裝搭配極短微裙與白色腰圍裙，輕劍斜掛腰間。",
                feature=(
                    "腰間輕劍劍柄末端刻有薇歐蕾特親手雕的王室薔薇紋章；右耳銀羽耳環是"
                    "薇歐蕾特 12 歲時的禮物，從未摘下。"
                ),
            ),
            social_connection=(
                ("薇歐蕾特·阿爾托利亞", "殿下、她生存的中心、心臟跳動的理由，比起主人更像是她的信仰；稱她「殿下」，把不敢說出口的愛全數藏進侍奉裡"),
            ),
            background=(
                "世代侍奉王室的羅森塔爾家族之女，薇歐蕾特王女的貼身近侍。輕劍術在"
                "護衛考核名列前茅，隨從武藝與護主本能使她永遠站在殿下與危險之間；"
                "基礎身體強化是她僅有的魔法天賦。她以完美的侍奉藏起一份不敢驚動對方"
                "的愛，尚未意識到自己願為這個人消失。"
            ),
        ),
        sexual_baseline=PresetSexualBaseline(
            arousal="平靜", virgin=True,
            sensitivity=(("頸項", "高"), ("耳朵", "高"), ("乳房", "高"),
                         ("腰腹", "高"), ("大腿", "高")),
            shame="強烈",
        ),
        # Pre-meeting: she still travels at Violet's side; nothing more has
        # begun yet.
        starting_companions=(StartingCompanion("violet_altoria", 95, "殿下"),),
    ),
    "yuka_darknight": PlayerPreset(
        # Reconverted from tmp/story_settings/character/YukaDarknight.md: age
        # 16; base statics 88/92/90 exact (the x1000 body enhancement is the
        # skill, not the allocation); the remaining budget inflates magic
        # power above the story's 250 because the elf gauge floors consume no
        # budget and the budget must be spent in full.
        "yuka_darknight", "悠花", 16, 16, "elf", "ciaran",
        (("hp", 0), ("mp", 0), ("sp", 0), ("atk_phys", 18),
         ("agility", 22), ("defense", 20), ("magic_power", 377)),
        "攻擊與防禦逼近精靈上限的雙刀配點",
        active_skills=("dual_blade_waltz", "shadow_slash", "status_disguise"),
        passive_skills=(
            "fire_mastery", "dark_mastery", "body_enhancement_extreme",
            "flash_step", "flight", "dual_wield_style", "blade_art_mastery",
            "extreme_endurance", "defense_instinct", "reincarnation_boon_yuka",
        ),
        starting_items=(("shadow_blade", 1), ("shadow_blade_echo", 1),
                        ("dark_elf_ninja_garb", 1)),
        sex="female",
        # Story's equipment: both blades and the garb are worn.
        starting_equipment=("shadow_blade", "shadow_blade_echo",
                            "dark_elf_ninja_garb"),
        persona=PresetPersona(
            identity=PresetIdentity(
                public="暗影谷村的年輕黑暗精靈、擁有罕見黑髮的雙刀使、悠奈的旅伴與妹妹",
                hidden="轉生者（前世為現代日本的女高中生）、刀術狂熱者、悠奈最珍視的伴侶",
            ),
            personality=(
                "陽光開朗、充滿活力，笑容極具感染力，走到哪裡都能迅速融入人群。對"
                "刀術的熱愛近乎痴迷，每一次揮刀都是在跟自己的極限對話；熱愛體能，"
                "享受突破身體框架的快感。握刀時氣質驟變，整個人像一把出鞘的刀；心底"
                "仍保留一絲前世的害羞，在公共場合裸露會不自覺遮一下，然後尷尬地笑笑"
                "放下手。深愛悠奈，是不帶任何保留的純粹的愛；最大的秘密是對悠奈的魔"
                "力上癮。普通的性愛對她早已索然無味，能真正滿足她的只剩悠奈的魔法，"
                "而她永遠不會承認這件事。"
            ),
            life_story=(
                "前世是現代日本田徑隊王牌女高中生，16 歲與姊姊悠奈一同死於意外，睜"
                "眼成為暗影谷村黑暗精靈的新生兒，前世記憶一如昨日。4 歲第一次握上木"
                "刀的瞬間找到此世歸屬，感動到幾乎落淚；5 歲轉生特典「武感」顯現，能"
                "本能預判對手攻擊意圖。10 歲已是同輩最出色的刀術使，14 歲修成身體超"
                "強化。16 歲與悠奈一同離開村子。不管去哪裡，只要跟悠奈在一起就是好"
                "地方。"
            ),
            habit=(
                "每天固定體能訓練與刀術練習，練完滿身大汗回到悠奈身邊；走路步伐輕"
                "快，習慣走在前面，每次回頭確認悠奈的位置才安心前進；在公共場合仍會"
                "不自覺遮一下胸口或下體，然後尷尬地笑笑放下手。"
            ),
            appearance=PresetAppearance(
                height="165 公分",
                weight="52 公斤",
                measurement="胸圍 90（D 罩杯）、腰 59、臀 88",
                style="罕見黑短髮的運動系黑暗精靈",
                overview=(
                    "基亞蘭族褐色健康膚色，黑色短鮑伯頭清爽俐落，紅色眼眸明亮有神；"
                    "肌肉線條結實，力量與柔美並存，精靈族的尖耳從短髮間探出。"
                ),
                attire="基亞蘭族墨黑戰鬥服飾，忍者基底的短和服剪裁，刻意敞開的前襟與極短裙襬。",
                feature=(
                    "罕見黑色短鮑伯頭，在銀髮同族中與悠奈並列為異色存在；長期練刀使"
                    "手掌帶著薄繭，笑容極具感染力。"
                ),
            ),
            social_connection=(
                ("悠奈", "雙胞胎姊姊、前世的摯愛、此世的靈魂伴侶；互稱「悠奈」「悠花」。前世一同死於意外，此世一同作為黑暗精靈誕生"),
            ),
            background=(
                "暗影谷村出身的黑暗精靈雙刀使，罕見的黑短髮在銀髮同族中格外醒目。"
                "雙刃旋舞與影斬名聲在外，轉生特典武感使她總能先一步抵達對手要害。"
                "陽光開朗，視戰鬥為與自身極限的對話，與姊姊悠奈形影不離。"
            ),
        ),
        # Story's disguise layer: magic 30, physical 60, agility 60, defense 30.
        disguised_stats=(("magic_power", 30), ("atk_phys", 60),
                         ("agility", 60), ("defense", 30)),
        sexual_baseline=PresetSexualBaseline(
            arousal="微興奮", virgin=False,
            sensitivity=(("乳房", "極高"), ("私處", "極高"), ("耳朵", "高")),
            wetness="濕潤", shame="輕微", exposure="中等",
        ),
        # The twins arrive together: 悠花's own card is her companion, seeded
        # at 95 (above the invite threshold, inside 至愛 with headroom), with
        # 悠奈 as the elder sister.
        starting_companions=(StartingCompanion("yuna_darknight", 95, "雙胞胎姊姊"),),
    ),
    "yuna_darknight": PlayerPreset(
        # Reconverted from tmp/story_settings/character/YunaDarknight.md: age
        # 16; story defense 92 exact, the story's 65/65 physical floor sits
        # under the elf minimum, and the remaining budget inflates magic
        # power above the story's 350 (the budget must be spent in full).
        "yuna_darknight", "悠奈", 16, 16, "elf", "ciaran",
        (("hp", 0), ("mp", 0), ("sp", 0), ("atk_phys", 0),
         ("agility", 0), ("defense", 22), ("magic_power", 415)),
        "防禦特化的魔力體質配點",
        active_skills=("divine_sexual_arts", "status_disguise"),
        passive_skills=(
            "fire_mastery", "dark_mastery", "divine_sexual_mastery",
            "reincarnation_boon_yuna", "body_enhancement", "flight",
            "defense_instinct",
        ),
        starting_items=(("dark_elf_kimono", 1),),
        sex="female",
        # Story's equipment: the kimono is the only worn item (no weapon, no
        # accessories).
        starting_equipment=("dark_elf_kimono",),
        persona=PresetPersona(
            identity=PresetIdentity(
                public="暗影谷村的年輕黑暗精靈、擁有罕見黑髮的性魔法天才",
                hidden="轉生者（前世為現代日本的女高中生）、極端性愛實踐者、性魔法主宰",
            ),
            personality=(
                "知性冷靜，即使在公共場合高潮，表情管理依然完美。享樂至上，追求更多、"
                "更強、更新鮮的快感，熱情真誠到近乎天真；每天都為轉生到這具玩不壞的"
                "黑暗精靈肉體而感恩。越在人多的場合狀態越好，注視越多魔法越華麗。對"
                "悠花有特別的執著，喜歡用魔法把她玩到崩潰，再溫柔抱緊她說「辛苦了」。"
                "說話語調溫和禮貌，優雅地說出下流詞彙，反差讓人目瞪口呆。"
            ),
            life_story=(
                "前世是表面知性優等生、私下沉溺極端性刺激的雙面女高中生，16 歲與妹"
                "妹悠花一同死於意外，轉生為暗影谷村黑暗精靈的新生兒。5 歲轉生特典「性"
                "魔法主宰」顯現，一道魔力讓悠花瞬間高潮失神；8 歲自如融合暗魔法與性"
                "魔法；10 歲在村中廣場疊加七層性魔法，持續高潮整個下午。12 歲起研究"
                "神之秘法的性愛系統，發現能創造不存在於物理法則中的快感；14 歲已是村"
                "中公認的性魔法天才。16 歲與悠花離開村子。她斷定人類的反應比精靈更有"
                "趣。"
            ),
            habit=(
                "公共場合坐下時從不刻意併攏雙腿，穿這樣就是要給人看的；思考時下意"
                "識以指尖輕觸陰蒂，這個動作早已自動化；每晚睡前用性魔法給自己疊加多"
                "重快感，在持續高潮中入睡。"
            ),
            appearance=PresetAppearance(
                height="165 公分",
                weight="49 公斤",
                measurement="胸圍 88（D 罩杯）、腰 58、臀 86",
                style="罕見黑髮的知性黑暗精靈",
                overview=(
                    "褐色健康膚色，極罕見的黑色長直髮瀑布般垂至腰際，紫色眼眸沉靜溫"
                    "和，施法時浮現專注的狂熱；身材勻稱玲瓏，尖耳從黑髮間探出。"
                ),
                attire="基亞蘭族墨黑傳統服飾，遊女和服基底的短和服剪裁，前襟敞開、裙襬極短。",
                feature=(
                    "黑長直髮是精靈族中最顯眼的標誌；施展性魔法時，暗紫色魔力紋路沿"
                    "脊椎蔓延至腰際。"
                ),
            ),
            social_connection=(
                ("悠花", "雙胞胎妹妹、前世的性伴侶、此世最喜歡的實驗對象；互稱「悠花」「悠奈」。深愛著她，愛的表現方式是把她玩到死去活來"),
            ),
            background=(
                "與雙胞胎妹妹一同離開暗影谷村的黑暗精靈，罕見的黑長髮與知性外表之下，"
                "是將性魔法鑽研到極致的享樂主義者。精通火與闇屬性，"
                "並以神之秘法觸及性愛系統的領域。"
            ),
        ),
        # Story's disguise layer: 30 across magic and all three physical axes.
        disguised_stats=(("magic_power", 30), ("atk_phys", 30),
                         ("agility", 30), ("defense", 30)),
        sexual_baseline=PresetSexualBaseline(
            arousal="微興奮", virgin=False,
            sensitivity=(("乳房", "極高"), ("私處", "敏感異常"), ("耳朵", "高")),
            wetness="泛濫", shame="無", exposure="極高",
        ),
        # The symmetric half of the pair: 悠奈 arrives with 悠花, the younger
        # twin, at the same affinity.
        starting_companions=(StartingCompanion("yuka_darknight", 95, "雙胞胎妹妹"),),
    ),
    "elosia_shadowmoon": PlayerPreset(
        # Pre-meeting Elosia: the phantasm elf who just left the village and
        # walked into the human world ALONE -- not yet registered at the guild,
        # Violet not yet met, no disciple, no party name. Reconverted from
        # tmp/story_settings/character/ElosiaShadowmoon.md:
        # species is 伊歐拉斯族 (eolas, Phantasm Elf), age 10/apparent 10 (she
        # CLAIMS 222; the persona prose carries the lie). Story statics
        # 70/70/95 exact; the story's 873 magic exceeds the creation ceiling,
        # so the full remaining budget lands at the 512 maximum the budget
        # allows.
        "elosia_shadowmoon", "伊洛希雅", 10, 10, "elf", "eolas",
        (("hp", 0), ("mp", 0), ("sp", 0), ("atk_phys", 0),
         ("agility", 0), ("defense", 25), ("magic_power", 412)),
        "防禦滿值、魔力極高的魔導師配點",
        active_skills=("dominion_art", "status_disguise"),
        passive_skills=(
            "wind_mastery", "light_mastery", "body_enhancement",
            "defense_instinct", "flight", "reincarnation_boon_elosia",
        ),
        starting_items=(("elven_traditional_robe", 1), ("crescent_earring", 1)),
        sex="female",
        # Story's equipment: the robe and the crescent earring are worn.
        starting_equipment=("elven_traditional_robe", "crescent_earring"),
        persona=PresetPersona(
            identity=PresetIdentity(
                public="離開精靈村的年輕冒險者、自稱經驗豐富的魔法師",
                hidden="轉生者（前世為現代日本的普通女高中生）",
            ),
            personality=(
                "表面以「精靈文化傳統」為由穿著暴露，實際刻意利用人類對精靈的尊敬滿"
                "足露出癖；對外純潔無辜、心機深沉，如夢似幻的可愛外表讓人心癢難耐又不"
                "敢冒犯。被質疑穿著時，會用「這是我族的文化」義正辭嚴地反駁；放鬆時會"
                "無意識自慰。最大快感來自「做不該做的事但沒人能阻止」；處女之身是她最"
                "後的道德底線，罪惡感是最大的春藥；享受用文化話語權讓人類不得不看、又"
                "不敢說話。"
            ),
            life_story=(
                "0 歲誕生時保留前世全部記憶，對精靈村落「裸露即日常」的文化既困惑又"
                "興奮。8 歲起固定參與村中群交活動；10 歲身體發育完成，以「尋找命定之"
                "人」為由離開幽月谷村，謊稱 222 歲，由於人族看不出幻童精靈的年齡而被"
                "相信。轉生特典讓她的魔法成長是伊歐拉斯族平均的百倍，打發時間學的魔法"
                "已達 873 級。剛離村不到一個月，獨自走進人類城鎮，發現人族對精靈的"
                "尊敬讓她得以名正言順地暴露，於是盤算著隱藏實力、先當個普通魔法師"
                "遊玩一陣。"
            ),
            habit=(
                "思考時無意識以指尖揉捏乳頭；交談時手自然放在衣襬邊緣，帶著暗示；公"
                "共場合從不刻意併攏雙腿；每次感受到他人投來的目光，下體就會自然分泌"
                "愛液。"
            ),
            appearance=PresetAppearance(
                height="135 公分",
                weight="28 公斤",
                measurement="胸圍 78（C 罩杯）、腰 54、臀 80",
                style="清純幼女外表與性成癮肉體的強烈反差",
                overview=(
                    "外表僅 10 歲左右的幻童精靈，銀白長髮及臀，紫羅蘭色大眼睛清澈透"
                    "亮；身材嬌小但胸部發育飽滿，乳頭與私處呈深粉色，身上散發淡淡花香。"
                ),
                attire="極簡的白色半透明蛛絲編織幻童精靈傳統服飾，托胸式設計與前短後長白紗裙，私處完全暴露。",
                feature=(
                    "左耳佩戴精靈族月牙形耳環；孩童般纖瘦的外表卻有超齡成熟的曲線，"
                    "容易喚起他人的背德感。"
                ),
            ),
            social_connection=(),
            background=(
                "自稱兩百二十二歲的幻童精靈術師，實際年齡只有十歲，精通風與光的主宰"
                "級魔法，也掌握統御術與狀態偽裝。她剛離開幽月谷村、獨自走入人類王國，"
                "表面理由是「想看看短壽者們如何過日子」，實則貪戀人族對精靈的尊敬所"
                "允許的、名正言順的暴露。她還沒進公會，也沒有遇上任何人。"
            ),
        ),
        # Story's disguise layer: magic 120, physical 50, agility 50, defense 30.
        disguised_stats=(("magic_power", 120), ("atk_phys", 50),
                         ("agility", 50), ("defense", 30)),
        sexual_baseline=PresetSexualBaseline(
            arousal="微興奮", virgin=True,
            sensitivity=(("乳房", "極高"), ("私處", "極高"), ("耳朵", "高")),
            wetness="濕潤", shame="成癮", exposure="極高",
        ),
        # Pre-meeting: she travels alone -- no disciple, no party yet.
        starting_companions=(),
    ),
}
