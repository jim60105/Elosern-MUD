"""Combat-session flow tests: innate skill affordances, engage/engage-group
opening, player-round settlement, commanded-action attribution, the round
settlement seam, and the session command surface.

Package split of the original flat module; each slice module groups the
shipped classes by concern (innate flow, engage/player rounds,
attribution/seam/command surface, grouped opening, opening dispatch, and the
structural submission contract). Shared synthetic rows and scope helpers live
in ``_support`` (not a collected test module).
"""
