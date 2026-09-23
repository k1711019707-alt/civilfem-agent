# Proposal

## Why

当前项目只有 Python API 和 MCP Server，没有面向工程人员的可视化入口。用户需要手动编写 JSON、准备求解输入并读取运行目录，验证网格和报告的成本较高。增加轻量中文 Web GUI，可让首次使用者在浏览器中完成同一条受控流程。

## What Changes

- 新增基于 Streamlit 的中文单页 Web GUI。
- 支持 JSON 上传、输入检查、Canonical Model 提取和模型验证。
- 支持 Gmsh 网格生成、PNG 预览、OpenSeesPy/CalculiX 后端选择和求解提交。
- 支持运行状态、日志、结果摘要和 Markdown/HTML 报告下载。
- 增加 `streamlit` 可选依赖、GUI 启动说明和 GUI 回归测试。
- 保留现有 Python API、MCP 工具和安全路径边界，不引入任意 shell 执行。

## Capabilities

### New Capabilities

- `web-gui`: 中文浏览器界面，串联输入、验证、网格、求解、状态、结果和报告下载。

### Modified Capabilities

无。GUI 复用现有运行生命周期和报告接口，不改变其既有行为契约。

## Impact

- 新增 `gui.py`、GUI 测试和 Streamlit 可选依赖。
- 修改 `pyproject.toml`、`README.md`。
- 不修改 MCP 工具签名，不新增服务端口以外的外部系统依赖。
