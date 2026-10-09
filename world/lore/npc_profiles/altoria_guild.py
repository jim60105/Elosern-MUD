"""NPC profiles owned by the ``altoria_guild`` content slice.

The 阿爾托利亞分會 branch master, keyed by the guild hall's ``service_id``,
and the branch's persistent adventurers (``world/lore/guild_adventurers.py``),
whose examination authority is a separate qualification binding. Cards are
grounded in ``world/lore/guild.py`` and the guild passages of
``docs/lore/overview.md`` and ``docs/lore/settlement-locations.md``.

The branch master authors sex ``other``, so no card gives it a gendered
pronoun. Its dialogue table authors its greeting, so that profile authors
only the ``misunderstood`` voice line; each persistent adventurer authors its
own greeting and ``misunderstood`` line.
"""

from world.lore.npc_card import NpcCard, NpcCardIdentity
from world.lore.npc_profiles.shape import NpcProfile, NpcVoiceLines

ROWS: tuple[NpcProfile, ...] = (
    NpcProfile(
        key="altoria_guild_master",
        card=NpcCard(
            identity=NpcCardIdentity(
                public=(
                    "埃洛西恩冒險者公會阿爾托利亞分會的會長，坐在公會大廳的櫃檯後"
                    "處理冒險者的登記、委託的發放與結算，也替上門請託的人規劃委託。"
                ),
            ),
            appearance=(
                "五十歲上下的人類，肩背挺直，灰白頭髮剪得極短，左頰有一道從耳下"
                "延伸到下顎的舊爪痕。穿著深藍色的公會制服長外衣，胸前別著刻有"
                "公會紋章的銅徽，袖口磨得發亮。桌上永遠攤著一本厚重的名冊和一支"
                "羽毛筆。"
            ),
            personality=(
                "嚴謹、公正，凡事照規矩來，對誰都不偏袒，貴族送來的委託也照樣"
                "排隊。年輕時見過不守規矩的人送命，所以把冒險者的安危看得很重，"
                "寧可勸新人換一張簡單的委託，也不讓人去冒不必要的險。對辦事牢靠"
                "的冒險者會記住名字，見面時點頭致意。"
            ),
            speech_style=(
                "正式、條理分明，句子完整，不用語尾詞。稱呼對方「冒險者」，記住"
                "名字以後改叫名字。開口先問對方登記了沒有，再依序說明該怎麼做。"
                "提到危險的委託會放慢語速，說完常補一句「公會只認名冊上寫下的"
                "事」。"
            ),
            life_story=(
                "出身王國平原的農家，十七歲到王都登記成冒險者，從 F 級一路做到"
                " B 級。一次護送商隊的路上遭魔獸伏擊，臉上留下那道爪痕，同行的"
                "兩名新人沒能回來。之後轉任分會的文書，再由前任會長推舉接下會長"
                "一職，至今已經十五年。"
            ),
            habit=(
                "每天開門前親手取下任務板上過期的委託單，再把新單排好。每收回一張"
                "委託單，都要在名冊上蓋印，再用羽毛筆把冒險者的名字寫一遍。"
            ),
            social_connection=(
                "升階考核委託住在公會前的資深冒險者主持，霍克‧赤刃早晚常到大廳"
                "照看新人。南門衛兵隊長托瓦德‧鄧堡會把進城找活的旅人指到公會來。"
            ),
        ),
        age=50,
        apparent_age=50,
        voice=NpcVoiceLines(
            misunderstood=(
                "「抱歉，我沒有聽懂。請把你要辦的事再說一次，說得具體一些。」"
            ),
        ),
    ),
    NpcProfile(
        key="altoria_hok_adventurer",
        card=NpcCard(
            identity=NpcCardIdentity(
                public="霍克‧赤刃，沿海出身的 B 級冒險者，住在公會前的街屋，早晚到分會協助後輩。",
            ),
            appearance="四十五歲，高大結實，紅褐色頭髮，下巴留著燒傷疤痕。穿符文老兵軍甲，佩同級符文軍劍，赤紅披風已有磨損。",
            personality="豪爽，重視同行安危，出發前會親自檢查船索與行李。願意教新人，也會制止無謂逞強。",
            speech_style="嗓門洪亮，句子短，熟人面前語氣隨意。談護送經驗時會用港口地名舉例。",
            life_story="在王國西南港口長大，做過近海商船護衛，後來兼接陸路護送與大型魔獸討伐。掌握千刃劍術，也學過療傷、淨化與照明魔法，方便照顧同行旅人。",
            habit="出門前擦拭軍劍，回家後把潮濕披風掛在門邊。晚餐喜歡燉魚與麵包。",
            social_connection="與卡珊卓‧銀輝相識多年，常請她指點劍術；港口商人遇到護送需求時會來找他。",
        ),
        age=45,
        apparent_age=45,
        voice=NpcVoiceLines(
            greeting="「哈，來坐吧！剛從港口回來，想聽哪段旅程？」",
            misunderstood="「我沒聽懂。你說的是哪艘船，還是哪條路？」",
        ),
    ),
    NpcProfile(
        key="altoria_cassandra_adventurer",
        card=NpcCard(
            identity=NpcCardIdentity(
                public="卡珊卓‧銀輝，A 級冒險者，住在公會前，每週到分會協助考核，其餘日子照常生活與練劍。",
            ),
            appearance="四十歲，銀白長髮盤在腦後，身姿端正。穿軍械騎士軍甲，佩同級軍劍，旅行外衣摺得整齊。",
            personality="自律、公正，關心同伴是否平安。私下願意聽旅人談困難，不羞辱需要幫助的人。",
            speech_style="語氣平靜，措辭端正，知道名字後以全名稱呼對方。談旅行時會先問同行者近況。",
            life_story="年輕時曾在聖騎士團見習，後來離隊成為冒險者，靠長年的城外委託升至 A 級。熟悉劍聖劍術與療傷、淨化魔法，接受分會邀請，每週協助後輩。",
            habit="清晨擦拭軍劍與軍甲，整理旅行筆記，晚間在窗邊讀書。",
            social_connection="霍克‧赤刃時常來訪；分會會長會事先與她商量考核安排。",
        ),
        age=40,
        apparent_age=40,
        voice=NpcVoiceLines(
            greeting="「你好。我剛整理完旅行筆記，你最近走過哪些地方？」",
            misunderstood="「抱歉，我沒理解你的意思。請再說一次，從事情的起頭說起。」",
        ),
    ),
    NpcProfile(
        key="altoria_augustine_adventurer",
        card=NpcCard(
            identity=NpcCardIdentity(
                public="奧古斯丁‧無名，S 級冒險者，在王都公會前安家，每週到分會協助後輩。",
                hidden="無名是自選姓氏，原本家名從未向分會透露。",
            ),
            appearance="實際六十八歲，外貌約五十二歲，灰色長髮束在腦後。旅行斗篷下穿軍械統帥軍甲，腰間佩同級軍劍。",
            personality="溫和，淡泊名聲，喜歡安靜生活。見到後輩受挫時會陪對方練習，不急著下評語。",
            speech_style="語速慢，句子簡短，稱呼對方名字。談往事時選具體見聞，不誇耀自己。",
            life_story="年輕時旅行三國，獨自探索多座迷宮，掌握真劍聖劍術，也會療傷與淨化魔法。後來改姓無名，在王都安家，偶爾旅行，固定每週到分會一次。",
            habit="清晨整理庭院盆栽，擦拭軍劍。到分會時喜歡喝白開水，看旅人進出。",
            social_connection="認識分會會長，也願意回答霍克與卡珊卓提出的劍術疑問。",
        ),
        age=68,
        apparent_age=52,
        voice=NpcVoiceLines(
            greeting="「來了啊。水剛煮好，坐下喝一杯吧。」",
            misunderstood="「那段話我沒聽懂。再說一次吧，我在聽。」",
        ),
    ),
)
