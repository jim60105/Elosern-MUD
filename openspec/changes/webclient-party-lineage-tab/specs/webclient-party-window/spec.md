# Spec Delta

## ADDED Requirements

### Requirement: The lineage list groups graphs with node diamonds
The 系譜 tab's list column SHALL group graphs by element or style; each row SHALL name the graph by its roots joined with ‧, show one diamond per node (filled: capped, half-filled: owned, dashed: locked), show owned/total, and mark 可解鎖 when any node is ready. Graphs of one, two or seven nodes SHALL render the same way.

#### Scenario: A one-node graph renders like the others
- **WHEN** the viewed member owns 聖水祝福 with no lineage edges
- **THEN** its row shows one filled diamond and 1/1 with the same row layout as a seven-node graph

### Requirement: The lineage detail draws the real graph
The detail column SHALL draw the selected graph with nodes placed by `depth`, each merge node drawn once, edges labelled with their minimum level, and the three node states distinguished by border style and text as well as colour; selecting a node SHALL open that skill in the 技能 tab.

#### Scenario: A merge node appears once with two labelled edges
- **WHEN** the ice graph is selected and 冰晶風暴 requires 冰霜護甲 Lv 2 and 冰槍 Lv 2
- **THEN** 冰晶風暴 is drawn once with two incoming edges labelled Lv 2

#### Scenario: Selecting a node opens the skill
- **WHEN** the player activates the 冰錐術 node
- **THEN** the window switches to 技能 with 冰錐術 selected
