"""Action-options trigger service tests (composition root).

Package split of the original flat module; each slice module groups the
shipped classes by concern (the scheduling contract, stale-token eviction,
memo/failure isolation and the cache cap, the dismissal barrier, and the
reconnect trigger). The shared service fixtures and FakeLLM helpers live in
``_support`` (not a collected test module).
"""
