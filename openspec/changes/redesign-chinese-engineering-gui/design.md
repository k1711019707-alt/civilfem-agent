# Design

## Context

当前 `gui.py` 已串联输入检查、Gmsh、CalculiX、报告和云图，但页面是纵向表单，部分区域仍使用 JSON 查看器。核心求解接口已稳定，改造应集中在呈现层和可选 API 辅助层；运行环境为本机 Windows，API 密钥不能写入仓库。

## Goals / Non-Goals

**Goals:**

- 保留现有输入、网格、求解、报告调用，替换为三栏深色工程控制台布局。
- 把复杂返回值转换成有限个工程 KPI 和可展开诊断。
- 通过独立配置/客户端模块接入 Responses 与 FHL Images，并支持无凭据降级。
- 为配置脱敏、mock HTTP、GUI smoke 和真实 CalculiX 流程提供验证。

**Non-Goals:**

- 不改写 CalculiX 输入格式、`.frd` 解析或应力计算算法。
- 不让外部 API 生成、修正或覆盖 FEM 数值。
- 不提交海之子配置文件、密钥、`.env` 或运行产物。

## Decisions

1. **配置来源**：环境变量优先，其次读取 `CIVILFEM_API_CONFIG` 指向的 JSON；不自动复制外部项目文件。这样便于复用本机配置且避免凭据进入 Git。备选是 Streamlit secrets，但 Windows 本机已有外部配置且测试更容易隔离。
2. **HTTP 客户端**：使用 Python 标准库 `urllib`，提供 URL 规范化、超时、JSON 解析和错误脱敏。避免新增依赖；备选是 `requests`，但当前项目无需为两类 API 增加依赖。
3. **GUI 布局**：顶部状态栏 + 左侧五步导航 + 中央云图/输入工作区 + 右侧 KPI/AI 摘要 + 底部进度条；采用少量 CSS 仅实现用户明确要求的深色视觉稿，业务组件仍使用原生 Streamlit。
4. **API 边界**：Responses 只接收白名单结果摘要；FHL Images 只做可选图片后处理。所有 API 失败均为非阻塞，主流程继续使用本地结果。
5. **日志策略**：移除默认 `st.json` 全量展示，保留截断后的错误和可选诊断 expander。这样符合“GUI 不打印过多日志”要求。

## Risks / Trade-offs

- [外部 API 不可用] → 本地结果优先，API 调用捕获超时/HTTP/JSON 错误并脱敏。
- [Streamlit 版本差异] → 使用兼容的 `st.columns`、`st.container`、`st.metric`，AppTest 覆盖页面启动。
- [编码环境显示异常] → 文件统一 UTF-8，测试通过后用 UTF-8 读取关键文案。
- [视觉 CSS 依赖内部选择器] → CSS 仅控制背景、边框和间距；核心布局不依赖内部 DOM 结构。

## Migration Plan

1. 增加 API 配置/客户端和 OpenSpec 规格，不改变现有求解 API。
2. 替换 GUI 渲染段；保留原有辅助函数和测试调用接口。
3. 运行单元、AppTest、compileall、真实 CalculiX 和报告验证。
4. 仅提交明确源码、测试、规格和文档；如 GUI smoke 失败，可回滚单个 GUI 提交而不影响 FEM 模块。
