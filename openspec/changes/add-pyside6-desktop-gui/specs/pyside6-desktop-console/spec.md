# Spec Delta

## Purpose

为 CivilFEM 提供无需浏览器的本地工程桌面工作台，使工程师可以在单一窗口中完成 CAD 导入、模型确认、网格、CalculiX 求解、云图查看和报告导出。

## ADDED Requirements

### Requirement: Local desktop workflow

系统 SHALL 提供本地桌面窗口，用户可选择 JSON/DXF 文件、查看 CAD 几何摘要、显式选择 H 型钢梁映射、生成网格、运行 CalculiX、查看结果并导出报告。

#### Scenario: Start desktop application

- **WHEN** 用户运行桌面入口
- **THEN** 系统打开本地 CivilFEM 窗口，不启动浏览器，不依赖 Streamlit 页面。

### Requirement: Non-blocking analysis

求解和报告生成 SHALL 在后台任务中执行，窗口在任务期间保持响应，并显示当前步骤、进度和错误摘要。

#### Scenario: Run FEM

- **WHEN** 用户点击运行三维 FEM
- **THEN** 界面显示求解中状态，用户仍可查看窗口；完成后刷新云图和右侧结果摘要。

### Requirement: Local credentials

桌面 GUI SHALL 复用现有 API 客户端和本机配置，但不得在界面、日志、报告或 Git 文件中显示或保存完整 URL/Key。

#### Scenario: API unavailable

- **WHEN** 本机 API 配置缺失或请求失败
- **THEN** 本地 FEM 和报告流程仍可运行，AI 分析按钮显示脱敏错误。
