# Design: Authoritative shop prices in party documentation

## Context

The parent party-management UI design §4.3 says prices are unchanged and then claims every sell price is half the buy price. Handoff evidence records buy 8 and sell 6 for a synthetic potion. `shop-economy` already sources exact integer buy/sell prices independently from commerce declarations, rejecting sell-above-buy without requiring a half ratio. `services_catalog.py` builds its synthetic potion offer through `synth_offer_rule`; synthetic item bands admit the observed values. The shop view reads `buy_copper` and `sell_copper` from their respective rows.

## Goals / Non-Goals

Resolve the design discrepancy by retaining authoritative economy semantics. No pricing-engine correction, catalog rebalance, forced half-price rule or alteration of the already-corrected help convention is authorized.

## Decisions

Amend only the erroneous price sentence in `docs/superpowers/specs/2026-10-18-party-member-management-ui-design.md:75` to: Buy and sell prices remain the independently configured authoritative integer-copper offer values. The buy view shows only buy prices, and the sell view shows only sell prices; no universal ratio is implied. This proposal explicitly amends that parent design assertion and leaves its other shop behavior intact.

Add asymmetric-price regression scenarios to the existing full buy/sell requirement blocks in `webclient-shop-window`. Prove a fixed synthetic offer buying at 8 and selling at 6 through the real service publisher and trade path, with independently known wallet, bag and stock deltas. Extend existing shop-window tests so each tab reads its own field, each total uses that field and quantity, and the opposite price is absent. The exact 8/6 pair is a synthetic arithmetic input, never a production balance approval table.

Before recording completion, cite the authoritative offer rule and synthetic declaration/probe output in task evidence. If those sources expose a different separate defect, retain this design correction and report the new evidence through its owning change. Do not silently change commerce data to fit the obsolete sentence.

## Risks / Trade-offs

Storybook examples or tests using half-price pairs can hide a ratio assumption. Use an asymmetric pair in the focused consumer tests without migrating unrelated fixtures. New requirement IDs are unnecessary because the parent requirement names remain unchanged.

## Verification and documentation

The same implementation group updates the parent design and focused existing backend/shop-window tests. Register any new test method/module, annotate the existing buy/sell requirements and run focused service/trade and Vitest tests plus strict delta validation. A managed browser method is needed only if existing real-consumer coverage cannot establish the delivered path; register it if added. No pre-sync traceability failure is classified as a pricing defect.
