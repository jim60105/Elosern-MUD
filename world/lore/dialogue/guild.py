"""The adventure guild's authored dialogue row (the guild-hall counter).

One table: the ``guild_staff`` row spoken by the 阿爾托利亞分會 front-desk
clerk, keyed by the ``dialogue_key`` the guild-hall place row authors.

The clerk talks like a clerk, in 正體中文: guidance rides inside what the
person behind the counter would actually say, never a recited command
manual. Two shape rules bind authored rows here:

- Four keyword answers at most. The dialogue panel ships
  ``DIALOGUE_MAX_CHOICES`` entries and silently drops the rest, so a fifth
  keyword is a keyword the player can never press. This row carries
  exactly four.
- The strings stay load-bearing. The scripted-dialogue and
  guild-registration contracts pin substrings of this text (the `回報`
  keyword and the unregistered register-first fallback, and every
  ``guild <verb>`` command somewhere in the combined greeting and
  responses), and focused tests plus one browser flow match those
  substrings verbatim. Reword freely around them; never delete one.
"""

from world.lore.dialogue.shape import DialogueDefinition, KeywordResponse

# Exactly four answers, in panel order. Each is one clerk's spoken remark;
# the contract-pinned substrings ride inside the prose.
GUILD_STAFF_RESPONSES: tuple[KeywordResponse, ...] = (
    KeywordResponse(
        "註冊",
        "「先在櫃檯註冊成為冒險者（guild register），階級從F起——"
        "沒有名號的人，連那邊的任務板都碰不得。登記過了，這行飯"
        "才輪得到你吃。」",
    ),
    KeywordResponse(
        "任務",
        "「單子都釘在那頭的板上。你先 guild list 撿一張合階級的，"
        "喊一聲 guild accept 加任務名就領走。辦完了回這張櫃檯，"
        "對我說『回報』再報上編號，或是自己敲 guild turnin "
        "<任務編號> 交回，兩條路我都認；中途不想辦了，"
        "guild abandon 撒手便是。」",
    ),
    KeywordResponse(
        "公會",
        "「這裡是埃洛西恩冒險者公會，阿爾托利亞分會。櫃檯歸我守："
        "看單接單，guild list、guild accept；辦過的、辦到一半的，"
        "guild log 與 guild show 帳上都查得到；交回用 guild turnin，"
        "或直接對我說『回報』；撒單用 guild abandon；功績夠了想"
        "知道自個兒幾階，guild merit 一查便知。」",
    ),
    KeywordResponse(
        "回報",
        "「交回單子？我帳上還沒有你的名字——先來 guild register "
        "報到，註冊過後辦完的單，再對我說『回報』加上編號，"
        "或是 guild turnin <任務編號>，一樣算數。」",
    ),
)

# One entry keyed exactly as the guild-hall place row authors it: the key
# travels in the row, so the slice assembles into DIALOGUE_ROWS unchanged.
ROWS: tuple[tuple[str, DialogueDefinition], ...] = (
    (
        "guild_staff",
        DialogueDefinition(
            greeting=(
                "櫃檯後的公會職員從帳簿裡抬起眼：「新面孔？想在這行"
                "吃飯，規矩是先走一遍 guild register，從F階起。之後"
                "的細活我懶得念第二遍：guild list 挑單、guild accept "
                "領單，辦到哪一步 guild log 與 guild show 都有底；"
                "辦完回來說聲『回報』加編號，或自己 guild turnin 交回；"
                "不想辦了 guild abandon，功績攢出階級來再 guild merit。"
                "說罷，他又低頭繼續撥他的算盤。」"
            ),
            responses=GUILD_STAFF_RESPONSES,
        ),
    ),
)
