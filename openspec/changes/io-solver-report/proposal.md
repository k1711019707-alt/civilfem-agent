# Proposal

## Why

当前高层 MCP 接口仍把输入检查、网格、求解和报告全部返回 `not_implemented`，无法形成可运行的工程闭环。本变更先接入可检测、可复现、可审计的输入资产、可选开源后端和 Markdown/HTML 报告。

## What Changes

- 增加 JSON、IFC、DXF 输入资产检查；STEP/FCStd 返回真实能力状态和可行动原因。
- 增加 Gmsh 能力探测与受控网格任务清单，输出网格资产状态和哈希。
- 增加 CalculiX/OpenSeesPy 后端探测、运行清单、状态查询和资源/路径边界。
- 增加统一运行目录、结果摘要和 Markdown/HTML 报告生成。
- 增加测试、可选开源依赖组和示例输入。

## Capabilities

### New Capabilities

- `input-asset-inspection`: 多格式输入资产检查和结构化诊断。
- `simulation-run-lifecycle`: 网格/求解运行清单、状态和安全边界。
- `engineering-report`: 结果摘要与带限制声明的报告输出。

### Modified Capabilities

- 无。

## Impact

- 修改 `civilfem/workflow.py`、`civilfem/mcp_api.py` 和 `mcp_server.py`。
- 新增输入、运行、报告模块及集成测试。
- IFC、DXF、meshio、gmsh 为可选开源依赖；未安装时返回明确状态，不影响核心模型测试。
