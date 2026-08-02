"""Read-only world introduction prose shown to new players at login.

Owned by the ``login-creation-ux`` change; no other module depends on it yet.
The text is immutable so every entry surface renders the same introduction.
"""

WORLD_INTRODUCTION = (
    "歡迎來到伊洛瑟恩大陸，一片由魔法與古老種族交織而成的世界。\n"
    "戰爭的傷痕仍刻在國境之上，而冒險者的道路，正等待第一位旅人踏上。"
)
