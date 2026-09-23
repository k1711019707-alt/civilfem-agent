# Component Plugin Workflow

## ADDED Requirements

### Requirement: 插件协议
系统 MUST 提供插件协议，至少包含类型名、验证、几何构建、网格、求解器导出和结果提取方法。

#### Scenario: 插件接口可发现
- **WHEN** 系统加载钢梁插件
- **THEN** 插件暴露验证、几何、网格、求解器和结果提取方法

### Requirement: 钢构件适配
系统 MUST 提供钢梁和钢柱插件，并复用现有钢截面校核逻辑。

#### Scenario: 钢梁校核
- **WHEN** 输入合法 H 型截面、钢材和内力
- **THEN** 插件返回结构化校核结果，包含条文、需求值、容量、比值和结论

### Requirement: 非法几何拒绝
系统 MUST 拒绝非正截面尺寸和未知钢材牌号。

#### Scenario: 非法尺寸
- **WHEN** `h`、`b`、`tw` 或 `tf` 小于等于零
- **THEN** 返回可行动验证错误，不进入求解阶段
