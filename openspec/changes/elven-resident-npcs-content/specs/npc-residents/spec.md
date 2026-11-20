# Spec Delta

## ADDED Requirements

### Requirement: The three elven villages carry their authored residents
三座精靈村（`elven_village_fionnen`、`elven_village_ciaran`、`elven_village_eolas`）SHALL 經 `RESIDENT_REGISTRY` 各承載 15 位居民，且每位居民的 `profile_key`、`subrace`、`sex`、`home_room`、`schedule_template`、`dialogue_key` 均解析到已登錄的設定檔、亞種、性別、內室、作息模板與對話表；字面數值 SHALL 落在其種族的合法帶內。

#### Scenario: Every village resolves fifteen residents
- **WHEN** 居民登錄表與三座精靈村都已完成同步
- **THEN** 每座村有 15 具居民 `LLMNPC` 存在，且每位居民身處其指定村、性別為 `female`、數值在精靈帶內（各 pool 10000、物理三軸 70–95、魔力 100–200）

#### Scenario: Author references resolve before sync writes
- **WHEN** 任一居民的 `profile_key`、`home_room`、`dialogue_key` 或 `schedule_template` 指的是未登錄、不存在或無效的鍵
- **THEN** 同步整批拒收並具名該居民與缺失鍵，不建立任何居民

#### Scenario: A resident dialogs without a service
- **WHEN** 玩家對任一居民使用交互介面
- **THEN** 其條件式劇本話題可被交談，且不出現任何交易／公會／教會／委託服務入口