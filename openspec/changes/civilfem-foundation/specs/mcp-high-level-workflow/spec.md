# MCP High-Level Workflow

## ADDED Requirements

### Requirement: 高层工具契约
系统 MUST 暴露 inspect_input、extract_structural_model、validate_structural_model、build_mesh、submit_simulation、get_simulation_status、get_result_summary、generate_report 八个高层接口。

#### Scenario: 工具接口可调用
- **WHEN** MCP SDK 加载服务
- **THEN** 八个工具均注册且名称稳定

### Requirement: 结构化返回
每个接口 MUST 返回 JSON 可序列化结构，并包含状态字段；未实现能力 MUST 返回 `not_implemented`，不得伪造成功。

#### Scenario: 查询未实现网格
- **WHEN** 用户调用 `build_mesh` 且未安装网格后端
- **THEN** 返回 `not_implemented` 和明确原因

### Requirement: 运行状态
提交模拟 MUST 返回 `run_id`；状态接口 MUST 区分 `queued`、`running`、`failed`、`completed`。

#### Scenario: 查询任务状态
- **WHEN** 用户使用已返回的 `run_id` 查询任务
- **THEN** 系统返回任务标识和明确状态
