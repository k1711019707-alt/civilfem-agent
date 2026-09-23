# Spec Delta

## Purpose

为 CivilFEM Agent 提供中文浏览器界面，使工程人员能够在不编写调用代码的情况下完成输入检查、模型验证、网格生成、求解提交、状态查看和报告下载。

## ADDED Requirements

### Requirement: 中文 GUI 流程

系统 MUST 提供中文浏览器界面，并 MUST 按输入、验证、网格、求解、结果和报告顺序呈现可操作流程。

#### Scenario: 启动 GUI

- **WHEN** 用户在已安装 GUI 依赖的 `fangzhen` 环境运行启动命令
- **THEN** 浏览器界面启动，并显示项目标题、后端能力状态和输入区域

### Requirement: 输入与模型验证

系统 MUST 支持上传 JSON 文件，显示输入检查结果、Canonical Model 摘要和验证状态；验证失败时 MUST 阻止后续求解提交。

#### Scenario: 合法 JSON

- **WHEN** 用户上传合法结构化 JSON 并点击验证
- **THEN** 界面显示 `inspected`、项目标识、构件数量和 `valid` 或待确认状态

#### Scenario: 非法模型

- **WHEN** 用户上传无法构造 Canonical Model 的 JSON
- **THEN** 界面显示可读错误，并不提交网格或求解任务

### Requirement: 网格与求解操作

系统 MUST 提供网格尺寸、求解后端和 CalculiX 输入文件控件，并 MUST 复用现有受控 Python API 完成网格和求解。

#### Scenario: 生成网格

- **WHEN** 用户通过验证模型并点击生成网格
- **THEN** 界面显示运行状态、节点数、单元数和可查看的 PNG 网格预览

#### Scenario: 提交求解

- **WHEN** 用户选择可用后端并提供所需输入后点击求解
- **THEN** 界面显示 `queued`、`completed` 或失败状态及运行标识，不伪造成功结果

### Requirement: 结果与报告下载

系统 MUST 展示运行状态、结果摘要、标准输出/错误摘要，并 MUST 提供现有 Markdown 和 HTML 报告下载。

#### Scenario: 完成任务

- **WHEN** 求解任务状态为 `completed`
- **THEN** 用户可查看结果摘要并下载对应 Markdown 或 HTML 报告

#### Scenario: 失败任务

- **WHEN** 求解任务状态为 `failed` 或 `not_implemented`
- **THEN** 界面显示错误原因和限制说明，不将任务显示为通过
