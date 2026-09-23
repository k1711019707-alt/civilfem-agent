# Spec Delta

## Purpose

为结构化模型建立输入资产入口，识别支持的文件格式、基本实体统计、单位线索和缺失字段，避免未经确认直接求解。

## ADDED Requirements

### Requirement: 多格式只读检查
系统 MUST 对 JSON、IFC、DXF 文件执行只读检查，并返回格式、文件哈希、实体统计和可行动错误。

#### Scenario: 检查 JSON
- **WHEN** 用户提交合法 JSON 文件
- **THEN** 系统返回 `inspected`、格式 `json`、记录数量和 SHA-256 哈希

#### Scenario: 检查未知格式
- **WHEN** 用户提交不支持的扩展名
- **THEN** 系统返回 `not_implemented` 和支持格式列表

### Requirement: 缺失参数显式化
系统 MUST 列出无法从输入读取的材料、荷载、边界和几何参数，不得静默补全关键工程参数。

#### Scenario: IFC 缺少材料
- **WHEN** IFC 文件没有材料关联
- **THEN** 检查结果列出材料缺失并标记待确认
