# Proposal

## Why

当前 GUI 只能接收 JSON，工程人员仍需手工把 CAD 图纸转换成结构输入。开源优先的可行入口是 DXF；DWG 需要专有 SDK，不在首版直接解析。

## What Changes

- 支持 GUI 上传 DXF 图纸并进行只读检查。
- 统计图层、实体数量、几何边界和可识别的线段长度。
- 将 CAD 几何摘要展示给用户，并要求用户确认截面、材料、荷载和边界等工程参数。
- 根据用户确认参数生成 Canonical Model，再复用现有网格、求解和报告流程。
- 明确提示 DWG 需另存为 DXF，不从图纸静默猜测关键工程参数。
- 增加 DXF 解析测试、GUI 流程测试和使用文档。

## Capabilities

### New Capabilities

- `cad-dxf-input`: DXF 图纸检查、几何摘要和人工确认后建模。

### Modified Capabilities

无。

## Impact

- 修改 `civilfem/inputs.py`、`gui.py`、`pyproject.toml`、`README.md`。
- 新增 DXF 解析和 GUI 回归测试。
- 继续使用 `ezdxf`，不新增闭源 CAD SDK，不改变现有 API 签名。

