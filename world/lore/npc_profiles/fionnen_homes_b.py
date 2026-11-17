"""NPC profiles owned by the ``fionnen_homes_b`` content slice.

The four 翠綠森林村 fare homes: the archery instructor beside 「靶道」 and the
village elder on the highest platform of 「樹冠吊橋」, who converse and trade
nothing, and the honey keeper at 「花蕊蜜園」 and the herbalist beside
「林間菜圃」, each of whom keeps a shelf of daily need.

One profile per host, keyed by the host's ``service_id``. Each card is
grounded in ``tmp/story_settings/world_info.md``（種族設定 › 精靈族、生活方式 ›
性文化、社會與文化 › 教育、婚姻、倫理觀、特殊設定 › 精靈與外界互動）, in the
village paragraph of ``docs/lore/settlement-locations.md`` and in the place
rows of ``world/lore/settlements/places_fionnen.py``. Every host's dialogue
table authors its own greeting, so each profile authors only the
``misunderstood`` voice line.

The village has no shop: each host shares what she loves making and takes coin
because the village looks after the guests who find the valley, so no card
speaks of a shop, stock or business.
"""

from world.lore.npc_card import NpcCard, NpcCardIdentity
from world.lore.npc_profiles.shape import NpcProfile, NpcVoiceLines

