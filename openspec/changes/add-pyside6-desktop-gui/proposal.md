# Proposal

## Why

当前 CivilFEM 仍以 Streamlit 网页形式运行，浏览器控件、白色图像画布和响应式布局无法一比一复刻已确认的深色工程控制台视觉稿。需要改成本地 PySide6 桌面应用，使工程师在本机窗口中直接完成 CAD 导入、网格、CalculiX 求解、云图和报告操作。

## What Changes

- 新增 PySide6 本地桌面入口，不再把 Streamlit 作为主 GUI。
- 一比一复刻视觉稿的顶部状态栏、左侧流程导航、中间三维应力云图区、右侧结果摘要和底部进度时间线。
- 本地桌面 GUI 使用简体中文和深色工程控制台主题。
- 复用现有 CAD 检查、显式 H 型钢梁映射、Gmsh、CalculiX、应力云图、报告和 API 客户端。
- 增加文件选择、参数确认、异步求解、错误提示、报告导出和 API 辅助分析按钮。
- 保留 Streamlit 文件以便兼容旧部署，但桌面入口成为推荐启动方式。
- PySide6 作为可选 GUI 依赖，不影响核心 FEM 模块和无 GUI 测试。

## Capabilities

### New Capabilities

- `pyside6-desktop-console`: 本地桌面工程控制台及完整 FEM 工作流。
- `desktop-visual-fidelity`: 桌面窗口按视觉稿提供固定比例、深色主题和状态布局。

### Modified Capabilities

无。

## Impact

- 新增 `desktop_gui.py` 和桌面 GUI 测试。
- 修改 `pyproject.toml` 增加 `desktop` 可选依赖。
- 复用 `civilfem` 后端，不改变 CalculiX 输入、结果解析和报告格式。
- 运行时 API 配置继续从环境变量或 `%LOCALAPPDATA%\CivilFEM\api_config.json` 读取，不提交 URL/Key。
