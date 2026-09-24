# Spec Delta

## Purpose

为结构工程师提供一个简体中文、低噪声、可核查的有限元工作台，使模型输入、网格、求解、云图和报告状态在同一工程控制台中可见。

## ADDED Requirements

### Requirement: Chinese engineering console

系统 SHALL 以简体中文显示主要导航、按钮、状态、指标和错误信息，并保留 Gmsh、CalculiX、FEM、von Mises、MPa、mm 等技术名词。

#### Scenario: Initial console

- **WHEN** 用户打开 Streamlit 页面且尚未上传模型
- **THEN** 页面显示中文工程标题、五步流程导航、项目/求解状态卡片和模型上传入口，不显示英文操作文案。

### Requirement: Professional result summary

系统 SHALL 将求解结果以最大 von Mises 应力、最大位移、节点数、单元数、求解器和运行时间等摘要呈现，并提供应力云图和报告下载入口。

#### Scenario: Completed FEM run

- **WHEN** CalculiX 三维分析完成且结果文件有效
- **THEN** 页面显示应力云图、关键 KPI、网格质量和 Markdown/HTML 报告下载按钮。

### Requirement: Low-noise diagnostics

系统 SHALL 默认隐藏原始 stdout、stderr、完整节点数组和完整运行 manifest，仅在用户主动展开诊断区域时显示经过裁剪的错误或调试信息。

#### Scenario: Solver failure

- **WHEN** 求解失败
- **THEN** 页面显示脱敏后的可行动错误摘要，不直接打印完整求解日志或 API 凭据。
