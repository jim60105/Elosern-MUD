"""NPC profiles owned by the ``eolas_homes_b`` content slice, the 幽月谷村 fare homes.

This slice holds the village's three fare homes: the herb keeper, the baker and
the elder.

One profile per host, keyed by the host's ``service_id``. Each card is grounded
in the elf passages of ``tmp/story_settings/world_info.md``（全族皆為女性、
無固定職業分工、無婚姻與正式教育、壽命帶來的知識、對身體與性沒有羞恥概念），
the 幻童精靈 passages of the same source, ``docs/lore/overview.md`` 性愛與身體，
the 幽月谷村 paragraphs of ``docs/lore/settlement-locations.md`` and the place
rows of ``world/lore/settlements/places_eolas.py``. Every host's dialogue table
authors its own greeting, so each profile authors only the ``misunderstood``
voice line.

The village has no shop: the makers share what they love making and take coin
because the village looks after the guests who find the valley, so no card
speaks of a stall, stock or business.
"""

from world.lore.npc_card import NpcCard, NpcCardIdentity
from world.lore.npc_profiles.shape import NpcProfile, NpcVoiceLines

ROWS: tuple[NpcProfile, ...] = (
    NpcProfile(
        key="eolas_nirnel",
        card=NpcCard(
            identity=NpcCardIdentity(
                public=(
                    "幽月谷村照看石階菜畦的人。她種香草，按時辰採收，再用慢火熬"
                    "成封好的藥露；誰累了或帶傷來，就在她屋裡取走一瓶。她記得每"
                    "一株香草的性子，哪一味配哪一味，聞一下就知道。"
                ),
            ),
            appearance=(
                "苔綠的頭髮壓在一頂草帽下，指甲縫裡留著泥土。腰間掛著一排塞好"
                "軟木的陶瓶，走動時彼此相碰。身上那件白衣洗得發白，袖口沾著草"
                "汁，蹲在菜畦裡常沾上一褲腳的泥。屋裡生著爐火的時候，她把衣襟鬆"
                "開，領口敞著，頸下一片皮膚和鎖骨露在暖光裡。"
            ),
            personality=(
                "性情沉靜，善於觀察，一眼就看出人身上哪裡累。熬藥從不趕時間，"
                "火候沒到就守著不走。她看草像看人，哪株渴了、哪株招了蟲，一眼"
                "就曉得；日子裡大半的時間都給了這片菜畦。她讀得懂身子哪種累是行"
                "路，哪種累是夜裡纏過了頭，說起性愛和說起藥草一樣平穩。"
            ),
            speech_style=(
                "聲音平穩柔和，句子說得完整，交代完一件事會在句尾帶個「喔」。"
                "稱呼對方「你」，講到藥材和時辰時語氣一樣平穩。"
            ),
            life_story=(
                "精靈不生病，她便轉去研究疲憊，想知道身子累到哪裡，魔力又散到"
                "哪裡。架上那幾本筆記寫的是哪一種草對哪一種疲憊有用，字跡越寫越密。"
            ),
            habit=(
                "採藥之前，她先把一片葉子夾在指間揉開，聞過氣味才動手。"
            ),
            social_connection=(
                "雷林‧莉特弗特每天早晨來取廚房用的香草。"
            ),
        ),
        age=660,
        apparent_age=10,
        voice=NpcVoiceLines(
            misunderstood=(
                "「你是累，還是傷？說明白，我才好替你挑。」"
            ),
        ),
    ),
    NpcProfile(
        key="eolas_raellin",
        card=NpcCard(
            identity=NpcCardIdentity(
                public=(
                    "幽月谷村愛做飯的人，住在岩屋坡。她在共用的窯場烤豆餅，有人"
                    "要上獸徑，她就替對方備一份帶走。做飯做到一身汗，她也不停；"
                    "誰路過她都會招呼進來吃一口，吃飽了才好上路。"
                ),
            ),
            appearance=(
                "蜜褐的頭髮編成兩條短辮，手肘以下沾著麵粉。腰間插著一塊木製的"
                "翻餅板，白衣上留著窯火的氣味。衣袖常挽到肩頭，前臂和頸子都讓窯"
                "火烘得微紅，做起事來毫不遮掩。"
            ),
            personality=(
                "性情溫暖，話也多，總是先餵飽來人再問來意。她對香草特別挑剔，"
                "差一點味道都嚐得出來。看到誰瘦了，她就多塞一份餅；累了就在共"
                "食棚的長椅上打個盹，醒來再烤一爐。她不害羞於被人親近，也坦白"
                "夜裡不愛一個人躺，吃飽、泡暖了身子，再鑽進誰的被窩都成。"
            ),
            speech_style=(
                "日常而爽朗，句子短，句尾常帶「喔」「嘛」。稱呼對方「你」，一"
                "面說一面把吃的往人手裡塞。"
            ),
            life_story=(
                "從前烤餅的人把手藝教給了她，之後她換過許多回香草的配法。"
                "共食棚的桌上每日有她烤的餅，要帶上獸徑的食糧，也從她這裡包。"
            ),
            habit=(
                "每一爐的第一張餅，她都掰成兩半先聞一聞。"
            ),
            social_connection=(
                "她的香草取自妮爾內爾‧德米多顧的石階菜畦。"
            ),
        ),
        age=380,
        apparent_age=10,
        voice=NpcVoiceLines(
            misunderstood=(
                "「先吃一口，邊吃邊說。你是餓了，還是有事要問？」"
            ),
        ),
    ),
    NpcProfile(
        key="eolas_saelnel",
        card=NpcCard(
            identity=NpcCardIdentity(
                public=(
                    "幽月谷村的長老，住在岩屋坡最老的一間石室。村裡少有要她裁斷"
                    "的事，她便讀書、回想從前，陪來的人說話。族裡的舊事她都記得，"
                    "哪一坡種過什麼、哪條溪改了道，她能講上半天。"
                ),
            ),
            appearance=(
                "白髮垂到腰間，隨手束著。灰色的眼睛很靜，手邊總有一本磨舊的"
                "書。身上那件白衣洗得極軟，她坐著的時候書就攤在膝上。"
            ),
            personality=(
                "性情從容，話裡帶著冷幽默，看人著急只覺得有趣。有人來討一"
                "句定奪，她常把話繞回一個問題。她記性好，講起往事不厭其煩，也"
                "樂意聽人說谷外的事。她講到族人把大半日子花在性愛上，語氣和說天"
                "氣沒有兩樣，從不避諱。"
            ),
            speech_style=(
                "說話慢，中間留著停頓。回答之前，她常從一件記得的小事說起；稱"
                "呼誰都是「孩子」。"
            ),
            life_story=(
                "她在這座谷裡待得比誰都久。圖書館的筆記她讀遍了，其中不少是她"
                "自己寫的；窯場砌起來、蛛絲林植下去，她都在場。"
            ),
            habit=(
                "每天傍晚讀一頁書出聲，屋裡沒有別人聽。"
            ),
            social_connection=(
                "希瑞爾溫‧布瑞特瓦特爾每次寫好新的筆記，都拿來問她從前試過沒有。"
            ),
        ),
        age=1040,
        apparent_age=10,
        voice=NpcVoiceLines(
            misunderstood=(
                "「我沒聽明白。不急，你從頭說一次就好。」"
            ),
        ),
    ),
)
