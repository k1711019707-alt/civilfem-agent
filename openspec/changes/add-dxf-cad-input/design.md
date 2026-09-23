# Design

## Context

现有 `civilfem.inputs.inspect_asset` 已能读取 DXF 并统计模型空间实体，但只返回数量和图层；GUI 目前只接收 JSON。CAD 图纸中的截面、材料、荷载和边界通常不完整，必须保留人工确认边界。

## Goals / Non-Goals

**Goals:**

- 扩展 DXF 检查结果，加入二维边界、线段长度和实体类型统计。
- 在 Streamlit GUI 中提供 DXF 上传、摘要展示和参数确认表单。
- 将确认参数转换为既有 Canonical Model，复用现有网格、求解和报告 API。

**Non-Goals:**

- 不直接解析 DWG，不引入闭源 CAD SDK。
- 不从任意 CAD 图元自动推断材料、荷载、支座或设计结论。
- 不改变既有 JSON 输入、MCP API 和求解器接口。

## Decisions

- 使用 `ezdxf` 作为 DXF 解析器，保持开源优先和当前可选依赖结构。
- 对 LINE、LWPOLYLINE、POLYLINE、ARC、CIRCLE 等图元提取边界；未知实体仍计入实体统计。
- 几何摘要作为证据，不直接作为工程参数；用户在 GUI 表单中确认 H 型截面、钢材牌号、长度、荷载和边界。
- DXF 建模结果使用与 JSON 相同的 `CanonicalModel`，避免复制下游流程。
- GUI 使用 `st.form` 批量提交参数，防止每次控件变化触发高成本操作；预览图使用 `st.image`。

## Risks / Trade-offs

- [图纸单位缺失] → 显示单位待确认，长度默认只作为几何参考，不自动用于正式模型。
- [二维图纸不是实体模型] → 只生成用户确认的简化 H 型构件模型，并在界面标记假设。
- [DWG 无法直接读取] → 提示用户从 AutoCAD/兼容软件另存为 DXF。
- [超大 DXF 解析耗时] → 沿用 256 MiB 输入上限，并限制摘要计算为受控图元范围。

## Migration Plan

安装现有 `formats` 依赖后即可使用 DXF。旧 JSON 流程保持不变。删除新增摘要和 GUI 分支即可回滚。