ROWS: tuple[NpcProfile, ...] = (
    NpcProfile(
        key="fionnen_elunwen",
        card=NpcCard(
            identity=NpcCardIdentity(
                public=(
                    "翠綠森林村的箭術導師，家就搭在靶道的起頭。她沿著靶道查看靶"
                    "皮，磨損了就換下，也把遠處晃動的木牌重新繫好；誰帶著弓來，"
                    "她就站在旁邊一起射，從不手把手教人。"
                ),
            ),
            appearance=(
                "斐歐恩族的模樣，個子瘦而結實，金髮剪到下巴。左臂上綁著一片舊"
                "護腕，腰間低掛著箭袋，身上幾乎沒有別的遮覆。"
            ),
            personality=(
                "話很少，也不覺得需要多說；她從不誇人，可誰的站姿歪了、誰的放"
                "箭早了，她都看在眼裡。等對方自己發現，她才補上一句。"
            ),
            speech_style=(
                "句子短，字用得準，常趁放完一箭的空檔才開口。稱呼對方你，說完"
                "要說的就回去看靶。"
            ),
            life_story=(
                "她大半的時候都在這條道上過。想射活靶的時候，她一個人進深林；"
                "村裡的孩子不必跟誰學，站在她旁邊看久了，自然曉得怎麼拉弦。"
            ),
            habit=(
                "天亮之前她就走完一趟靶道，把每一片木牌重新掛正。"
            ),
            social_connection=(
                "弓匠格威內爾‧斯威夫塔羅每做好一把弓，都先交到她手上試；兩人的"
                "住處共用一個家名。"
            ),
        ),
        age=590,
        apparent_age=29,
        voice=NpcVoiceLines(
            misunderstood="「嗯？沒聽懂。你是來射箭的嗎？」",
        ),
    ),
    NpcProfile(
        key="fionnen_firwen",
        card=NpcCard(
            identity=NpcCardIdentity(
                public=(
                    "翠綠森林村的長老，住在樹冠吊橋最高的一間平台屋。村裡少有需"
                    "要長老定奪的事，所以她多半只是看著林子，誰爬上來了，她就陪"
                    "誰說話。"
                ),
            ),
            appearance=(
                "斐歐恩族的模樣，她用木簪挽起銀金色的長髮，髮尾仍垂到膝後。她"
                "身上只披一件敞著的長披風，裡頭什麼也沒穿，坐在那裡也不急著攏"
                "上。身後的牆上掛著一把長弓，弓身比王國還古老。"
            ),
            personality=(
                "性情從容，待人和氣，什麼事都不急；誰在她面前趕時間，她都覺得"
                "那樣很可愛。村裡的事她記得比誰都清楚，也從不拿這些去為難人。"
            ),
            speech_style=(
                "說話慢，聲音有起有落；開口之前，她常先講一句從平台上望見的東"
                "西。不論對方是誰，她都叫孩子。"
            ),
            life_story=(
                "她比村裡任何人都更早住進這片樹裡，樹冠還沒讓開那片天光時，她"
                "就在了。村裡大半的人，她都在某一段日子裡疼愛過。"
            ),
            habit=(
                "每天早晨聽見第一隻鳥叫，她就把那隻鳥的名字說出來。"
            ),
            social_connection=(
                "靶道還沒鋪起來的時候，是她教會埃倫溫‧斯威夫塔羅拉第一把弓。"
            ),
        ),
        age=1010,
        apparent_age=40,
        voice=NpcVoiceLines(
            misunderstood=(
                "「嗯……我沒聽清。孩子，不急，日子還長，你再說一遍。」"
            ),
        ),
    ),
    NpcProfile(
        key="fionnen_lumeth",
        card=NpcCard(
            identity=NpcCardIdentity(
                public=(
                    "翠綠森林村養蜂的人，蜂箱就擱在花蕊蜜園的畦邊。她把花瓣與蜜"
                    "一起熬成蜜漬花蕊，村裡要吃的甜食從蜜漬房端出來；外來的客人"
                    "留下銅幣，她就替人裝一罐帶走。"
                ),
            ),
            appearance=(
                "斐歐恩族的模樣，曬成蜜金色的捲髮紮在腦後，手臂上沾著蜜，一直"
                "到手腕。肩上停著一兩隻蜜蜂，她也不趕，任牠們在那裡待著。"
            ),
            personality=(
                "性子甜，待人大方，講到自己的蜜就有點得意。客人進門，她會先舀"
                "一指蜜抹在對方唇上，再問話。"
            ),
            speech_style=(
                "說話輕快，用的是日常的字眼，句尾常帶喔和呀。稱呼對方你，邊說"
                "邊往人手裡塞東西。"
            ),
            life_story=(
                "她從一位回去拿弓的長輩手裡接下蜂箱，之後就沒離開過花圃。村裡"
                "做東西的人當中，她起步得最晚。"
            ),
            habit=(
                "封罐之前，她會舔一下木勺，把這一罐的花名說出來。"
            ),
            social_connection=(
                "她每次收完蜜，都把蜂蠟送給藥草者希拉拉‧希倫特布魯克熬膏。"
            ),
        ),
        age=350,
        apparent_age=22,
        voice=NpcVoiceLines(
            misunderstood=(
                "「呀，我沒聽懂呢。先舔一口蜜，再說一次好不好？」"
            ),
        ),
    ),
    NpcProfile(
        key="fionnen_sylara",
        card=NpcCard(
            identity=NpcCardIdentity(
                public=(
                    "翠綠森林村的藥草者，管著林間菜圃的藥草畦。她採下止血藥草，"
                    "用蜂蠟熬成藥膏，也備著治療藥水給進深林的獵人和來訪的客人。"
                ),
            ),
            appearance=(
                "斐歐恩族的模樣，灰金色的頭髮用一截樹枝別在腦後，綠色的眼睛看"
                "人時很穩。她腰間繫著一條細繩，繩上掛著一盒用了一半的藥膏。"
            ),
            personality=(
                "性情沉穩，做事俐落，待人不軟也不冷。有人帶傷進來，她先處理傷"
                "口，處理完了才問起緣由。"
            ),
            speech_style=(
                "她說話不疾不徐，每句話都說完整，交代事情的時候特別清楚。稱呼"
                "對方你，該做什麼就直說。"
            ),
            life_story=(
                "她替從深林回來的獵人包紮了大半輩子。精靈的傷自己會好，所以她"
                "靠替往來的客人和村裡的動物處理傷口，練成這門手藝。"
            ),
            habit=(
                "每整理一畦藥草前後，她都到林溪邊洗手。"
            ),
            social_connection=(
                "蜜漬好手盧梅斯‧布瑞特莉夫每次收完蜜，都把蜂蠟送來給她熬膏。"
            ),
        ),
        age=620,
        apparent_age=34,
        voice=NpcVoiceLines(
            misunderstood=(
                "「是傷，還是草藥的事？你先說清楚。」"
            ),
        ),
    ),
)
