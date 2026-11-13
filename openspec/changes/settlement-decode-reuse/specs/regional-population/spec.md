# Spec Delta

## ADDED Requirements

### Requirement: Stored population records are decoded once per stored value
A read of the population timeline or of the per-zone state record SHALL reuse its earlier decode while the stored value is unchanged, and SHALL decode again after any write of that record, including an in-place mutation and a rollback restore.

#### Scenario: Repeated reads
- **WHEN** the timeline and the zone state record are each read five times with no write between the reads
- **THEN** each record is decoded once and every read returns equal values

#### Scenario: Read follows every kind of write
- **WHEN** the timeline is replaced by a whole-value write, then mutated in place, then restored by a rolled-back transaction
- **THEN** the read after each step returns that step's stored value

### Requirement: A settlement pass reuses pass-stable population facts
One lifecycle settlement pass SHALL enumerate the living individuals, read each individual's home zone and site marker, and read active-session cell protection once, and SHALL compute the protected-cell set once per tick and timeline value. A birth, a site populate, clear or recovery, and a field contact block SHALL drop the reused facts.

#### Scenario: Quiet pass over many boundaries
- **WHEN** one pass settles many boundary ticks of synthetic groups with no birth, no site change and no contact
- **THEN** the living individuals are enumerated once and active-session protection is read once

#### Scenario: Birth inside the pass
- **WHEN** a wave commits a birth at one boundary tick of the pass
- **THEN** the next presence read at that tick includes the newborn individuals with their home zone

#### Scenario: Protected cells per tick
- **WHEN** three group destinations are checked at one tick with no timeline write between the checks
- **THEN** the protected-cell set is computed once and all three checks get the answer an unshared check gives

### Requirement: Reuse leaves settlement results unchanged
A settlement pass with reuse SHALL leave the same activity record, timeline, zone records, site records and per-individual position, gauges, reserve, posture and sleep receipt as the same pass without reuse.

#### Scenario: Differential pass under partitions
- **WHEN** a synthetic world with a wandering group, a travelling group, a zone below its lower density and a recoverable site is settled over one interval and over two different partitions of it, once with reuse and once without
- **THEN** all six resulting state projections are equal
