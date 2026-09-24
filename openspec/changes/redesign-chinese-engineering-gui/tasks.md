# Tasks

## 1. API 基础

- [x] 1.1 新增安全配置模型，验证环境变量/外部 JSON 优先级、缺失密钥降级和脱敏输出
- [x] 1.2 新增 Responses/FHL Images 标准库客户端，验证 URL、超时、HTTP 错误和响应解析
- [x] 1.3 新增 mock API 测试，确保 Authorization 不出现在异常、日志或返回摘要中

## 2. 中文工程控制台

- [x] 2.1 将 GUI 顶部、左侧流程、中央工作区和右侧 KPI 重排为深色工程控制台，并验证页面主要文案为简体中文
- [x] 2.2 将结果展示收敛为应力/位移/网格/求解摘要、云图和报告下载，验证不默认渲染完整 JSON/日志
- [x] 2.3 增加 AI 工程分析入口和“辅助解释、不替代工程复核”提示，验证 API 不覆盖本地 FEM 数值

## 3. 验证与交付

- [x] 3.1 增加 Streamlit AppTest 或导入 smoke 测试，验证无上传、有效模型和失败结果页面
- [x] 3.2 运行 pytest、compileall、git diff --check，并完成真实 CalculiX 云图/报告流程
- [x] 3.3 检查提交内容不含密钥、`.env`、`.civilfem` 运行产物，提交并推送 GitHub
