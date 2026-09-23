# Design

## Context

首版已有 Canonical Model、钢构件插件和 8 个 MCP 工具名称，但网格、求解和报告为空实现。实现必须保持可选依赖，不让重型 CAD/FEM 安装阻塞核心模型。

## Goals / Non-Goals

**Goals:**

- 让输入检查和报告真实可运行。
- 用白名单根目录和参数数组约束外部进程。
- 在后端缺失时返回证据充分的状态。

**Non-Goals:**

- 本变更不实现完整 IFC 到实体网格自动建模。
- 本变更不宣称 CalculiX/OpenSeesPy 在当前机器必然安装。
- 本变更不输出规范设计结论。

## Decisions

- 使用标准库 `hashlib`、`pathlib`、`subprocess` 实现生命周期，减少核心依赖。
- IFC/DXF 使用可选 IfcOpenShell/ezdxf；导入失败返回诊断，不回退到猜测。
- 运行清单使用 JSON 文件，便于 MCP、审计和后续 SQLite 替换。
- 报告先生成 Markdown，再用标准库转义生成简单 HTML，避免模板依赖。

## Risks / Trade-offs

- [可选库缺失] -> 保留能力探测和明确 not_implemented 状态。
- [外部求解器输出格式差异] -> 首版只记录命令、日志和状态，结果解析单独适配。
- [运行目录残留] -> 每次使用唯一 run_id，提供状态和清理依据。

## Migration Plan

保留现有 8 个函数签名；内部改为调用新模块。旧钢校核输出不变。失败时无需迁移，删除运行目录即可回滚。
