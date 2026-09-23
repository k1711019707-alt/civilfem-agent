# Canonical Structural Model

## ADDED Requirements

### Requirement: 版本化模型
系统 MUST 提供 `schema_version`、`project_id`、单位、构件列表和证据元数据。

#### Scenario: 合法模型创建
- **WHEN** 用户提供项目标识和至少一个合法构件
- **THEN** 系统返回可序列化的 Canonical Structural Model，`schema_version` 默认为 `0.1`

### Requirement: 关键参数状态
系统 MUST 将缺少材料、荷载或边界条件的构件标记为 `pending_confirmation`，不得静默猜测。

#### Scenario: 缺少关键参数
- **WHEN** 构件缺少材料或边界条件
- **THEN** 验证结果为 `pending_confirmation`，并列出缺失字段

### Requirement: 路径和来源可追溯
系统 MUST 保存来源、实体标识、置信度和坐标/单位信息。

#### Scenario: 读取 JSON 来源
- **WHEN** 构件来自 JSON 输入
- **THEN** 结果包含 JSON 来源证据和输入单位
