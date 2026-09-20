"""
Synthetic behavior tests for damage and debuff state feedback (light-cleric-feedback).

Exercising:
- Different damage sources share reaction with loss-proportional gain (direct spell, item, periodic tick)
- Coefficient shaping: floor(140 x actual_loss / max_hp); a half-max-HP loss is worth five times a tenth-max-HP loss
- A full climax journey costs half of maximum HP (post-climax 15 + 70 = 極限 floor 85)
- No-loss negative instances price at the authored flat fraction of max HP (floor(140 x 0.05) = 7)
- Indeterminate cases (absent loss amount, unreadable or non-positive max HP) apply nothing rather than guess
- Retired source-tier gain mapping fails closed at rule load naming the rule id
- Negative triggers: misses, zero damage, dead targets, immunity refused debuffs, buff refreshes, resource costs
- Distinct events for new debuff acceptance and subsequent periodic damage ticks
- Transitive feedback cascades entering normal lock phase without inventing a second state system
- Late-failure rollback restoring complete cascade (action, item, and clock paths)
- Conferred passive grants do NOT create binary event-reaction entitlement
- Source tier retention on debuff instances across clock advances
- Recovery-only passive multiplier: equipment-independent benefit, snapshot stability across caster arousal changes
- Conferred recovery passive fractional scaling via combat modifier rule scaling
- No duplicate sacramental/direct-heal multiplier and clean independent composition with equipment heal_gain
- Second synthetic non-light configuration proving generic reaction-input reuse

Package split of the original flat module; each slice module groups
the shipped classes by concern. Shared module-level fixtures, helpers,
and bases live in ``_support`` (not a collected test module).
"""
