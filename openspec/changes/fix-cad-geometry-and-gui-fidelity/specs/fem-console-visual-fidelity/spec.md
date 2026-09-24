# Spec Delta

## Purpose

让实际 Streamlit 页面在信息层级、深色配色、流程导航和应力结果展示上接近已确认的 CivilFEM 工程控制台视觉稿，而不是普通表单页面。

## ADDED Requirements

### Requirement: Engineering console layout

GUI SHALL 提供顶部项目/模型/求解状态栏、左侧五步流程导航、中间主视图区、右侧结果摘要和底部进度时间线；主要卡片使用深色背景与蓝色工程强调色。

#### Scenario: Console with uploaded model

- **WHEN** 用户打开页面并上传模型
- **THEN** 页面同时显示项目、模型、求解状态、流程步骤、主视图区和结果摘要，不将 API 配置卡片挤占主工作区。

### Requirement: Dark stress visualization

应力云图 SHALL 使用深色工程背景、可读的蓝-青-绿-黄-红色标尺、网格边线和最大值标注；不得默认使用大面积白色画布。

#### Scenario: Stress cloud available

- **WHEN** FEM 结果包含应力场和云图
- **THEN** GUI 在主视图区显示深色背景云图，并在右侧摘要显示最大 von Mises 应力和最大位移。
