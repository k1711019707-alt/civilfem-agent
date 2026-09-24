# Spec Delta

## Purpose

为结构模型提供可追溯的三维实体有限元静力分析结果，使用真实 CalculiX 求解输出位移、应力和 von Mises 应力，并生成可视化附件。

## ADDED Requirements

### Requirement: 三维 FEM 求解

系统 SHALL 将有效结构模型和 Gmsh 三维网格转换为 CalculiX 输入文件，并调用已配置的 CalculiX 求解器执行静力分析。

#### Scenario: 求解器可用且分析完成
- **WHEN** 模型、网格、材料、边界条件和载荷有效，且 CalculiX 可执行文件可用
- **THEN** 系统返回 `completed`，保存 `.inp`、求解日志和 CalculiX 结果文件

#### Scenario: 求解器不可用
- **WHEN** 未发现 `CIVILFEM_CALCULIX` 或 PATH 中的 `ccx`/`calculix`
- **THEN** 系统返回 `not_implemented`，不伪造 `completed` 或应力结果

### Requirement: 应力结果提取

系统 SHALL 从真实 CalculiX 结果中提取节点位移、应力分量和 von Mises 应力，并返回最大值及对应节点或单元标识。

#### Scenario: 结果文件有效
- **WHEN** CalculiX 生成可解析的 `.frd` 结果
- **THEN** 运行清单保存结果摘要，包含单位、位移最大值、von Mises 最大值和结果文件路径

#### Scenario: 结果文件缺失或无法解析
- **WHEN** 求解结束但结果文件不存在或格式不受支持
- **THEN** 系统返回 `failed`，错误信息说明结果解析失败原因

### Requirement: 应力云图

系统 SHALL 基于三维网格和 von Mises 应力结果生成 PNG 应力云图，并将图片路径写入运行结果。

#### Scenario: 云图生成成功
- **WHEN** 网格和应力场均可用
- **THEN** 系统生成带颜色标尺、单位和网格轮廓的 PNG 文件

#### Scenario: 可视化依赖缺失
- **WHEN** PyVista 或结果转换依赖不可用
- **THEN** 系统保留数值结果并返回明确的 `not_implemented` 云图状态
