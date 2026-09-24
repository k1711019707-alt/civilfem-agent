# Proposal

## Why

复杂 DXF 当前只被读取为二维统计，确认参数后却固定生成 H 型钢梁模型，导致输入图纸与输出结果不一致。现有 GUI 也与已确认的深色工程控制台视觉稿存在明显差异，需要同时修正数据边界和界面呈现。

## What Changes

- **BREAKING**：复杂 DXF 不再默认转换为 `steel_beam`；没有明确工程映射时，流程停留在“几何已识别、等待建模确认”。
- 增加 CAD 几何预览/摘要，显示实体类型、图层、边界和识别置信状态。
- 仅当用户显式选择“H 型钢梁映射”并填写参数后，才允许进入 Gmsh/CalculiX。
- 非 H 型钢梁图纸显示可解释的阻断原因，不伪造应力结果。
- 按视觉稿重排 GUI：顶部项目/模型/求解状态栏，左侧流程导航，中间深色云图工作区，右侧结果摘要，底部流程时间线。
- 应力云图采用深色背景、网格边线和工程色标，避免白色画布破坏视觉一致性。
- 增加回归测试，确认复杂 DXF 不会静默变成钢梁；确认 Git 不跟踪本地 URL、Key 或配置文件。

## Capabilities

### New Capabilities

- `cad-geometry-fidelity`: CAD 输入必须保留真实几何语义，显式映射后才可分析。
- `fem-console-visual-fidelity`: GUI 布局、色彩和结果云图遵循已确认工程控制台视觉稿。

### Modified Capabilities

无。

## Impact

- 修改 `gui.py`、`civilfem/inputs.py`、`civilfem/visualization.py` 和相关测试。
- 可能扩展 CAD 状态字段，但不改变 JSON 钢梁输入和既有 CalculiX 求解格式。
- 更新 `.gitignore` 与安全扫描测试，确保外部本机 API 配置永不提交。
