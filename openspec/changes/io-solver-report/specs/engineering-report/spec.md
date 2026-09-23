# Spec Delta

## Purpose

将输入、假设、网格、求解状态、结果摘要和校核限制整理为可读且可追溯的工程辅助报告，并明确报告不替代工程审查。

## ADDED Requirements

### Requirement: 报告输出
系统 MUST 支持 Markdown 和 HTML 报告，报告 MUST 包含运行标识、模型阶次、状态、结果摘要、假设、限制和证据路径。

#### Scenario: 完成任务报告
- **WHEN** 任务状态为 completed 且存在结果摘要
- **THEN** 系统生成 Markdown 或 HTML 文件并返回路径和 SHA-256 哈希

### Requirement: 未完成任务报告
系统 MUST 对失败或未实现任务生成带状态和错误原因的报告，不得把失败显示为通过。

#### Scenario: 求解器缺失
- **WHEN** 任务状态为 not_implemented
- **THEN** 报告明确显示未实现原因和工程限制
