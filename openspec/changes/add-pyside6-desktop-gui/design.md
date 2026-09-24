# Design

## Context

项目已有稳定的 `civilfem` 后端和 Streamlit GUI，但用户要求本地窗口和视觉稿级布局。当前环境没有 PySide6，需要把它作为可选依赖安装；核心模块不能依赖 Qt，测试环境也应能在无桌面显示器时导入模块。

## Goals / Non-Goals

**Goals:**

- 新增 PySide6 桌面应用，固定尺寸比例复刻视觉稿。
- 通过 Qt signals/worker 将网格、CalculiX、报告任务放到后台线程。
- 用 `QMainWindow`、自绘 QSS 和 `QLabel/QPixmap` 呈现云图、预览和 KPI。
- 保留现有 Streamlit 文件作为兼容入口，但 README 将桌面入口设为主入口。

**Non-Goals:**

- 不重写 Gmsh、CalculiX、FRD 解析或报告算法。
- 不在本次实现任意 CAD 自动转有限元实体。
- 不把 API Key 复制到项目配置或 Qt 日志。

## Decisions

1. **PySide6 而非 Tkinter**：QSS、布局、线程和高 DPI 支持更适合一比一视觉复刻；Tkinter 作为无依赖方案会牺牲控件样式。
2. **单文件入口 + 后端适配函数**：先将界面集中在 `desktop_gui.py`，避免把现有业务拆散；后台任务通过 QObject worker 和 signal 更新。
3. **图像优先**：直接加载 PyVista/Matplotlib 生成的 PNG，并在 Qt 端补充深色卡片、色标和状态；不引入 OpenGL 三维交互依赖，保证 CalculiX 结果链稳定。
4. **线程安全边界**：worker 只调用纯后端函数并返回字典，所有 QWidget 更新在主线程完成；上传文件复制到 `.civilfem/uploads` 后才交给后端。
5. **无显示器验证**：测试只导入类、检查 QSS 和用 `QT_QPA_PLATFORM=offscreen` 创建窗口；真实 GUI 手工 smoke 在本机完成。

## Risks / Trade-offs

- [PySide6 未安装] → `python -m pip install -e ".[desktop]"`；无 Qt 时核心测试仍可运行并给出明确提示。
- [后台线程错误] → 捕获异常并通过 error signal 显示脱敏摘要，窗口保持可操作。
- [视觉稿与不同 DPI 有差异] → 设置最小窗口尺寸、字体层级和高 DPI 属性，避免使用绝对坐标堆叠全部控件。

## Migration Plan

1. 增加 desktop 依赖和桌面入口。
2. 运行 offscreen smoke、完整 pytest、真实 CalculiX 和报告流程。
3. 更新 README 启动命令；保留 `streamlit run gui.py` 兼容方式。
4. 只提交源码、测试、OpenSpec 和依赖声明，不提交本机配置或运行产物。
