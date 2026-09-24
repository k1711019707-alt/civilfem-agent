"""GUI 纯流程回归测试。"""

import json

import pytest

from gui import inspect_uploaded_model, parse_json_upload, reuse_cad_confirmation, save_upload


@pytest.fixture(autouse=True)
def configured_root(tmp_path, monkeypatch):
    """每项 GUI 测试使用独立项目根。"""
    monkeypatch.setenv("CIVILFEM_PROJECT_ROOT", str(tmp_path))


def valid_record() -> dict:
    """返回最小合法钢构件输入。"""
    return {
        "project_id": "gui-test",
        "id": "B-1",
        "type": "steel_beam",
        "section": {"h": 300, "b": 300, "tw": 10, "tf": 15},
        "steel": "Q355",
        "Lx": 6000,
        "Ly": 6000,
    }


def test_parse_and_inspect_valid_upload(tmp_path):
    """合法 JSON 必须可解析、检查并验证模型。"""
    raw = json.dumps(valid_record()).encode("utf-8")
    data, error = parse_json_upload(raw)
    assert error is None
    assert data["project_id"] == "gui-test"
    path = save_upload(raw, "model.json", tmp_path)
    result = inspect_uploaded_model(path, tmp_path)
    assert result["inspection"]["status"] == "inspected"
    assert result["validation"]["status"] == "valid"


def test_invalid_upload_stops_before_validation(tmp_path):
    """无法构成 Canonical Model 的输入必须返回错误而非伪造成功。"""
    raw = b'{"project_id":"bad","type":"unknown"}'
    data, error = parse_json_upload(raw)
    assert data is None
    assert error
    path = save_upload(raw, "bad.json", tmp_path)
    result = inspect_uploaded_model(path, tmp_path)
    assert result["status"] == "failed"
    assert result["validation"] is None


def test_missing_backend_never_reports_completed(monkeypatch):
    """后端缺失时 GUI 能力状态不能伪造成完成。"""
    monkeypatch.setattr("gui.capabilities", lambda: {"gmsh": False, "calculix": False, "openseespy": False})
    from gui import backend_available

    assert backend_available("calculix") is False


def test_reuse_cad_confirmation_after_form_submit():
    """同一 DXF 在后续按钮 rerun 中必须复用已确认模型。"""
    confirmed = {"status": "valid", "model": {"project_id": "cad"}}
    assert reuse_cad_confirmation("same", "same", confirmed) == confirmed
    assert reuse_cad_confirmation("old", "same", confirmed) is None
