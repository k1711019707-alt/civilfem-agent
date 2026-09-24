# Proposal

## Why

当前 CivilFEM Streamlit 页面仍是线性表单，结果摘要和求解状态不够专业，且缺少统一的简体中文工程控制台视图。现在需要把已验证的网格、CalculiX、应力云图和报告能力集中到清晰的工程工作流中，并接入可选 API 辅助解释，同时确保密钥不进入仓库。

## What Changes

- 重做 Streamlit 主界面为深色工程控制台：中文流程导航、求解状态、网格质量、运行时间、结果 KPI 和应力云图。
- 统一所有用户可见文案为简体中文；保留 Gmsh、CalculiX、FEM、von Mises、MPa、mm 等技术名词。
- 隐藏原始 stdout/stderr、节点数组和完整运行 JSON，仅展示工程摘要及可展开的必要诊断信息。
- 新增安全 API 配置加载：优先环境变量，可选读取本机外部配置文件；界面只显示脱敏状态。
- 新增 Responses API 工程结果解释入口；API 只能辅助解释，不得伪造或改写 FEM 数值。
- 新增 FHL Images API 客户端能力，为结果图后处理保留受控入口；失败时不影响本地 FEM 主流程。
- 增加 API 配置、脱敏、mock 请求和 GUI smoke 测试，并完成全流程验证。

## Capabilities

### New Capabilities

- `chinese-engineering-gui`: 深色简体中文工程控制台、结果摘要、应力云图和低噪声交互。
- `api-assisted-engineering-analysis`: 安全加载 API 配置，并对工程结果提供可选的辅助解释与图像后处理。
- `fem-stress-report-presentation`: 以专业摘要方式呈现既有三维 FEM 应力云图、位移和报告结果。

### Modified Capabilities

无。

## Impact

- 修改 `gui.py`，新增 `civilfem/api_config.py` 与 `civilfem/api_client.py`。
- 增加 OpenSpec capability/spec、单元测试和 Streamlit AppTest smoke 测试。
- 运行时可读取海之子同源的本机 URL/Key 配置，但不复制或提交完整密钥。
- 不改变既有 CalculiX、Gmsh、报告文件格式和核心求解接口。
