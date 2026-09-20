"""Tests for the gallery record model: card contract, validation, and writes.

Package split of the original flat module; each slice module groups the
shipped classes by concern (store-root confinement and the validators, the
card contract and equipment snapshot reader, and the two halves of the
write/delete/tolerant-read battery). The identity/card factories and fake
entities live in ``_support`` (not a collected test module).
"""
