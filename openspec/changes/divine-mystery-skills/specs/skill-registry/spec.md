## ADDED Requirements

### Requirement: divine_sexual_mastery and divine_sexual_arts exist as distinct skills
`SKILL_REGISTRY` SHALL contain `divine_sexual_mastery` (性魔法主宰, `PASSIVE`,
`effects=["sexual_magic_mastery"]`, flavor/title content not gating any other skill's castability in
this change) and `divine_sexual_arts` (神之秘法：性愛系統, `ACTIVE`, `usable_out_of_combat=True`, empty
`cost`, `effects=["sexual_event:<name>"]`), both gated by `can_use_divine_arts` per the `divine-mystery`
capability's requirement.

#### Scenario: divine_sexual_mastery does not gate divine_sexual_arts
- **WHEN** an elf entity owns `divine_sexual_arts` but not `divine_sexual_mastery`
- **THEN** casting `divine_sexual_arts` is not rejected for lacking `divine_sexual_mastery`
