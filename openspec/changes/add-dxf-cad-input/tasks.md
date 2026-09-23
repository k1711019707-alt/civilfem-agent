# Tasks

## 1. DXF 解析

- [x] 1.1 编写 DXF 几何摘要回归测试，验证实体、图层、边界和线段长度
- [x] 1.2 扩展 DXF 检查器并运行 DXF 测试，验证损坏文件和超大输入拒绝

## 2. GUI CAD 流程

- [x] 2.1 编写 DXF 上传与人工确认参数测试，验证未确认参数不能进入求解
- [x] 2.2 增加 GUI DXF 上传、摘要显示和 DWG 转 DXF 提示
- [x] 2.3 增加截面、材料、长度、荷载和边界表单，并生成 Canonical Model
- [x] 2.4 复用现有网格、OpenSeesPy/CalculiX、状态和报告流程，验证 CAD 到报告闭环

## 3. 依赖与文档

- [x] 3.1 更新 README 的 DXF 输入、单位确认和启动说明
- [x] 3.2 运行全部 pytest、GUI smoke test、OpenSpec 严格校验和 Git diff 检查
