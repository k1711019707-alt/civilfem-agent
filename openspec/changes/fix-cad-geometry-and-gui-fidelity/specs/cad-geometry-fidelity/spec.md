# Spec Delta

## Purpose

确保 CAD 图纸的真实几何、图元类型和建模状态在分析前被保留和展示，防止复杂图纸被静默替换成不相干的默认钢梁模型。

## ADDED Requirements

### Requirement: Explicit CAD-to-analysis mapping

系统 SHALL 区分“CAD 几何已识别”和“可用于 FEM 的结构模型”。复杂 DXF 在没有用户明确选择结构映射、材料、截面、边界和荷载前 MUST 停止在待确认状态，不得生成 `steel_beam` 结果。

#### Scenario: Complex DXF without mapping

- **WHEN** 用户上传包含多种图元或多个图层的复杂 DXF，且未选择结构映射
- **THEN** GUI 显示真实几何摘要和“等待建模确认”，不允许生成钢梁网格、应力云图或钢梁报告。

### Requirement: Explicit beam mapping

系统 SHALL 仅在用户主动选择“H 型钢梁映射”并提交完整截面、材料、长度、边界和荷载参数后，才创建 `steel_beam` Canonical Model 并进入 FEM 流程。

#### Scenario: User confirms beam mapping

- **WHEN** 用户选择 H 型钢梁映射并填写有效工程参数
- **THEN** 系统创建带有映射来源标记的钢梁模型，并允许生成网格和求解。

### Requirement: Honest unsupported geometry state

系统 MUST 对无法直接映射的 CAD 几何返回可解释状态和下一步建议，不得用默认参数伪造结构分析结果。

#### Scenario: Unsupported plan drawing

- **WHEN** DXF 主要由平面图、文字、块引用或多构件线框组成
- **THEN** 系统显示“几何已识别但当前求解器不支持直接分析”，并保留原图纸摘要供后续建模。
