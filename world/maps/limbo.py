"""Immutable starting-room (Limbo) identity data (localize-limbo-zhtw).

The starting room where characters first exist is an Elosern story location
authored in Traditional Chinese. ``LIMBO_KEY`` is the single source of truth
for the room's zh-tw object key, ``LIMBO_ALIAS`` keeps the legacy English name
resolvable for builders and documentation, and ``LIMBO_DESC`` is the authored
description. Consumers must read these values instead of duplicating the
strings (lore-registry convention).
"""

# The zh-tw object key of the starting room ("the Void Realm"). Replaces the
# upstream Evennia "Limbo" key; searched by key only, never by dbref.
LIMBO_KEY = "虛境"

# The legacy English key Evennia's first-boot setup creates; sync_limbo()
# renames a room carrying it in place so existing databases converge.
LIMBO_LEGACY_KEY = "Limbo"

# Alias that keeps the English name resolvable after the rename.
LIMBO_ALIAS = "limbo"

# Authored zh-tw description: the threshold where awakening souls pause
# before stepping onto 伊洛瑟恩大陸 (a "gray waiting room", per the onboarding
# design spec O2). Contains no upstream Evennia boilerplate.
LIMBO_DESC = """你身處一片無盡的灰白虛境。沒有天空，也沒有大地，只有流動的霧氣在四周緩緩盤繞。記憶像斷線的珠子散落在腳邊——你隱約記得一座宏偉的城，記得它名叫聖潔王都·阿爾托利亞。

這裡是伊洛瑟恩的門檻：每一縷新生的靈魂都會在此停留片刻，然後踏上那片大陸。霧氣深處透出一線微光，那是一座城門的輪廓。

只要邁步向前，就能踏入真實的世界。"""
