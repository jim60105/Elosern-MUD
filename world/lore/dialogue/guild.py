"""The adventure guild's authored dialogue row (the guild-hall counter).

One table: the ``guild_staff`` row spoken by 葛里安·衛登, the 阿爾托利亞分會
branch master behind the counter, keyed by the ``dialogue_key`` the
guild-hall place row authors. The table is written against the branch
master's persona card in ``world/lore/npc_profiles/altoria_guild.py``; the
host authors sex ``other``, so narration gives no gendered pronoun.

Every line is spoken in character (scripted-dialogue, guild-registration):
the branch master explains what the counter is for in the world's own terms
(sign the register, take a slip from the board, report back with the slip's
number, hand a slip back, ask where one stands) and never names a command.
The register is formal: an office-holder receiving adventurers. Two shape
rules bind this row:

- Four keyword answers at most. The dialogue panel ships
  ``DIALOGUE_MAX_CHOICES`` entries and silently drops the rest, so a fifth
  keyword is a keyword the player can never press. This row carries
  exactly four.
- ``回報`` is a keyword identifier with mechanics behind it: for a
  registered member the talk path answers with the guild service's own
  reportable-quest listing or turn-in result, so the authored response
  below is the register-first fallback an unregistered player hears.
"""

from world.lore.dialogue.shape import DialogueDefinition, KeywordResponse

# Exactly four answers, in panel order.
GUILD_STAFF_RESPONSES: tuple[KeywordResponse, ...] = (
    KeywordResponse(
        "註冊",
        "「登記很簡單，在這本名冊上寫下名字，公會就認你是冒險者。每個人都"
        "從 F 級開始，先接採集這類簡單的委託，再逐級往上。名冊上記下的每"
        "一筆，公會都會負責到底。」",
    ),
    KeywordResponse(
        "任務",
        "「委託單都釘在大廳那面任務板上，單子寫著階級、地點與報酬。挑一張"
        "合你階級的拿來櫃檯，我登記之後，這份委託就算你接下了。辦到哪一步"
        "，隨時可以來問，名冊上都有記錄。中途辦不下去，把單子交回來即可，"
        "不必勉強。」",
    ),
    KeywordResponse(
        "公會",
        "「埃洛西恩冒險者公會由三國共同承認，總部設在帝國首都，這裡是阿爾"
        "托利亞分會。分會負責冒險者的登記、委託的發放與結算，以及階級的晉"
        "升。想知道自己目前是幾級、離下一級還有多遠，到櫃檯問一聲，我翻名"
        "冊給你看。」",
    ),
    KeywordResponse(
        "回報",
        "「回報？名冊上還沒有你的名字。請先在櫃檯登記成冒險者。接下委託、"
        "辦完之後，再回到這裡向我回報，並報上委託單的編號。公會只認名冊上寫下的事。」",
    ),
)

# One entry keyed exactly as the guild-hall place row authors it: the key
# travels in the row, so the slice assembles into DIALOGUE_ROWS unchanged.
ROWS: tuple[tuple[str, DialogueDefinition], ...] = (
    (
        "guild_staff",
        DialogueDefinition(
            greeting=(
                "櫃檯後的分會會長葛里安·衛登擱下羽毛筆，抬眼看你：「歡迎來到冒險者公會阿爾托利亞分會，冒險者。你是來登記"
                "，還是來交委託？還沒登記"
                "的話，請先在這本名冊上留下名字，從 F 級開始。登記之後，到大廳"
                "那面任務板挑一張合你階級的委託單，拿來櫃檯讓我登記。辦完了回到"
                "這裡向我回報，報上委託單的編號即可。」"
            ),
            responses=GUILD_STAFF_RESPONSES,
        ),
    ),
)
