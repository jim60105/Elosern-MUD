## ADDED Requirements

### Requirement: The startup prune reclaims stored art of unregistered monster keys
The startup prune SHALL delete every gallery record, gallery job record and classic asset record whose kind is `monster` and whose key is not a registered visual species, before its file phase, so the files only those records referenced become orphans and are deleted in the same pass. Records of registered species SHALL be untouched.

#### Scenario: An unregistered species leaves nothing behind
- **WHEN** the server starts with a gallery record holding one card, a pending gallery job and a done classic record for monster key `t_gone`, which the synthetic registry does not register
- **THEN** after the prune no record names `t_gone` and none of the files those records referenced exists

#### Scenario: A registered species is untouched
- **WHEN** the same prune runs while the synthetic registry registers `t_kept`, which has a gallery record with one card
- **THEN** that record, its card and its file are unchanged

#### Scenario: The prune stays idempotent
- **WHEN** the prune runs a second time
- **THEN** it deletes nothing and raises nothing
