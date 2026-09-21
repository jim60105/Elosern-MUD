## ADDED Requirements

### Requirement: Commerce balance data is a set of files, not one file
The commerce rulebook SHALL be a directory of YAML files rather than a single file, read in
sorted filename order so the load is deterministic. Its `assortments:` and `shops:` lists SHALL
concatenate across files and its `price_scales:` mappings SHALL merge.

An assortment key, a shop key or a settlement scale declared in more than one file SHALL fail
load naming the key and both files. Splitting the rulebook is only worth doing if each file
owns what it declares, and a merge where the last file silently wins would remove exactly that
guarantee.

#### Scenario: Sections spread across files load as one catalog
- **WHEN** the commerce rulebook directory holds assortments and shops split across several
  files
- **THEN** the loaded catalog contains every section from every file, identical to what one
  concatenated file would produce

#### Scenario: A key declared twice across files fails load
- **WHEN** two files in the directory declare the same assortment key, shop key or settlement
  scale
- **THEN** load raises naming the key and both files

#### Scenario: The split changes no resolved offer
- **WHEN** the resolved shop catalog is compared before and after the split
- **THEN** every shop's offers, prices, stock and hours are unchanged
