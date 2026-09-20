"""Synthetic gauge-transfer behavior tests (gauge-transfer-effects).

Package split of the original flat module; each slice module groups the
shipped classes by concern (parse/validation, drain-and-share settlement,
restore plus audience conditions, and regen-lock/clock interaction). The
shared synthetic skill registry maps and the test base live in ``_support``
(not a collected test module).
"""
