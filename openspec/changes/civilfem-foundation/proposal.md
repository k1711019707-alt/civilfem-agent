# Proposal

## Why

当前仓库只有钢构件截面校核原型，缺少方案要求的统一结构模型、构件插件、输入验证和高层工作流接口。现在建立最小可运行基础，可复用现有确定性钢构件校核逻辑，并为 IFC、网格、求解器和报告适配器保留清晰边界。

## What Changes

- 新增版本化 Pydantic Canonical Structural Model，保存项目、构件、材料、荷载、边界、证据和置信度。
- 新增钢梁、钢柱插件，复用现有 `steelcheck.py` 确定性校核能力。
- 新增 JSON 输入检查、单位和关键参数验证，缺失关键参数时返回 `pending_confirmation`。
- 新增 8 个高层 MCP 工具接口骨架：inspect、extract、validate、mesh、submit、status、result、report。
- 新增 pytest 单元测试和最小依赖锁定；首版不假装实现 IFC/Gmsh/CalculiX/PyVista 全链路。

## Capabilities

### New Capabilities

- `canonical-structural-model`: 版本化统一结构模型及校验状态。
- `component-plugin-workflow`: 钢梁、钢柱插件和确定性校核适配。
- `mcp-high-level-workflow`: 受控高层工具契约和运行状态接口。

### Modified Capabilities

- 无。

## Impact

- 新增 `civilfem/` Python 包、`mcp_server.py`、测试和依赖文件。
- 复用 `steel-check-mcp/steelcheck.py`；不改其既有输出契约。
- `fangzhen` Conda 环境安装 Python 3.12、Pydantic、pytest；MCP SDK作为可选运行依赖。
