# Spec Delta

## Purpose

将已确认的 CivilFEM 深色工程控制台视觉稿落实为固定布局的桌面窗口，确保关键状态、应力云图和工程摘要具有一致的信息层级和视觉比例。

## ADDED Requirements

### Requirement: Fixed engineering console layout

桌面窗口 SHALL 使用深色背景并固定呈现顶部项目/模型/求解状态栏、左侧 CAD/Model/Mesh/Solve/Report 流程导航、中间主云图区、右侧结果摘要和底部进度时间线。

#### Scenario: Completed result view

- **WHEN** FEM 运行完成
- **THEN** 用户可在同一窗口同时看到应力色标云图、最大应力、最大位移、网格信息、求解器信息和完成状态。

### Requirement: Engineering visualization

应力云图 SHALL 使用深色画布、蓝青绿黄红工程色标、可见网格边线和单位标注；无结果时主视图区 SHALL 显示 CAD/网格预览或清晰的待处理状态。

#### Scenario: No result yet

- **WHEN** 用户尚未运行求解
- **THEN** 中间区域显示 CAD 或网格预览及当前流程提示，而不是空白白色区域。
