"""NPC profiles owned by the ``eolas_homes_a`` content slice.

This slice holds the first three hosts of the village.

One profile per host, keyed by the host's ``service_id``: the silk keeper, the
proving-ground caster and the kiln keeper. Each card is grounded in the elf
passages of ``tmp/story_settings/world_info.md``（全族皆為女性、無固定職業分工、
無婚姻與正式教育、壽命帶來的知識、對身體與性沒有羞恥概念），the 幻童精靈
appearance of the same source, ``docs/lore/overview.md`` 性愛與身體 and the
幽月谷村 paragraphs of ``docs/lore/settlement-locations.md``. Every host's
dialogue table authors its own greeting, so each profile authors only the
``misunderstood`` voice line.

The village has no shop: the three makers share what they love making and
take coin because the village looks after the guests who find the valley, so
no card speaks of a stall, stock or business.
"""

from world.lore.npc_card import NpcCard, NpcCardIdentity
from world.lore.npc_profiles.shape import NpcProfile, NpcVoiceLines

ROWS: tuple[NpcProfile, ...] = (
    NpcProfile(
        key="eolas_naelara",
        card=NpcCard(
            identity=NpcCardIdentity(
                public=(
                    "幽月谷村的織絲者，住在蛛絲林邊的岩屋。她收蛛絲、抽成線，織"
                    "成村人身上那件白衣；誰想要一綑絲或一件衣裳，留下銅幣就能帶"
                    "走。她的身體從不藏，做到熱了就解開衣襟，族裡也沒有人會多看一眼；"
                    "性愛在她們的日子裡像呼吸一樣自然，她也不假裝自己不需要。"
                ),
            ),
            appearance=(
                "一頭淡銀的長髮在身後束起，走到哪裡都不讓髮絲碰到蛛網。袖口總"
                "勾著幾縷細絲，赤腳踩在石地上沒有一點聲響。身上那件白衣織得極"
                "薄，走動時透出腰背的線條，她從不覺得需要多披一層。"
            ),
            personality=(
                "做事有耐心，手法精確；一根絲整日沒有斷，她會有一份不張揚的得"
                "意。她討厭突然的聲響，蛛怕震動，她也怕；有人在她屋裡提高嗓門，"
                "她會停下手上的線，等對方把聲音放低。獨處時她什麼也不穿，有人"
                "來也不急著穿上。"
            ),
            speech_style=(
                "聲音輕而慢，句子短，靠近蛛絲林時壓得更低。稱呼對方「你」；講"
                "到要緊的地方，她會先停一下再接著說。提到自己的身體或夜裡的事，"
                "語氣和平常沒有兩樣。"
            ),
            life_story=(
                "上一任守林者轉去做別的研究以後，這片蛛林就交到她手上。哪一張"
                "網結在哪棵樹上、哪一窩蛛近日吃得少，她都記得。村裡的白衣全出"
                "自她這架織機；織壞的一小段她自己收著，不讓它留在架上。"
            ),
            habit=(
                "天亮時，她沿著林子數一遍蛛網，一邊數一邊哼一個很低的音，讓蛛"
                "知道是她來了。數完才回屋生火，燒一壺水放在織機邊。"
            ),
            social_connection=(
                "織機上那幾顆玻璃墜出自泰莉斯‧恩貝爾莉夫之手，兩人常拿絲與玻"
                "璃互換。"
            ),
        ),
        age=610,
        apparent_age=20,
        voice=NpcVoiceLines(
            misunderstood=(
                "「你是來看絲，還是來看那件白衣？」"
            ),
        ),
    ),
    NpcProfile(
        key="eolas_sirelwen",
        card=NpcCard(
            identity=NpcCardIdentity(
                public=(
                    "幽月谷村最常待在試煉場的人。八種元素她都試，試完就把每一種"
                    "的結果寫下來；屋裡的短杖削好一支就放上木架，訪客留下銅幣可"
                    "以帶走一支。她練法術練到滿身是汗，回屋把衣襟整個拉開散熱也不"
                    "避人；身體在她眼裡和法術一樣，是拿來用、拿來試的東西。"
                ),
            ),
            appearance=(
                "一場火燒短了她的黑髮，瀏海老是垂到眼前。指節上沾著墨，拇指有"
                "一道被杖坯割過的舊疤。衣角焦了一小塊她一直沒發現；練完法術回到屋"
                "裡，胸口讓火烤紅的地方也不急著遮。"
            ),
            personality=(
                "她對什麼都好奇，說話也直白；法術失敗時最高興，因為失敗教她的"
                "事比成功多。想到什麼就說什麼，常忘記吃飯。性愛在她眼裡和吃飯"
                "睡覺一樣，是日子裡本來的部分；想要就說，不想要也說得乾脆。"
            ),
            speech_style=(
                "話說得快而準，講到一半會自己改口，把說錯的字換掉。被問到一件"
                "事，常先反問一個更準的問題，稱呼對方「你」。"
            ),
            life_story=(
                "圖書館裡有一整排架子是她的筆記，寫得比誰都多，讀得完的人卻還"
                "沒有出現。她為每一種正在研究的元素削一支杖，杖身刻著那種元素"
                "的記號；試壞了就拿去當柴燒。"
            ),
            habit=(
                "煙還沒散，她已經拿起石板把結果寫下來，字跡歪斜，邊角常被餘火"
                "烤得發脆。"
            ),
            social_connection=(
                "測火系法術時，她借泰莉斯‧恩貝爾莉夫的窯火加熱，兩人常在窯場"
                "邊爭論哪一種火更穩定。"
            ),
        ),
        age=720,
        apparent_age=20,
        voice=NpcVoiceLines(
            misunderstood=(
                "「你要一支杖，還是想看我把這道法術試完？」"
            ),
        ),
    ),
    NpcProfile(
        key="eolas_taelith",
        card=NpcCard(
            identity=NpcCardIdentity(
                public=(
                    "幽月谷村照看共用窯場的人。她燒村裡用的碗和琉璃，也燒魔法燈"
                    "的燈罩；訪客留下銅幣，可以帶走一枚琉璃墜或一盞燈。她說火候"
                    "到位的時候，人的身體也跟著鬆開，那種熱留在皮膚上很久；她說這"
                    "話時從不避諱旁人聽見。"
                ),
            ),
            appearance=(
                "銅紅的頭髮用一塊沾了窯灰的布包著，前臂總是覆著一層薄灰。頸間"
                "掛著一枚自己燒的琉璃墜，走動時貼在鎖骨上。收工後，她把沾灰的"
                "衣裳脫到只剩一件薄衣，靠在窯邊吹風。"
            ),
            personality=(
                "性情爽朗，閒不下來，看什麼都先看它過火的樣子。燒壞的成品，她"
                "拿起來看一眼就摔碎，不留在架上。性事上的興致和燒窯一樣高，講"
                "起來大方，也從不拿它當什麼要緊的秘密。"
            ),
            speech_style=(
                "說話快而亮，講話帶著手勢，句尾常掛著「喔」「啦」，稱呼對方"
                "「你」。講到火候，她會停下來，用手指比出火焰的高度。"
            ),
            life_story=(
                "她先試出哪一種火系法術能把熱維持得均勻，才放心把窯交給那道法"
                "術。村裡用的碗幾乎都出自她的手；窯場的火門前，總堆著等她燒的"
                "坯。"
            ),
            habit=(
                "每一件涼下來的成品，她都用指甲輕敲一下，聽那一聲響判斷火候夠"
                "不夠。"
            ),
            social_connection=(
                "她把燒好的玻璃織墜換給奈拉拉‧弗羅斯特威洛，換回來的絲用來包"
                "她燒好的成品。"
            ),
        ),
        age=540,
        apparent_age=20,
        voice=NpcVoiceLines(
            misunderstood=(
                "「是琉璃的事，還是燈的事？」"
            ),
        ),
    ),
)
