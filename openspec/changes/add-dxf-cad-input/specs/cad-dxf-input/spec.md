# Spec Delta

## Purpose

将 DXF CAD 图纸作为结构分析的可追溯输入源，提供只读几何检查和人工确认环节，再生成可用于网格与求解的结构化模型。

## ADDED Requirements

### Requirement: DXF 图纸检查

系统 MUST 支持读取 DXF 文件并返回文件哈希、实体数量、图层列表、二维边界和可识别线段长度统计。

#### Scenario: 合法 DXF

- **WHEN** 用户上传合法 DXF 图纸
- **THEN** 系统返回 `inspected`、格式 `dxf`、实体统计、图层列表和几何摘要

#### Scenario: 非法 DXF

- **WHEN** 用户上传损坏或非 DXF 文件
- **THEN** 系统返回 `invalid` 和可读解析错误，不进入建模或求解

### Requirement: CAD 参数人工确认

系统 MUST 在 DXF 几何摘要之后要求用户明确填写截面、材料、荷载、长度和边界等关键工程参数；系统 MUST 不得从图纸静默猜测缺失参数。

#### Scenario: 参数未确认

- **WHEN** 用户只上传 DXF 而未填写关键参数
- **THEN** 系统显示待确认状态，并禁止生成求解模型

#### Scenario: 参数确认

- **WHEN** 用户填写并确认关键工程参数
- **THEN** 系统生成 Canonical Model，并允许进入现有网格和求解流程

### Requirement: CAD 输入安全边界

系统 MUST 将上传 DXF 写入配置项目根内，并 MUST 拒绝路径穿越、超大文件和任意命令字符串。

#### Scenario: 越权或超大输入

- **WHEN** 上传文件路径越权或文件超过输入大小限制
- **THEN** 系统拒绝文件并返回明确错误

