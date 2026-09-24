# Tasks

## 1. Desktop foundation

- [x] 1.1 增加 PySide6 可选依赖和 `desktop_gui.py` 入口，验证无 Qt 环境时导入错误清晰
- [x] 1.2 实现顶部状态栏、左侧流程导航、中间视图区、右侧摘要和底部时间线，验证 offscreen 窗口结构
- [x] 1.3 加入视觉稿深色 QSS、固定比例、字体层级和卡片样式，验证截图无白色主画布

## 2. Backend workflow

- [x] 2.1 接入 JSON/DXF 文件选择、CAD 预览和显式 H 型钢梁映射，验证复杂 DXF 不自动变钢梁
- [x] 2.2 实现后台网格/FEM worker、状态信号和错误处理，验证窗口不卡死且结果更新
- [x] 2.3 接入云图、KPI、AI 分析和 Markdown/HTML 导出，验证本机 API 缺失时本地流程仍可用

## 3. Verification and delivery

- [x] 3.1 增加桌面 GUI 单元/offscreen smoke 测试并验证 PySide6 安装
- [x] 3.2 运行 pytest、compileall、真实 CalculiX、报告和 Git 敏感信息扫描
- [x] 3.3 更新 README 启动方式，提交并推送 GitHub，确认不含本机 URL/Key
