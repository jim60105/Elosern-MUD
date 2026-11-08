"""
Canonical affordance vocabulary tests (action-options-affordance-contract).

Covers the frozen discriminated ``AffordanceView`` contract, the
``ACTION_CODE_ALLOWLIST`` constant, the per-rule candidate builders with their
version-1 identical eligibility and disabled semantics, validator-normalized
params (including the freeform binding-only exception), the idle baseline, the
vocabulary collector order, and the delivery/possession rules.

Package split of the original flat module; each slice module groups
the shipped classes by concern. Shared module-level helpers live
in ``_support`` (not a collected test module).
"""
