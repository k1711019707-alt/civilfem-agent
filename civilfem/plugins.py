"""构件插件协议和钢构件适配器。"""

# 启用前向类型注解。
from __future__ import annotations

# 导入协议、类型和路径工具。
from pathlib import Path
from typing import Any, Protocol
import sys

# 将既有钢校核原型目录加入导入路径，保持原代码不改。
ROOT = Path(__file__).resolve().parents[1]
LEGACY = ROOT / "steel-check-mcp"
if str(LEGACY) not in sys.path:
    sys.path.insert(0, str(LEGACY))

# 导入确定性钢构件计算核心。
from steelcheck import IH, Member, check_member

# 导入统一模型类型。
from .schemas import Component, ValidationReport, ModelStatus


class ComponentPlugin(Protocol):
    """所有构件插件必须实现的最小协议。"""

    # 声明插件类型名。
    type_name: str

    # 验证构件参数。
    def validate(self, component: Component) -> ValidationReport: ...

    # 构建几何资产，首版返回描述性字典。
    def build_geometry(self, component: Component) -> dict[str, Any]: ...

    # 生成网格资产，未接入 Gmsh 时返回未实现状态。
    def mesh(self, geometry: dict[str, Any]) -> dict[str, Any]: ...

    # 导出求解器输入，未接入 CalculiX 时返回未实现状态。
    def export_solver(self, component: Component) -> dict[str, Any]: ...

    # 提取统一结果。
    def extract_results(self, raw_result: dict[str, Any]) -> dict[str, Any]: ...


class SteelPlugin:
    """复用既有 `steelcheck.py` 的钢构件插件基类。"""

    # 由子类覆盖具体构件类型。
    type_name = "steel"

    # 验证钢材、截面和长度参数。
    def validate(self, component: Component) -> ValidationReport:
        # 收集可行动问题。
        issues: list[str] = []
        # 材料牌号是进入校核的关键参数。
        if not component.steel:
            issues.append("steel")
        # 受压构件需要计算长度。
        if component.N and (component.Lx <= 0 or component.Ly <= 0):
            issues.append("Lx/Ly")
        # 缺参数进入人工确认状态。
        if issues:
            return ValidationReport(status=ModelStatus.PENDING_CONFIRMATION, issues=issues, object_id=component.id)
        # 已知牌号交给既有核心检查。
        try:
            if component.steel not in {"Q235", "Q355", "Q390", "Q420"}:
                raise ValueError(f"未知钢材牌号 {component.steel}")
        except ValueError as error:
            return ValidationReport(status=ModelStatus.INVALID, issues=[str(error)], object_id=component.id)
        # 所有基础检查通过。
        return ValidationReport(status=ModelStatus.VALID, object_id=component.id)

    # 返回几何描述，后续由 FreeCAD/Gmsh 适配器消费。
    def build_geometry(self, component: Component) -> dict[str, Any]:
        return {"kind": "h_section_prism", "section": component.section.model_dump(), "source": "deterministic"}

    # 明确声明首版尚未接入 Gmsh。
    def mesh(self, geometry: dict[str, Any]) -> dict[str, Any]:
        return {"status": "not_implemented", "reason": "Gmsh 网格适配器尚未接入"}

    # 明确声明首版尚未接入 CalculiX。
    def export_solver(self, component: Component) -> dict[str, Any]:
        return {"status": "not_implemented", "reason": "CalculiX 求解器适配器尚未接入"}

    # 保持结果字段透明，不修改原始求解结果。
    def extract_results(self, raw_result: dict[str, Any]) -> dict[str, Any]:
        return {"status": "completed", "result": raw_result}

    # 调用既有钢构件校核核心。
    def check(self, component: Component) -> dict[str, Any]:
        # 先验证关键参数，防止核心收到不完整输入。
        report = self.validate(component)
        # 不合法或待确认时直接返回结构化状态。
        if report.status is not ModelStatus.VALID:
            return report.model_dump()
        # 转换为旧核心的截面对象。
        section = IH(**component.section.model_dump())
        # 转换为旧核心的构件对象。
        member = Member(member_id=component.id, section=section, steel=component.steel or "", N=component.N, Mx=component.Mx, My=component.My, V=component.V, Lx=component.Lx, Ly=component.Ly)
        # 返回确定性校核结果。
        return check_member(member)


class SteelBeamPlugin(SteelPlugin):
    """钢梁插件。"""

    # 声明钢梁类型名。
    type_name = "steel_beam"


class SteelColumnPlugin(SteelPlugin):
    """钢柱插件。"""

    # 声明钢柱类型名。
    type_name = "steel_column"


# 注册首版插件，避免动态导入复杂度。
PLUGINS: dict[str, SteelPlugin] = {"steel_beam": SteelBeamPlugin(), "steel_column": SteelColumnPlugin()}
