# Design

## 总体结构

`civilfem` 采用 Pydantic 数据模型、插件协议和服务函数三层结构。现有 `steel-check-mcp/steelcheck.py` 作为只读确定性核心，通过适配器转换为统一结果。

## 边界

- 首版只实现结构化 JSON 输入与钢梁/钢柱。
- IFC、DXF、STEP、FreeCAD、Gmsh、CalculiX、OpenSeesPy、PyVista 只保留接口状态，不返回伪造结果。
- MCP 服务优先使用官方 Python SDK；SDK缺失时模块仍可被单元测试导入。
- 所有文件路径只允许位于配置项目根目录；本首版工具接口不接收任意 shell 命令。

## 验证

- Pydantic 验证正值尺寸、枚举字段和模型版本。
- 插件验证材料、边界、荷载和截面完整性。
- pytest 覆盖合法模型、缺失参数、非法尺寸、钢梁校核和未实现工具状态。
