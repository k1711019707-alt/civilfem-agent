# Spec Delta

## Purpose

为每次三维有限元运行生成适合工程复核的结构化报告，集中呈现输入、网格、求解状态、关键结果、应力云图和适用限制。

## ADDED Requirements

### Requirement: 专业工程报告

系统 SHALL 生成 Markdown 和 HTML 两种报告，至少包含运行信息、模型与材料、网格统计、边界和载荷、求解器状态、最大位移、最大 von Mises 应力、云图附件和限制声明。

#### Scenario: FEM 运行完成
- **WHEN** 运行状态为 `completed` 且存在结构化结果
- **THEN** 报告展示关键数值、单位、结果文件路径和应力云图，并保留结果哈希

#### Scenario: 运行失败或未配置
- **WHEN** 运行状态为 `failed` 或 `not_implemented`
- **THEN** 报告展示失败原因和缺失条件，不显示虚假的应力结论

### Requirement: Streamlit 结果展示

Streamlit 页面 SHALL 提供应力云图预览、关键 FEM 指标展示和 Markdown/HTML 报告下载。

#### Scenario: 用户查看完成运行
- **WHEN** 运行完成且云图存在
- **THEN** 页面显示云图、最大应力、最大位移，并提供报告下载按钮
