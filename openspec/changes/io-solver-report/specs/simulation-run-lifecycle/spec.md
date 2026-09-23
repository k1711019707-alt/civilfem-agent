# Spec Delta

## Purpose

为网格和有限元求解提供可复现运行目录、后端能力状态、路径边界和生命周期查询，使失败可定位且不伪造完成结果。

## ADDED Requirements

### Requirement: 后端能力状态
系统 MUST 检测 Gmsh、CalculiX 和 OpenSeesPy 是否可用，并在不可用时返回 `not_implemented` 或 `failed` 及原因。

#### Scenario: 后端缺失
- **WHEN** 本机未安装 CalculiX
- **THEN** 提交结果返回 `not_implemented`，不创建虚假完成结果

### Requirement: 运行目录边界
系统 MUST 将运行文件写入配置根目录下的唯一目录，并拒绝 `..`、根目录外路径和任意 shell 字符串。

#### Scenario: 越权路径
- **WHEN** 输出目录解析后位于项目根目录外
- **THEN** 系统拒绝任务并返回路径越权错误

### Requirement: 状态可追溯
每次任务 MUST 保存 `run_id`、输入哈希、后端、开始时间、结束时间、状态和错误摘要。

#### Scenario: 查询已提交任务
- **WHEN** 用户使用 `run_id` 查询任务
- **THEN** 系统返回 queued、running、failed 或 completed 之一及运行清单
