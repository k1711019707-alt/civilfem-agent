"""确定性输入解析和模型验证服务。"""

# 导入类型和 JSON 工具。
from __future__ import annotations
import json
from pathlib import Path

# 导入统一模型和插件注册表。
from .schemas import CanonicalModel, ModelStatus, ValidationReport
from .plugins import PLUGINS
from .inputs import inspect_asset


def inspect_input(path: str, project_root: str | None = None) -> dict:
    """只读检查 JSON、IFC 或 DXF 输入文件。"""
    # 委托给统一输入资产检查器。
    return inspect_asset(path, project_root)


def extract_structural_model(data: dict | list[dict]) -> CanonicalModel:
    """从结构化 JSON 构造 Canonical Model。"""
    # 统一单对象和数组输入。
    records = data if isinstance(data, list) else [data]
    # 读取项目标识，缺省值仅用于演示。
    project_id = records[0].get("project_id", "demo") if records else "demo"
    # 优先读取包装构件，否则从扁平记录中剥离项目级元数据。
    components = [record["component"] if "component" in record else {key: value for key, value in record.items() if key != "project_id"} for record in records]
    # 创建版本化模型。
    return CanonicalModel(project_id=project_id, components=components)


def validate_structural_model(model: CanonicalModel) -> ValidationReport:
    """验证模型状态和插件参数。"""
    # 收集所有构件问题。
    issues: list[str] = []
    # 逐构件选择确定性插件验证。
    for component in model.components:
        plugin = PLUGINS.get(component.type)
        if plugin is None:
            issues.append(f"{component.id}: 未注册插件")
            continue
        report = plugin.validate(component)
        issues.extend(f"{component.id}: {issue}" for issue in report.issues)
    # 缺失参数优先返回待确认。
    status = ModelStatus.PENDING_CONFIRMATION if issues else ModelStatus.VALID
    # 返回模型级报告。
    return ValidationReport(status=status, issues=issues, object_id=model.project_id)
