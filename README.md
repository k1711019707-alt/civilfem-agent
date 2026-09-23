# CivilFEM Agent

开源优先的多构件土木结构有限元智能代理。项目把结构化输入、钢构件校核、Gmsh 网格、OpenSeesPy/CalculiX 求解、结果摘要和工程报告串成可追溯流程。

> 本项目用于学习和工程辅助分析，不替代规范验算、人工复核或正式工程审查。

## 能力

- JSON、IFC、DXF、STEP、FCStd 输入资产检查与 SHA-256 追踪
- 中文 GUI 支持 DXF 图纸检查、几何摘要和人工确认后建模
- Pydantic Canonical Structural Model 与钢构件插件验证
- Gmsh H 型钢实体四面体网格
- OpenSeesPy 二维线弹性悬臂梁求解
- CalculiX 外部求解器运行、状态查询和日志保存
- PyVista 离屏网格渲染
- Markdown/HTML 工程辅助报告
- MCP Server 工具暴露
- 运行目录白名单、路径越权拒绝、固定参数数组启动外部程序

## 环境

- Windows 10/11 x64
- Python 3.12+
- Conda 环境：`fangzhen`
- 可选后端：Gmsh、OpenSeesPy、CalculiX、PyVista

## 安装

```powershell
git clone https://github.com/k1711019707-alt/civilfem-agent.git
cd civilfem-agent

conda create -n fangzhen python=3.12 -y
conda activate fangzhen
python -m pip install -e ".[dev,mcp]"
```

CalculiX 可安装到 `D:\CalculiX`，并配置可执行文件：

```powershell
$env:CIVILFEM_CALCULIX = "D:\CalculiX\ccx.exe"
```

也可将 `D:\CalculiX` 加入用户 `PATH`。项目优先读取 `CIVILFEM_CALCULIX`，否则查找 `ccx`、`calculix`、`CalculiX`。

## 快速验证

```powershell
conda activate fangzhen
$env:CIVILFEM_CALCULIX = "D:\CalculiX\ccx.exe"
python -m pytest -q
```

当前验证基线：23 项测试通过。

## Python 流程示例

```python
import json
from civilfem.workflow import extract_structural_model, inspect_input, validate_structural_model
from civilfem.mcp_api import build_mesh, submit_simulation, generate_report

data = json.load(open("examples/steel_beam.json", encoding="utf-8"))
model = extract_structural_model(data)
validation = validate_structural_model(model)
payload = model.model_dump(mode="json")

mesh = build_mesh(payload, project_root=".", mesh_size=150)
run = submit_simulation(payload, project_root=".", backend="calculix", solver_input="path/to/model.inp")
report = generate_report(run["run_id"], project_root=".", fmt="markdown")
```

建议先检查输入并确认 `validation.status == "valid"`，再提交网格或求解任务。

## 中文 Web GUI

安装 GUI 可选依赖并启动：

```powershell
conda activate fangzhen
python -m pip install -e ".[gui]"
$env:CIVILFEM_PROJECT_ROOT = (Get-Location).Path
$env:CIVILFEM_CALCULIX = "D:\CalculiX\ccx.exe"
streamlit run gui.py
```

浏览器默认打开 `http://localhost:8501`。页面支持上传 JSON 或 DXF 图纸，按输入检查、模型验证、Gmsh 网格、OpenSeesPy/CalculiX 求解、状态查询和 Markdown/HTML 报告下载顺序操作。DXF 只提供图层、实体、边界和长度等几何证据；截面、材料、荷载、长度和边界必须人工确认。DWG 请先另存为 DXF。上传文件只写入 `CIVILFEM_PROJECT_ROOT` 下的 `.civilfem/uploads/`，GUI 不接受 shell 命令。

## MCP Server

```powershell
conda activate fangzhen
$env:CIVILFEM_PROJECT_ROOT = (Get-Location).Path
$env:CIVILFEM_CALCULIX = "D:\CalculiX\ccx.exe"
python mcp_server.py
```

已注册工具包括：

- `inspect_input`
- `extract_structural_model`
- `validate_structural_model`
- `build_mesh`
- `submit_simulation`
- `get_simulation_status`
- `get_result_summary`
- `generate_report`

## 项目结构

```text
civilfem/                  核心模型、输入、网格、求解、报告和安全边界
examples/                  示例结构化输入
tests/                     自动化测试
steel-check-mcp/           既有钢构件规范校核核心
openspec/                  需求、设计和实现任务记录
mcp_server.py              MCP 协议入口
pyproject.toml             Python 包和可选依赖
```

`gui.py` 提供中文 Streamlit Web GUI；运行 `streamlit run gui.py` 即可打开浏览器控制台。

## 运行产物

每次任务写入配置项目根下的：

```text
.civilfem/runs/<run_id>/
```

目录包含运行清单、网格、求解日志、结果摘要和报告。`run_id` 由系统生成，输入路径必须位于 `CIVILFEM_PROJECT_ROOT` 内。

## 开源组件

- [Gmsh](https://gmsh.info/)：几何和网格
- [OpenSeesPy](https://openseespydoc.readthedocs.io/)：结构分析
- [CalculiX](https://github.com/Dhondtguido/CalculiX)：有限元求解
- [PyVista](https://pyvista.org/)：可视化
- [IfcOpenShell](https://ifcopenshell.org/)：IFC 检查
- [ezdxf](https://ezdxf.readthedocs.io/)：DXF 检查
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)：工具协议

各组件按其自身许可证使用。部署或再分发二进制文件前，请分别核对第三方许可证。

[Streamlit](https://streamlit.io/) 用于中文 Web GUI。

## 限制

- 首版只提供 H 型钢几何与部分梁/构件分析流程。
- IFC、DXF、网格和求解器能力依赖本地可选安装。
- CalculiX 结果日志已接入；复杂结果文件的统一后处理仍需按算例扩展。
- 报告是工程辅助输出，不是正式设计结论。

## 许可证

本项目代码许可证待补充。第三方依赖和 CalculiX 不继承本项目未声明的许可证。
