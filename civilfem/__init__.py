"""CivilFEM Agent 首版公共接口。"""

# 导出统一模型类型，方便上层直接导入。
from .schemas import CanonicalModel, Component, Section, ValidationReport

# 声明包版本，便于运行清单记录。
__version__ = "0.1.0"

# 声明公开名称，限制通配符导入范围。
__all__ = ["CanonicalModel", "Component", "Section", "ValidationReport", "__version__"]
