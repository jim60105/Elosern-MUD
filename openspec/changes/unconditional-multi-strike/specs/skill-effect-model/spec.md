## RENAMED Requirements

- FROM: `### Requirement: A conditional follow-up strike repeats damage without repeating the action`
- TO: `### Requirement: A follow-up strike repeats damage on evidence or unconditionally without repeating the action`

## MODIFIED Requirements

### Requirement: A follow-up strike repeats damage on evidence or unconditionally without repeating the action
A validated damage policy SHALL permit one extra independent strike — either against a target with matching recent evidence (the evidence-conditional shape: `repeat_when` naming a recognized evidence kind) or unconditionally on every successful action resolution (the predicate-free shape: an extra-strike declaration with no `repeat_when`). Each strike SHALL have an independent hit roll and the same coefficient/policy. The first miss SHALL NOT suppress the second strike. The action SHALL pay resources/time and award eligible practice once, project ordered damage correctly, and retain both rolls while emitting at most one terminal defeat or knockout for a target. The extra-strike count SHALL stay capped at one; every other shipped `DamagePolicy` validation SHALL stay fail-closed exactly as before, and the construction rule 「an extra strike requires `repeat_when`」 SHALL be retired so the predicate-free shape is legal vocabulary for any element.

#### Scenario: A first miss does not suppress the second roll
- **WHEN** fixed rolls make the first strike miss and the follow-up hit on an eligible target under an evidence-conditional policy
- **THEN** only the second damages HP and both rolls are recorded for one paid cast

#### Scenario: Ineligible target has one strike
- **WHEN** recent evidence is missing or expired for an evidence-conditional policy
- **THEN** only the ordinary strike occurs

#### Scenario: Repeated damage is atomic and nonlethal aware
- **WHEN** two strikes cross a protected target or a later commit step fails
- **THEN** successful settlement floors HP at 1 with one knockout; a failed settlement restores all HP and evidence

#### Scenario: An unconditional policy always resolves two independent strikes
- **WHEN** a synthetic damage policy declares its extra strike with no evidence predicate and strikes any living target under each fixed roll pair (hit-hit, miss-hit, hit-miss, miss-miss)
- **THEN** exactly two independent hit rolls are recorded and each landing strike deals the same coefficient/policy damage, whatever recent evidence the target does or does not hold, and a policy-free control skill on the same target still resolves exactly one strike

#### Scenario: The predicate-free shape is validated like every other policy
- **WHEN** policies declare an extra strike with a valid evidence kind, with no predicate, with an unknown evidence kind, with a boolean or out-of-cap strike count, or with `repeat_when` and a strike count other than one
- **THEN** the two well-formed shapes construct (conditional and unconditional), and each malformed combination still raises at construction exactly as before the widening
