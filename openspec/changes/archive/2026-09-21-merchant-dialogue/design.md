## Context

`merchant` is the only host blueprint with no dialogue component. Eight shipped hosts stand behind counters and cannot be addressed. The attendant change just established the pattern for talk-only hosts and moved the dialogue tables somewhere they can grow; this is the change that makes shopkeepers use it.

## Goals / Non-Goals

**Goals.** Every merchant answers. Eight authored tables. A rule that a merchant without a table fails load rather than shipping silent.

**Non-Goals.** No change to trade. No change to how affinity accrues — shops still accumulate through `trade`; dialogue adds a surface, not a second economy. No generative dialogue: these are scripted tables like the guild staff's.

## Decisions

### Extend `merchant`, do not add a second blueprint

The alternative is a `merchant_attendant` row that places opt into, leaving plain `merchant` for shopkeepers who stay silent. Rejected for the same reason the attendant change rejected per-role professions: a vocabulary whose two rows differ by "does this one speak" is a vocabulary that will be read as an occupation label.

More concretely, nobody would ever deliberately author a silent shopkeeper. If every merchant should talk, the blueprint should say every merchant talks, and the load error for a missing table becomes a useful reminder rather than an obstacle.

### The missing-table failure is the feature

Making dialogue mandatory means the eight shipped places and every future merchant place must author a key. That is a real authoring cost and it is the point: the defect being fixed is a shopkeeper nobody noticed was mute, and a blueprint that made dialogue optional would let the next one ship the same way.

The attendant change already added the rule that an authored key must resolve to a real table, so "authored but pointing at nothing" is caught too.

### Village hosts are not shopkeepers

The elven village's premise is that its four traders are villagers sharing what they make — 「對這位精靈而言這是分享興趣與互助，不是營業」. A shopkeeper dialogue template applied to them would undo in prose what the whole settlement's design establishes in structure.

So the register rule is a requirement rather than a style note: a trading host speaks as its settlement, and in the village that means no proprietor voice, no business hours quoted as policy, no goods called stock. This is the one part of this change that is easy to get wrong by being efficient — writing one template and filling in nouns.

### Nothing in the loader changes

Blueprint coverage already demands every component's identity kwargs, assembly already attaches whatever the blueprint declares, and the dialogue-resolution check already fires for any profession carrying `scripted_dialogue`. Adding a component to one row exercises all three without touching them.

## Risks

**Eight tables written at once tend toward sameness.** The spec pins that each host answers about what it actually offers rather than with a shared line, which is checkable; tone is not, and the village four are where a reviewer should look hardest.

**Existing merchant hosts are live objects.** The component is attached by assembly on every sync, and assembly is already idempotent and already runs for reused hosts, so an existing 瑪爾特·金秤 gains the component on the next startup without being recreated. Worth an explicit test rather than an assumption — the never-rename contract means this must happen by convergence, not by deleting and rebuilding her.
