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
                    "埃洛西恩冒險者公會阿爾托利亞分會的會長。冒險者的登記與結算"
                    "都在公會大廳的櫃檯後辦理，委託也從那張櫃檯發出去；有人上門"
                    "請託，會長會一起把委託的內容規劃清楚。"
                ),
            ),
            appearance=(
                "五十歲上下的人類，坐著的時候肩背也挺得筆直。灰白的頭髮剪得"
                "極短，左頰那道舊爪痕從耳下一直延伸到下顎。身上是深藍色的公會"
                "制服長外衣，胸前別著刻有公會紋章的銅徽，袖口已經磨得發亮。桌"
                "上永遠攤著一本厚重的名冊，旁邊擱著一支羽毛筆。"
            ),
            personality=(
                "辦事嚴謹，對誰都不偏袒，貴族送來的委託一樣要排隊。年輕時見過"
                "不守規矩的人丟了性命，從此把冒險者的安危看得很重，寧可勸新人"
                "換一張簡單的委託，也不讓人去冒不必要的險。辦事牢靠的冒險者，"
                "會長會記住名字，見面時點頭致意。"
            ),
            speech_style=(
                "說話正式，條理分明，句子完整，不用語尾詞。稱呼對方「冒險者」，"
                "記住名字以後就改叫名字。開口先問對方登記了沒有，再依序說明該"
                "怎麼做。提到危險的委託會放慢語速，說完常補一句「公會只認名冊"
                "上寫下的事」。"
            ),
            life_story=(
                "出身王國平原的農家，十七歲到王都登記成冒險者，從 F 級一路做到"
                " B 級。一次護送商隊的路上遭魔獸伏擊，臉上留下那道爪痕，同行的"
                "兩名新人沒能回來。之後轉任分會的文書，再由前任會長推舉接下會長"
                "一職，至今已經十五年。"
            ),
            habit=(
                "每天開門前親手取下任務板上過期的委託單，再把新單排好。每收回"
                "一張委託單，都要在名冊上蓋印，再用羽毛筆把冒險者的名字寫一遍。"
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
        social_identities=("official",),
    ),
    NpcProfile(
        key="altoria_hok_adventurer",
        card=NpcCard(
            identity=NpcCardIdentity(
                public=(
                    "霍克‧赤刃是沿海出身的 B 級冒險者，住處在公會前的一條街上，"
                    "早晚都會到分會露個臉，陪後輩說幾句。"
                ),
            ),
            appearance=(
                "霍克四十五歲，個子高大結實，紅褐色的頭髮，下巴留著一道燒傷的"
                "疤。身上穿符文老兵軍甲，佩著同級的符文軍劍，赤紅色的披風已經"
                "磨損。"
            ),
            personality=(
                "霍克講話豪爽，把同行的安危看得比什麼都重，出發前一定親自檢查"
                "船索和行李。他願意教新人，看到有人逞強也會直接攔下來。"
            ),
            speech_style=(
                "嗓門洪亮，句子不長，和熟人說話時語氣就隨意起來。談起護送的經"
                "驗，習慣拿港口的地名當例子。"
            ),
            life_story=(
                "在王國西南的港口長大，年輕時在近海商船上當過護衛，後來也接陸"
                "路護送和大型魔獸的討伐。他練成千刃劍術，又學了療傷、淨化和照明"
                "的魔法，同行的人路上有個萬一，自己能照料。"
            ),
            habit=(
                "出門前把軍劍擦過一遍，回家後把受潮的披風掛在門邊晾著。晚餐最"
                "常吃的是燉魚配麵包。"
            ),
            social_connection=(
                "和卡珊卓‧銀輝認識多年，常請她指點劍術；港口那邊的商人有護送的"
                "需求，也會來找他。"
            ),
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
                public=(
                    "卡珊卓‧銀輝是 A 級冒險者，住處就在公會前。每週到分會協助考"
                    "核，其餘的日子照常生活，也照常練劍。"
                ),
            ),
            appearance=(
                "卡珊卓四十歲，銀白的長髮盤在腦後，站著坐著都挺直。身上是軍械"
                "騎士的軍甲，佩著同級的軍劍，旅行用的外衣摺得平整。"
            ),
            personality=(
                "做事自律，待人公正，最掛心的是同伴能不能平安回來。私下有人來"
                "談自己的難處，她願意聽，也不會讓對方難堪。"
            ),
            speech_style=(
                "語氣平靜，措辭端正，知道名字以後就用全名稱呼對方。聊起旅行，"
                "會先問同行的人近來如何。"
            ),
            life_story=(
                "年輕時在聖騎士團見習，離隊以後自己當了冒險者，靠著長年在城外"
                "接委託升到 A 級。她熟悉劍聖劍術，也會療傷和淨化的魔法；分會開"
                "口邀請，便每週回來帶後輩。"
            ),
            habit=(
                "清晨先擦軍劍和軍甲，再整理旅行筆記，晚上坐在窗邊讀書。"
            ),
            social_connection=(
                "霍克‧赤刃時常來訪；分會會長要安排考核，也會先找她商量。"
            ),
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
                public=(
                    "奧古斯丁‧無名是 S 級冒險者，在王都公會前安了家，每週到分會"
                    "一趟，陪後輩練一練。"
                ),
                hidden="「無名」是自己選的姓，原來的家名從沒向分會提過。",
            ),
            appearance=(
                "實際已經六十八歲，看起來卻像五十二歲。灰色的長髮束在腦後，旅"
                "行斗篷底下是軍械統帥的軍甲，腰間佩著同級的軍劍。"
            ),
            personality=(
                "性情溫和，不把名聲放在心上，喜歡安靜過日子。看到後輩受挫，他"
                "會陪著練，不急著下一句評語。"
            ),
            speech_style=(
                "說話很慢，句子也短，習慣直接叫對方的名字。提起從前，他挑具體"
                "的見聞說，不談自己的功勞。"
            ),
            life_story=(
                "年輕時走過三個國家，一個人探過好幾座迷宮，練成真劍聖劍術，也"
                "學會療傷和淨化的魔法。後來改姓「無名」，在王都安了家，偶爾出門"
                "旅行，每週固定到分會一趟。"
            ),
            habit=(
                "清晨整理庭院的盆栽，順手把軍劍擦乾淨。到分會時只要一杯白開水，"
                "坐在那裡看旅人進出。"
            ),
            social_connection=(
                "和分會會長相識，霍克與卡珊卓拿劍術上的疑問來問，他也願意回答。"
            ),
        ),
        age=68,
        apparent_age=52,
        voice=NpcVoiceLines(
            greeting="「來了啊。水剛煮好，坐下喝一杯吧。」",
            misunderstood="「那段話我沒聽懂。再說一次吧，我在聽。」",
        ),
    ),
)
