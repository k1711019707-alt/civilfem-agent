# Spec Delta

## Purpose

将本地三维 FEM 结果转换为工程师可快速复核的应力、位移、网格和报告摘要，并保留完整云图与报告下载能力。

## ADDED Requirements

### Requirement: Professional FEM result presentation

系统 SHALL 在 GUI 中以专业摘要方式呈现三维 FEM 结果：显示最大 von Mises 应力、最大位移、网格节点/单元统计、求解器状态、应力云图以及 Markdown/HTML 报告下载；原始节点场数据不得默认展开。

#### Scenario: FEM result available

- **WHEN** 运行结果包含 `max_von_mises`、`max_displacement` 或 `stress_cloud`
- **THEN** GUI 显示对应 KPI 和云图文件，并允许下载报告，不打印完整结果数组。
