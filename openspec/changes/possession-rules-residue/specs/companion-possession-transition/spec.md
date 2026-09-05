# Delta spec: companion-possession-transition (possession-rules-residue)

The disconnect hook currently embeds the multisession guard (a session scan deciding whether to
release) inside `Account.at_post_disconnect` — business rules outside the single writer — while
`release_on_disconnect` additionally runs a dead `db_account` query. The guard becomes rules-owned
inside `release_on_disconnect`; the hook thins to the single call the original requirement words.

## MODIFIED Requirements

### Requirement: Disconnecting while possessing releases possession through the account disconnect hook
`Account.at_post_disconnect` SHALL call `possession.release_on_disconnect(self)` — the disconnect-only lifecycle point, verified in Evennia 6.1 to fire solely from `ServerSession.disconnect()` and never from `Account.unpuppet_object`'s deliberate unpuppet or a reload — and `PlayerCharacter.at_post_unpuppet` SHALL NOT gain any possession branch (it fires on every puppet swap, including possession's own release of A; wiring cleanup there would clear the fresh mirrors mid-possession). The hook SHALL contain no possession business logic beyond that single call: the multisession skip is owned by `release_on_disconnect` itself, which SHALL return without releasing when any live session of the account still puppets an object carrying a `possessed_by` mirror (the possession is actively driven on another session), and SHALL otherwise release every possession reachable through the account's characters and sessions — the scan over live sessions and owned characters is the sole discovery mechanism (no account-ownership query over NPC objects, which companion NPCs never satisfy). NOTHING in possession code SHALL inspect server shutdown state — reload keeps sessions, so no release fires and Evennia's own re-adoption re-puppets the persisted possession state (the retained lock grant makes this possible). Possession attributes SHALL survive a save/reload round-trip intact. The guard's precondition is Evennia's own ordering: `ServerSession.at_disconnect` unpuppets the departing session BEFORE it fires `Account.at_post_disconnect` (verified in Evennia 6.1), so the disconnecting session never still puppets anything at guard time and the scan sees only remaining sessions; tests simulating a disconnect SHALL clear the departing session's puppet before invoking the hook.

#### Scenario: Disconnect drops the puppet and the state together
- **WHEN** the possessing session disconnects
- **THEN** `release_on_disconnect` runs for the account, the NPC is unpuppeted, the grant stripped, both possession attribute mirrors cleared, and A is not force-puppeted anywhere

#### Scenario: A possession-internal unpuppet never triggers the release
- **WHEN** entering possession deliberately unpuppets A, or 歸位 unpuppets B
- **THEN** no disconnect release runs (the hook is not on the unpuppet path) and the intended possession state survives the swap intact

#### Scenario: Reload preserves a live possession
- **WHEN** attributes are saved and re-read without a disconnect (the reload path)
- **THEN** `possession` and `possessed_by` remain set and the NPC's account grant remains granted

#### Scenario: A still-driven possession survives one session's disconnect
- **WHEN** `release_on_disconnect` is called for an account while another of its live sessions still puppets the possessed NPC
- **THEN** no release occurs and the possession mirrors, grant, and puppet remain intact

#### Scenario: The guard unblocks once the last driving session is gone
- **WHEN** the remaining session puppeting the possessed NPC disconnects afterward
- **THEN** `release_on_disconnect` finds no possessed-puppet session, releases fully, and the mirrors and grant are cleared
