## ADDED Requirements

### Requirement: Scene selections use the landscape page
For a scene subject the page SHALL place the art above at 16:9, with the name and the committed `description` in the left column and the fact cells in the right column. With no stored card it SHALL show the subject's committed tile artwork labelled 官方內建圖 and offer 生成新圖; with a stored card it SHALL label the image 生成圖.

#### Scenario: A bundled scene offers generation
- **WHEN** the selected scene subject has no card rows
- **THEN** the page shows the subject's tile artwork, the 圖片 cell reads 官方內建圖, and the footer offers only 生成新圖

#### Scenario: A generated scene offers deletion and regeneration
- **WHEN** the selected scene subject has one stored card and its capabilities declare deletion, one card and no geometry
- **THEN** the 圖片 cell reads 生成圖 and the footer offers 刪除 and 重新生成

#### Scenario: The description sits beside the facts
- **WHEN** a scene with a committed description is selected
- **THEN** the description renders in the letter box in the left column below the art and the fact cells render in the right column
