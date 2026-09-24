# Design

## Context

当前 DXF 检查器能得到图层、实体类型和边界，但 GUI 的 `build_cad_model` 将所有确认参数写成 `steel_beam`，后端网格器也只有 H 型截面实现。当前云图由 PyVista 离屏渲染，默认白色背景；GUI 的主工作区顺序与视觉稿不一致。

## Goals / Non-Goals

**Goals:**

- 在数据层明确区分 CAD 检查结果、结构映射和可求解 Canonical Model。
- 保留复杂 DXF 的真实摘要，并在未映射时阻断求解。
- 通过显式映射保留现有钢梁 FEM 能力。
- 重排 Streamlit 页面并调整云图渲染，使其接近视觉稿。
- 检查 Git 跟踪对象，禁止本机 URL/Key 和配置文件进入提交。

**Non-Goals:**

- 本次不实现任意建筑平面图到完整有限元实体的自动识别。
- 不伪造复杂 CAD 的材料、边界或荷载。
- 不更换 CalculiX、Gmsh 或 PyVista。

## Decisions

1. **状态分层**：DXF 检查返回 `geometry_status`、`mapping_status` 和 `analysis_ready`；比用一个 `status` 字段猜测更能避免误进 FEM。备选是继续复用 Canonical Model，但会丢失未映射状态。
2. **显式映射控件**：GUI 默认选择“仅查看 CAD 几何”，用户必须切换到“H 型钢梁映射”才看到工程参数表。备选是默认展示参数表，容易再次误导用户。
3. **云图主题**：在 PyVista 设置背景、边线、色标和最大值注释；不把视觉效果交给浏览器 CSS，因为图片本身需要在报告中保持一致。
4. **布局**：保留原生 Streamlit columns/container 作为结构，CSS 只控制视觉稿要求的背景、边框、间距和状态强调，降低升级风险。
5. **凭据防护**：配置模块只读外部路径/环境变量；新增 Git 追踪扫描测试，源码中不出现真实 URL/Key，默认路径也不写入配置内容。

## Risks / Trade-offs

- [复杂 DXF 暂时无法直接求解] → 明确显示几何摘要和映射建议，允许用户手动映射到受支持模型。
- [视觉稿与 Streamlit 原生 DOM 有差异] → 使用稳定的容器和有限 CSS，并以 AppTest 验证页面结构。
- [云图背景变化影响已有截图] → 保留字段、色标和数值不变，只调整背景和可读性。

## Migration Plan

1. 先加入 DXF 映射失败测试和 Git 密钥扫描测试。
2. 修改 GUI 状态流和云图渲染。
3. 运行全量测试、复杂 DXF smoke、真实 CalculiX 钢梁流程和 AppTest。
4. 提交时仅加入明确源码/测试/规格，不加入 `.civilfem`、本机配置或截图运行产物。
