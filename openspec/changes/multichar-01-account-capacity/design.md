## Context

`server/conf/settings.py` never assigns `MAX_NR_CHARACTERS`, so Evennia's default of `1` applies.
The whole player-facing tree was written against that assumption:

- `typeclasses/accounts.py::_pending_character(account)` iterates `account.characters` and returns
  the first `creation_pending` one; `at_post_login` uses that to decide whether to send
  `WORLD_INTRODUCTION` plus `creation_start_screen()`. With exactly one character the predicate
  "the account has a pending character" and "the session is puppeting a pending character" are the
  same statement. With several they are not.
- `commands/localized/account.py` reads `settings.MAX_NR_CHARACTERS` once at import into
  `_MAX_NR_CHARACTERS` and branches on `== 1` in `CmdOOCLook.func` and `CmdOOC.func` to print a
  "use 進入世界 to get back" hint instead of Evennia's playable-character list.
- `commands/default_cmdsets.py::AccountCmdSet` calls `super().at_cmdset_creation()`, which mounts
  Evennia's `CmdCharCreate` and `CmdCharDelete` at `cmd:pperm(Player)`. Neither key is in
  `_LOCALIZED_ORIGINALS`, so both stay mounted in English.
  `DefaultAccount.create_character` calls `check_available_slots()` first, so `charcreate` fails
  today purely because of the cap.
- `docs/game/command-reference.md:820-821` documents both as 管理員 commands, which the mounted
  locks do not enforce. `tests/test_command_docs.py` cross-checks the reference against the
  mounted cmdsets, so the row text and the lock have to agree.

`settings-environment-overrides` makes `.env.example` and
`docs/development/settings-and-environment.md` contract-tested inventories: an added knob that is
not in both files fails `server/conf/tests/test_env_overrides.py`.

## Goals / Non-Goals

**Goals:**

- One deployment-overridable, two-sided-bounded character cap, following the file's existing
  `_env_int_bounded` idiom.
- Login screens (`WORLD_INTRODUCTION`, `creation_start_screen`) keyed to the character the session
  actually puppets, so they stay correct for any number of owned characters.
- A coherent localized OOC surface once an account can hold several characters.
- One player-facing character-creation path (the wizard) and no player-facing character deletion.
- Prove the capacity itself: N shells co-exist, each with its own `creation_pending` lifecycle,
  and the cap+1st creation is refused without side effects.

**Non-Goals:**

- No WebClient work at all (roster panel is change 02, actions are 03, UI is 04).
- No localized Telnet character switcher: `進入世界 <角色>` already handles switching, and the
  stock OOC list is accepted as-is (the original design's §9).
- No character deletion flow for players, and no per-slot monetization.
- No change to `MULTISESSION_MODE` or `AUTO_PUPPET_ON_LOGIN`; "one live puppet per session" and
  "reconnect resumes the last puppet" are exactly the semantics the later changes want.

## Decisions

### D1 — `_env_int_bounded`, not `_env_int`

`MAX_NR_CHARACTERS = _env_int_bounded("ELOSERN_MAX_CHARACTERS", 5, low=1, high=10)`.

`_env_int` only fails closed below zero; the cap needs a real upper bound because change 02 puts
one row per character into a snapshot panel that is subject to the OOB envelope size limit, and
change 04 renders them all in a dropdown. `low=1` keeps the single-character deployment
expressible. Alternative considered: plain `_env_int` with a documented soft expectation —
rejected because an operator setting `ELOSERN_MAX_CHARACTERS=500` would produce an unbounded
panel rather than a settings-load error.

### D2 — The login screens key on the session's puppet, not the account

`render_pending_character_login` stays as the single login coordinator, but `at_post_login`
resolves the subject as "the character this session is puppeting after the parent hook ran", and
sends the introduction only when *that* character is `creation_pending`. `_pending_character`
(account-wide scan) is retired from the login path.

Rationale: this is the only reading that stays true for one, two, or five characters, and it
matches the requirement's intent ("a newly registered account receives a world introduction before
character creation"). It also gives change 03 its D6 for free: puppeting a freshly created second
shell goes through the ordinary creation-mode snapshot, not through a login hook, so the
introduction is structurally impossible to resend.

Edge case that must be handled explicitly: with `AUTO_PUPPET_ON_LOGIN = True` and a
`_last_puppet` that Evennia could not re-puppet, `session.puppet` is `None` after the parent hook.
The introduction is then not sent — an unpuppeted session has no character to introduce, and the
stock OOC list is the right surface. Alternative considered: keep the account-wide scan and add a
"only if the puppet is the pending one" guard on top — rejected as the same predicate written
twice.

### D3 — Delete the `== 1` branches rather than re-express them

Both branches gate on `_AUTO_PUPPET_ON_LOGIN and _MAX_NR_CHARACTERS == 1 and self.playable`. Once
the default cap is 5 they are unreachable at the default configuration but still reachable at
`ELOSERN_MAX_CHARACTERS=1`, which would give one deployment a different OOC surface from another.
Removing them makes both commands unconditionally show `account.at_look(target=self.playable)` —
the playable-character list — which is the correct answer at every cap value including 1.

The module-level `_MAX_NR_CHARACTERS` binding is removed with its last reader, so the import-time
settings snapshot cannot go stale.

### D4 — Developer-lock `charcreate` / `chardelete` in the project `AccountCmdSet`

`AccountCmdSet.at_cmdset_creation` re-adds both commands as subclasses carrying
`locks = "cmd:perm(Developer)"`, using the same "remove the upstream key, add the project variant"
mechanism the localized wrappers already use.

Rationale: the reference page already documents them as 管理員, so this fixes an existing
doc/lock drift rather than inventing a policy. It also keeps the wizard-with-confirmation (change
03/04) the only player creation path — a raw `charcreate 阿貓` would otherwise create a shell whose
key is thrown away at activation anyway — and it removes a live `chardelete` that today can delete
an account's only character.

Alternatives considered: (a) leave both at `pperm(Player)` and rewrite the doc rows to say every
player can use them — rejected because it advertises an unlocalized English surface as a supported
player command, and `chardelete` has no confirmation; (b) remove both from the cmdset entirely —
rejected because Developer access to them is genuinely useful for building and test fixtures.

### D5 — Capacity is proven by a behavioural test, not by asserting the setting

The value assertion belongs to the env-override test. The capacity test creates the cap-many
characters on one account through `account.create_character(...)`, asserts each is
`creation_pending` and present in `account.characters`, then asserts the next call returns
`(None, [slot_error])` and creates no object. This is what changes 02–04 actually rely on.

## Risks / Trade-offs

- **A deployment pinned at `ELOSERN_MAX_CHARACTERS=1` loses the "use 進入世界 to get back" hint**
  → Mitigation: the replacement is Evennia's playable-character list, which names the single
  character and is what every other cap value shows; no information is lost, only phrasing.
- **`charcreate` was a convenient manual test fixture at Player permission** → Mitigation:
  Developer permission still has it, and the WebClient creation action (change 03) becomes the
  player-facing equivalent.
- **Two pending shells on one account both key off the account name** (Evennia's
  `create_character` defaults `key=self.key`) → this change does not fix it, because nothing
  displays a roster yet; it is called out here as an inherited constraint that change 02 must
  handle in the roster label, not in the object key.
- **`settings.MAX_NR_CHARACTERS` is read at import in more places than we changed** → Mitigation:
  after removing `_MAX_NR_CHARACTERS`, the repo-wide grep for the setting name is part of the
  verification task, so no other import-time snapshot survives.
