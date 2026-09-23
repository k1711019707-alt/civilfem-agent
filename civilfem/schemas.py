"""定义版本化 Canonical Structural Model。"""

# 启用前向类型注解，减少运行时依赖。
from __future__ import annotations

# 导入枚举、类型和 Pydantic 校验工具。
from enum import Enum
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ModelStatus(str, Enum):
    """统一流程状态。"""

    # 模型等待用户补充关键参数。
    PENDING_CONFIRMATION = "pending_confirmation"
    # 模型已经通过基础验证。
    VALID = "valid"
    # 模型存在错误，禁止进入求解。
    INVALID = "invalid"


class Evidence(BaseModel):
    """记录参数来源和追溯信息。"""

    # 禁止额外字段，避免来源信息被静默吞掉。
    model_config = ConfigDict(extra="forbid")
    # 来源类型，例如 json、ifc 或 user。
    source: str
    # 来源中的实体标识，可为空。
    entity_id: str | None = None
    # 来源文本或文件引用。
    reference: str | None = None


class Section(BaseModel):
    """钢构件 H 型截面，单位 mm。"""

    # 禁止额外字段，保持模型契约稳定。
    model_config = ConfigDict(extra="forbid")
    # 截面总高。
    h: float = Field(gt=0)
    # 翼缘宽度。
    b: float = Field(gt=0)
    # 腹板厚度。
    tw: float = Field(gt=0)
    # 翼缘厚度。
    tf: float = Field(gt=0)

    # 检查腹板高度必须为正。
    @field_validator("tf")
    @classmethod
    def check_depth(cls, value: float, info: Any) -> float:
        # 读取已解析的总高，阻止几何重叠。
        height = info.data.get("h")
        # 当总高已知且翼缘过厚时拒绝输入。
        if height is not None and height <= 2 * value:
            raise ValueError("h 必须大于 2*tf")
        # 返回通过校验的翼缘厚度。
        return value


class Material(BaseModel):
    """材料参数和牌号。"""

    # 禁止未知材料字段。
    model_config = ConfigDict(extra="forbid")
    # 材料标识。
    id: str
    # 材料角色，例如 steel。
    role: str = "steel"


class Component(BaseModel):
    """统一结构构件。"""

    # 禁止未知构件字段。
    model_config = ConfigDict(extra="forbid")
    # 构件唯一标识。
    id: str
    # 首版支持 steel_beam 和 steel_column。
    type: Literal["steel_beam", "steel_column"]
    # H 型截面参数。
    section: Section
    # 材料牌号，默认值只用于结构化输入，不代表工程确认。
    steel: str | None = None
    # 轴力，单位 kN。
    N: float = 0.0
    # x 轴弯矩，单位 kN·m。
    Mx: float = 0.0
    # y 轴弯矩，单位 kN·m。
    My: float = 0.0
    # 剪力，单位 kN。
    V: float = 0.0
    # x 方向计算长度，单位 mm。
    Lx: float = 0.0
    # y 方向计算长度，单位 mm。
    Ly: float = 0.0
    # 来源证据列表。
    evidence: list[Evidence] = Field(default_factory=list)


class CanonicalModel(BaseModel):
    """项目级 Canonical Structural Model。"""

    # 禁止未知顶层字段。
    model_config = ConfigDict(extra="forbid")
    # 固定 schema 版本。
    schema_version: Literal["0.1"] = "0.1"
    # 项目唯一标识。
    project_id: str
    # 首版统一单位约定。
    units: Literal["N-mm-MPa"] = "N-mm-MPa"
    # 结构构件列表。
    components: list[Component] = Field(min_length=1)
    # 模型状态由验证器更新。
    status: ModelStatus = ModelStatus.PENDING_CONFIRMATION
    # 缺失或待确认字段。
    pending_confirmation: list[str] = Field(default_factory=list)


class ValidationReport(BaseModel):
    """模型或插件验证结果。"""

    # 验证状态。
    status: ModelStatus
    # 错误、警告和待确认信息。
    issues: list[str] = Field(default_factory=list)
    # 通过验证的对象标识。
    object_id: str | None = None

