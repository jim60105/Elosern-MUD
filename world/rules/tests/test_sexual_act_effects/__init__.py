"""Sexual-act-effect tests (sexual-act-effects): the pure helpers in
``world/rules/sexual_act_effects.py``, the ``pleasure:``/``sexual_counter:``
effect handlers registered in ``world.rules.action``, and the end-to-end cast
path through ``ActionResolver`` with a test-local act installed via
``patch.dict``.

Package split of the original flat module; each slice module groups the
shipped classes by concern (config/pure helpers, pleasure-gain and counter
tables, act-cast handler integration, sexual-event channels, and pair-event
naming). Shared fixtures, helpers, and the ``_ActCastTestCase`` base live in
``_support`` (not a collected test module).
"""
