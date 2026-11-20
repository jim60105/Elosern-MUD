# Proposal

## Why

Shops sell food that currently has no use effect. Give players a reason to buy it as field supplies without adding hunger or satiety.

## What Changes

- Make the eleven currently stocked food items consumable outside combat, using the existing item action to restore HP, MP, or SP.
- Keep shop assortments, prices, ordinary potion behavior, and the potion-classified Miner's Bracing Broth unchanged.
- Do not add a food command, a new gauge, or a recovery bonus tied to lodging.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `item-use-resolution`: Define how authored food recovery uses the ordinary item action.

## Impact

The three affected item catalog files gain recovery profiles. The existing inventory, item-action, and deterministic recovery paths handle use without a new runtime subsystem.
