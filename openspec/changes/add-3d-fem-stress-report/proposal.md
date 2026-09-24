# Proposal

## Why

现有工作流只输出运行清单和求解 JSON，不能展示三维有限元应力分布，也不利于工程复核。项目已具备 Gmsh 网格、CalculiX 入口和本机 `D:\CalculiX\ccx.exe`，现在补齐真实求解、结果提取、应力云图和专业报告。

## What Changes

- 增加三维实体网格到 CalculiX `.inp` 的转换。
- 调用本机 CalculiX 执行静力有限元分析。
- 解析 CalculiX `.frd`，保存节点位移、应力和 von Mises 应力摘要。
- 使用 PyVista 生成应力云图 PNG，并在 Streamlit 页面预览和下载。
- 重做 Markdown/HTML 报告，加入工程信息、网格、材料、边界、求解指标、结果文件和限制说明。
- 将 `examples/cad_samples` 测试图纸纳入版本库。

## Capabilities

### New Capabilities

- `three-dimensional-fem-stress`: 使用 CalculiX 执行三维实体有限元分析，提取应力结果并生成云图。
- `engineering-report`: 输出包含 FEM 结果和可视化附件的专业工程报告。

### Modified Capabilities

- 无

## Impact

- 影响 `civilfem/meshing.py`、`civilfem/solvers.py`、`civilfem/reports.py`、`civilfem/visualization.py`、`civilfem/mcp_api.py` 和 `gui.py`。
- 可能新增 `meshio`、`pyvista` 结果处理依赖；CalculiX 通过 `CIVILFEM_CALCULIX` 或 PATH 发现。
- 新增求解运行目录文件：`.inp`、`.frd`、结果 JSON、应力云图 PNG、Markdown/HTML 报告。
- 上传 `examples/cad_samples` 中测试 DXF 与说明文件。
