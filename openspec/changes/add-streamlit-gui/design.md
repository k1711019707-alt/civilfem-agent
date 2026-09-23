# Design

## Context

现有项目已经提供 `civilfem.mcp_api` 高层函数、运行清单和报告生成器。GUI 只做交互编排，不复制模型、网格、求解或报告逻辑。

## Goals / Non-Goals

**Goals:**

- 用一个可直接运行的 Streamlit 页面串联已存在的后端能力。
- 保持中文界面、明确状态和失败原因。
- 让 GUI 生成的文件仍受 `CIVILFEM_PROJECT_ROOT` 和现有运行目录约束。

**Non-Goals:**

- 不新增独立 HTTP API、用户系统或数据库。
- 不在浏览器端实现有限元算法或任意命令执行。
- 不替代 MCP Server。

## Decisions

- 使用 Streamlit 单文件入口 `gui.py`：依赖少、适合本地工程工具，优于新增前后端分离项目。
- 使用 `st.session_state` 保存上传模型、运行标识和报告路径：支持页面重绘，不引入持久化数据库。
- 上传文件写入配置项目根下临时输入目录，再调用现有 `inspect_input`、`build_mesh`、`submit_simulation` 和 `generate_report`。
- CalculiX 输入使用文件上传，不允许用户输入命令字符串；后端调用继续使用固定参数数组。
- 页面先显示能力状态；不可用后端使用禁用控件或明确错误提示。
- 网格预览使用现有 PNG 产物，报告下载使用现有报告文件内容。

## Risks / Trade-offs

- [Streamlit 未安装] → 将其放入可选依赖并在 README 提供安装命令。
- [页面刷新丢失大文件] → 只在会话中保存路径和摘要，运行产物继续落盘。
- [长时间求解阻塞页面] → 首版复用现有同步 API，显示运行状态；后续可再引入异步队列。
- [用户上传文件越权] → 统一写入配置项目根临时目录，不接受外部任意路径。

## Migration Plan

安装 `.[gui]` 后运行 `streamlit run gui.py`。删除 `gui.py` 和可选依赖即可回滚，不影响 MCP 和 Python API。
