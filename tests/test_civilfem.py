"""CivilFEM 首版基础测试。"""

# 导入测试工具。
import pytest
import json
import zipfile
from pathlib import Path

# 导入模型、插件和验证服务。
from civilfem.schemas import CanonicalModel, ModelStatus, Section
from civilfem.plugins import SteelBeamPlugin
from civilfem.workflow import extract_structural_model, validate_structural_model
from civilfem.inputs import inspect_asset, allowed_path
from civilfem.runtime import create_run, load_run
from civilfem.reports import generate_report
from civilfem.mcp_api import build_mesh, submit_simulation
from civilfem.visualization import render_mesh


@pytest.fixture(autouse=True)
def configured_root(tmp_path, monkeypatch):
    """每项测试使用独立项目根目录。"""
    monkeypatch.setenv("CIVILFEM_PROJECT_ROOT", str(tmp_path))


def sample_model(**overrides):
    """构造最小钢梁模型。"""
    data = {"id": "B-1", "type": "steel_beam", "section": {"h": 300, "b": 300, "tw": 10, "tf": 15}, "steel": "Q355", "Mx": 100, "Lx": 6000, "Ly": 6000}
    data.update(overrides)
    return CanonicalModel(project_id="test", components=[data])


def test_valid_model():
    """合法模型通过插件验证。"""
    report = validate_structural_model(sample_model())
    assert report.status is ModelStatus.VALID


def test_example_record_extracts_without_project_metadata():
    """顶层项目字段不得泄漏到严格构件模型。"""
    # 构造与示例文件相同的扁平记录。
    record = {"project_id": "demo", "id": "B-1", "type": "steel_beam", "section": {"h": 300, "b": 300, "tw": 10, "tf": 15}, "steel": "Q355", "Lx": 6000, "Ly": 6000}
    # 提取严格 Canonical Model。
    model = extract_structural_model(record)
    # 验证项目字段和构件字段被正确分离。
    assert model.project_id == "demo"
    assert model.components[0].id == "B-1"


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


def test_json_asset_inspection(tmp_path):
    """输入检查必须返回哈希和记录统计。"""
    path = tmp_path / "model.json"
    path.write_text(json.dumps({"project_id": "p", "id": "B", "type": "steel_beam"}), encoding="utf-8")
    result = inspect_asset(path, tmp_path)
    assert result["status"] == "inspected"
    assert len(result["sha256"]) == 64
    assert result["count"] == 1


def test_unknown_asset_format(tmp_path):
    """未知格式必须返回未实现状态。"""
    path = tmp_path / "model.pdf"
    path.write_text("document", encoding="utf-8")
    result = inspect_asset(path, tmp_path)
    assert result["status"] == "not_implemented"


def test_step_asset_inspection(tmp_path):
    """STEP 检查必须识别 schema 和实体类型。"""
    path = tmp_path / "model.step"
    path.write_text("ISO-10303-21;\nHEADER;FILE_SCHEMA(('AP242'));ENDSEC;\nDATA;\n#1=CARTESIAN_POINT('',(0.,0.,0.));\nENDSEC;\nEND-ISO-10303-21;", encoding="ascii")
    result = inspect_asset(path, tmp_path)
    assert result["status"] == "inspected"
    assert result["count"] == 1
    assert "CARTESIAN_POINT" in result["entity_types"]


def test_fcstd_asset_inspection(tmp_path):
    """FCStd 检查必须读取 Document.xml 对象。"""
    path = tmp_path / "model.FCStd"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("Document.xml", "<Document><Object type='Part::Box'/></Document>")
    result = inspect_asset(path, tmp_path)
    assert result["status"] == "inspected"
    assert result["object_types"] == ["Part::Box"]


def test_path_escape_rejected(tmp_path):
    """项目根外路径必须拒绝。"""
    with pytest.raises(ValueError):
        allowed_path(tmp_path.parent, tmp_path)


