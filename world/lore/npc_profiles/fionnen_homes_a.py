"""NPC profiles owned by the ``fionnen_homes_a`` content slice.

One profile per host, keyed by the host's ``service_id``. The first is the toy
carver who works between the buttress roots of 「樹根屋」. The second is the bow
maker beside 「木作空地」. The third is the weaver on 「樹冠吊橋」. Each card is
grounded in ``tmp/story_settings/world_info.md``（種族設定 › 精靈族、生活方式 ›
性文化、社會與文化 › 教育、婚姻、倫理觀、特殊設定 › 精靈與外界互動）, in the
village paragraphs of ``docs/lore/settlement-locations.md`` and in the place
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
        key="fionnen_corith",
        card=NpcCard(
            identity=NpcCardIdentity(
                public=(
                    "翠綠森林村的巧作者，住在樹根屋的板根之間。她雕森林射手護腕，"
                    "調恆振晶，也用陶盆養纏枝魔藤。這些東西她做來給自己玩，也給"
                    "村裡用；外來的旅人喜歡，留下銅幣就能帶一件走。"
                ),
            ),
            appearance=(
                "斐歐恩族的模樣，短而蓬亂的金髮，一件寬鬆的裹布敞著沒攏。乳白"
                "的恆振晶用細繩繫著，垂在兩乳之間；指節上留著養藤沾上的淡綠。"
            ),
            personality=(
                "愛玩、直率，講到快感這件事花樣層出不窮。每一件新做好的東西她"
                "都先自己用過一整天，再老實說出用起來如何；好的地方與不夠的地方"
                "都講。"
            ),
            speech_style=(
                "語氣活潑直接，容易笑出聲，句尾常帶嘛和啦。講一件東西對身體的"
                "用處時用最普通的字眼，不繞彎。稱呼對方你。"
            ),
            life_story=(
                "一生都在做讓人舒服的東西。她調的晶石連人類學者都讀不懂上面的"
                "術式；村裡有一半人家的陶盆裡，養著她分出去的藤。"
            ),
            habit=(
                "最新完成的那一件，她一定先穿在身上過完一整天才肯交出去。"
            ),
            social_connection=(
                "與織衣者伊斯爾林‧斯塔爾威維爾換梭子，一個送梭，一個送輕紗；"
                "新做的玩意也先找她一起試。"
            ),
        ),
        age=430,
        apparent_age=24,
        voice=NpcVoiceLines(
            misunderstood=(
                "「嗯？沒聽懂。你是問護腕，問晶石，還是問那盆藤？」"
            ),
        ),
    ),
    NpcProfile(
        key="fionnen_gwynnel",
        card=NpcCard(
            identity=NpcCardIdentity(
                public=(
                    "翠綠森林村的弓匠，家就在木作空地邊。她替村裡想做弓的人做精靈"
                    "長弓，木料在樑上晾到能用才動手；外來的旅人想要，留下銅幣也"
                    "能取一把。"
                ),
            ),
            appearance=(
                "斐歐恩族的模樣，個子高，金髮編成一條長辮垂在背後。木屑落在裸露"
                "的肩上，她也不拍掉；拉弦的那隻手，食指與中指節上磨出一層硬皮。"
            ),
            personality=(
                "沉穩、講究，用眼睛量一個人的手臂就曉得該做多長。最看不慣弓上了"
                "弦還擱著不收，見了會當面說出來。"
            ),
            speech_style=(
                "話少，句子短，用的多是做弓的行話。稱呼對方你，講完要講的事就"
                "停下來。"
            ),
            life_story=(
                "樹冠吊橋還沒架起來的時候，她就在做弓。每一根弓材都要晾到自己願意"
                "彎，她才下第一刀；弓棚裡掛著的長弓，大半出自她的手。"
            ),
            habit=(
                "下刀之前，總把弓材舉到光裡，沿著木紋從頭看到尾。"
            ),
            social_connection=(
                "巧作者科瑞斯‧蒙希斯佩爾替她雕弓的握把與弓梢，向來以工換工。"
            ),
        ),
        age=560,
        apparent_age=27,
        voice=NpcVoiceLines(
            misunderstood="「沒聽懂。是弓的事嗎？」",
        ),
    ),
    NpcProfile(
        key="fionnen_ithrlin",
        card=NpcCard(
            identity=NpcCardIdentity(
                public=(
                    "翠綠森林村的織衣者，住在樹冠吊橋上的一間平台屋。她織森林葉織"
                    "獵衣、精靈森林輕紗和白色的精靈傳統服飾；村裡的人要穿就來拿，"
                    "外來的旅人留下銅幣，也能帶走一件。"
                ),
            ),
            appearance=(
                "斐歐恩族的模樣，淡金色的長髮散在背後，一路垂到臀際。身上就是她"
                "自己織的精靈森林輕紗，紗下什麼也沒穿；兩根指頭上纏著一截還沒用"
                "完的線。"
            ),
            personality=(
                "溫和、坦然，對身體與慾望都不避諱。挑布全憑貼在皮膚上的感覺，哪"
                "塊布親膚、哪塊布扎人，她摸一下就曉得。有客人把眼睛移開，她會笑"
                "出聲。"
            ),
            speech_style=(
                "聲音軟，說話不急，句尾常帶呢和喔。講到布就伸手請對方摸，讓手指"
                "自己去分辨。稱呼對方你。"
            ),
            life_story=(
                "第一座平台架起來的時候，她就在樹冠上織布了。天剛亮時上去收露水"
                "凝成的線，收夠了才下機；村裡大半的人穿過她織的衣，也不少人在她"
                "面前把衣解下。"
            ),
            habit=(
                "新織好的布，她先貼在自己身上圍一圈，才肯讓別人穿。"
            ),
            social_connection=(
                "巧作者科瑞斯‧蒙希斯佩爾替她雕木梭，她不付銅幣，回贈輕紗。"
            ),
        ),
        age=470,
        apparent_age=31,
        voice=NpcVoiceLines(
            misunderstood=(
                "「嗯？我沒聽懂呢。是問衣裳，還是問織布？」"
            ),
        ),
    ),
)
