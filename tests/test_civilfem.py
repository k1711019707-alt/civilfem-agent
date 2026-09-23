"""CivilFEM 首版基础测试。"""

# 导入测试工具。
import pytest

# 导入模型、插件和验证服务。
from civilfem.schemas import CanonicalModel, ModelStatus, Section
from civilfem.plugins import SteelBeamPlugin
from civilfem.workflow import validate_structural_model


def sample_model(**overrides):
    """构造最小钢梁模型。"""
    data = {"id": "B-1", "type": "steel_beam", "section": {"h": 300, "b": 300, "tw": 10, "tf": 15}, "steel": "Q355", "Mx": 100, "Lx": 6000, "Ly": 6000}
    data.update(overrides)
    return CanonicalModel(project_id="test", components=[data])


def test_valid_model():
    """合法模型通过插件验证。"""
    report = validate_structural_model(sample_model())
    assert report.status is ModelStatus.VALID


def test_missing_steel_pending():
    """缺少钢材牌号必须暂停确认。"""
    report = validate_structural_model(sample_model(steel=None))
    assert report.status is ModelStatus.PENDING_CONFIRMATION
    assert "B-1: steel" in report.issues


def test_invalid_section_rejected():
    """翼缘过厚必须被 Pydantic 拒绝。"""
    with pytest.raises(ValueError):
        Section(h=20, b=100, tw=5, tf=10)


def test_steel_check_reused():
    """插件必须返回既有核心的结构化结果。"""
    result = SteelBeamPlugin().check(sample_model().components[0])
    assert result["member_id"] == "B-1"
    assert "checks" in result
