# Spec Delta

## Purpose

为本地 FEM 结果提供可选的外部辅助分析能力，同时保持求解数值由本地 CalculiX 产生、凭据由本机安全配置提供且不进入报告或版本库。

## ADDED Requirements

### Requirement: Secure API configuration

系统 SHALL 优先从环境变量读取 Responses/FHL API URL、模型和密钥，并可从 `CIVILFEM_API_CONFIG` 指定的本机 JSON 配置读取；界面和日志 MUST 只显示脱敏后的配置状态。

#### Scenario: Missing credentials

- **WHEN** 未配置任何 API 密钥
- **THEN** 本地 FEM、云图和报告功能仍可运行，API 辅助入口显示“未配置”而不是抛出启动错误。

### Requirement: Engineering explanation guardrail

Responses API SHALL 仅接收结构化结果摘要并返回辅助解释；系统 MUST 明确标注该内容不替代工程复核，且不得用 API 输出覆盖 FEM 数值。

#### Scenario: API explanation succeeds

- **WHEN** 用户主动点击 AI 工程分析且本机 Responses 配置有效
- **THEN** 页面显示简体中文辅助解释、输入摘要和“需工程师复核”提示，关键应力/位移仍取自本地结果。

### Requirement: Resilient image assistance

FHL Images API SHALL 作为可选后处理入口；网络、HTTP 或响应格式错误 MUST 被转换为脱敏提示，并不得使本地求解结果或报告生成失败。

#### Scenario: Image API unavailable

- **WHEN** FHL Images API 超时或返回错误
- **THEN** 页面保留本地应力云图并提示图像辅助不可用，不显示 Authorization 值。
