# CivilFEM Agent

基于 Python 的钢结构分析工具，支持构件参数检查、Gmsh 网格生成、OpenSeesPy/CalculiX 求解和计算报告输出。

项目主要用于学习和工程辅助分析，不替代规范验算、人工复核或正式工程审查。

## 部署

环境要求：Windows 10/11、Python 3.12+、Conda。

```powershell
git clone https://github.com/k1711019707-alt/civilfem-agent.git
cd civilfem-agent

conda create -n fangzhen python=3.12 -y
conda activate fangzhen
python -m pip install -e ".[dev,mcp,gui]"
```

CalculiX 不是 Python 依赖，需要单独安装。Windows 可将 `ccx.exe` 放在 `D:\CalculiX`，然后配置：

```powershell
$env:CIVILFEM_CALCULIX = "D:\CalculiX\ccx.exe"
```

## 使用

### 启动本地 PySide6 桌面界面（推荐）

```powershell
conda activate fangzhen
$env:CIVILFEM_PROJECT_ROOT = (Get-Location).Path
$env:CIVILFEM_CALCULIX = "D:\CalculiX\ccx.exe"
python desktop_gui.py
```

桌面界面不启动浏览器。图纸、网格、CalculiX、应力云图和 Markdown/HTML 报告均在本机完成。

### 启动中文 Web 兼容界面

```powershell
conda activate fangzhen
$env:CIVILFEM_PROJECT_ROOT = (Get-Location).Path
$env:CIVILFEM_CALCULIX = "D:\CalculiX\ccx.exe"
streamlit run gui.py
```

浏览器打开 `http://localhost:8501`，按页面提示上传 JSON 或 DXF 文件，再依次执行检查、建模、网格、求解和报告操作。

### 启动 MCP Server

```powershell
conda activate fangzhen
$env:CIVILFEM_PROJECT_ROOT = (Get-Location).Path
$env:CIVILFEM_CALCULIX = "D:\CalculiX\ccx.exe"
python mcp_server.py
```

MCP Server 提供输入检查、模型验证、网格生成、求解提交、状态查询、结果查询和报告生成接口。

### 运行测试

```powershell
conda activate fangzhen
python -m pytest -q
```

## 主要目录

```text
civilfem/       核心模型、输入、网格、求解和报告模块
gui.py          中文 Web 界面
mcp_server.py   MCP Server 入口
examples/       示例输入
tests/          自动化测试
```

## 主要开源组件

- [Gmsh](https://gmsh.info/)：网格生成
- [OpenSeesPy](https://openseespydoc.readthedocs.io/)：结构分析
- [CalculiX](https://github.com/Dhondtguido/CalculiX)：有限元求解
- [PyVista](https://pyvista.org/)：网格可视化
- [Model Context Protocol](https://github.com/modelcontextprotocol/python-sdk)：工具接口