def test_configured_root_cannot_be_overridden(tmp_path):
    """调用者不得把项目根切换到配置根之外。"""
    outside = tmp_path.parent / "outside.json"
    outside.write_text("{}", encoding="utf-8")
    result = inspect_asset(outside, outside.parent)
    assert result["status"] == "invalid"
    assert "配置项目根" in result["issues"][0]


def test_invalid_run_id_rejected(tmp_path):
    """状态接口必须拒绝路径型运行标识。"""
    result = load_run("../outside", tmp_path)
    assert result["status"] == "failed"
    assert result["error"] == "非法 run_id"


def test_run_manifest_and_report(tmp_path):
    """运行清单和失败报告必须可读取。"""
    manifest = create_run(tmp_path, "simulation", "abc", "calculix")
    loaded = load_run(manifest["run_id"], tmp_path)
    report = generate_report(manifest["run_id"], tmp_path)
    assert loaded["run_id"] == manifest["run_id"]
    assert report["status"] == "queued"
    assert Path(report["report"]).is_file()
    assert "不替代人工复核" in Path(report["report"]).read_text(encoding="utf-8")


def test_gmsh_builds_h_section_mesh(tmp_path):
    """Gmsh 必须生成非空 H 型钢实体网格。"""
    model = sample_model(length=300).model_dump(mode="json")
    result = build_mesh(model, str(tmp_path), mesh_size=100)
    assert result["status"] == "completed"
    assert result["node_count"] > 0
    assert result["element_count"] > 0
    assert Path(result["mesh"]).is_file()
    image = render_mesh(result["mesh"])
    assert image["status"] == "completed"
    assert Path(image["image"]).is_file()


def test_missing_calculix_is_not_completed(tmp_path):
    """缺少 CalculiX 时不得伪造完成状态。"""
    result = submit_simulation({"project_id": "p"}, str(tmp_path), backend="calculix")
    assert result["status"] != "completed"


def test_calculix_uses_configured_executable_and_replaces_bad_output(tmp_path, monkeypatch):
    """CalculiX 必须使用可信环境配置并容忍不可解码输出。"""
    # 创建由 Python 执行的最小伪求解器脚本。
    script = tmp_path / "model"
    script.write_text("import sys\nsys.stdout.buffer.write(b'\\x81')\n", encoding="utf-8")
    # 创建满足运行接口约定的输入文件。
    solver_input = tmp_path / "model.inp"
    solver_input.write_text("*HEADING\n", encoding="ascii")
    # 将当前 Python 解释器配置为可信求解器可执行文件。
    monkeypatch.setenv("CIVILFEM_CALCULIX", __import__("sys").executable)
    # 提交真实子进程并读取运行清单。
    result = submit_simulation({"project_id": "p"}, str(tmp_path), backend="calculix", solver_input=str(solver_input))
    # 验证求解完成且非法字节被替换而未导致运行器崩溃。
    assert result["status"] == "completed"
    assert result["returncode"] == 0
    assert "�" in result["stdout"]


def test_opensees_cantilever_matches_elastic_solution(tmp_path):
    """OpenSeesPy 悬臂梁位移必须匹配弹性解析解。"""
    model = sample_model(length=300, Mx=0, V=10).model_dump(mode="json")
    model["analysis"] = {"boundary": "cantilever", "elastic_modulus": 206000}
    result = submit_simulation(model, str(tmp_path), backend="openseespy")
    section = model["components"][0]["section"]
    web_height = section["h"] - 2 * section["tf"]
    inertia = (section["b"] * section["h"] ** 3 - (section["b"] - section["tw"]) * web_height ** 3) / 12
    expected = -(10_000 * 300**3) / (3 * 206000 * inertia)
    assert result["status"] == "completed"
    assert result["result"]["displacement"][1] == pytest.approx(expected, rel=1e-6)


def test_opensees_requires_explicit_boundary(tmp_path):
    """OpenSeesPy 不得静默猜测边界条件。"""
    model = sample_model(length=300).model_dump(mode="json")
    result = submit_simulation(model, str(tmp_path), backend="openseespy")
    assert result["status"] == "pending_confirmation"
