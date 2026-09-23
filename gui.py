"""CivilFEM 中文 Streamlit 单页 GUI。"""

# 延迟导入 Streamlit，使核心流程可以在未安装 GUI 依赖时测试。
from __future__ import annotations

# 导入 JSON、路径和类型工具。
import json
import copy
from pathlib import Path
from typing import Any

# 复用项目已有的受控 API，不直接执行用户命令。
from civilfem.mcp_api import (
    build_mesh,
    generate_report,
    get_result_summary,
    get_simulation_status,
    submit_simulation,
)
from civilfem.runtime import capabilities
from civilfem.security import configured_project_root
from civilfem.visualization import render_mesh
from civilfem.workflow import extract_structural_model, inspect_input, validate_structural_model


def parse_json_upload(raw: bytes) -> tuple[dict | list[dict] | None, str | None]:
    """解析上传 JSON，并返回可供 Canonical Model 使用的数据。"""
    # 拒绝空文件，避免后续流程产生含糊错误。
    if not raw:
        return None, "JSON 文件为空"
    # 将 UTF-8 字节解析为 Python 对象。
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        return None, f"JSON 解析失败: {error}"
    # 仅允许项目支持的对象或对象数组结构。
    if not isinstance(data, (dict, list)) or (isinstance(data, list) and not all(isinstance(item, dict) for item in data)):
        return None, "JSON 顶层必须是对象或对象数组"
    # 提前构造 Canonical Model，确保非法输入不会进入网格或求解。
    try:
        extract_structural_model(data)
    except Exception as error:
        return None, f"模型构造失败: {error}"
    # 返回经过结构检查的数据。
    return data, None


def save_upload(raw: bytes, filename: str, project_root: str | Path = ".") -> Path:
    """将上传文件安全保存到项目根下的临时输入目录。"""
    # 解析并创建配置项目根，阻止写入任意外部路径。
    root = configured_project_root(project_root)
    # 仅保留文件名部分，阻止路径穿越。
    safe_name = Path(filename).name or "upload.json"
    # 将 GUI 上传统一写入受控目录。
    target_dir = root / ".civilfem" / "uploads"
    target_dir.mkdir(parents=True, exist_ok=True)
    # 写入字节内容并返回绝对路径。
    target = (target_dir / safe_name).resolve()
    target.relative_to(root)
    target.write_bytes(raw)
    return target


def inspect_uploaded_model(path: str | Path, project_root: str | Path = ".") -> dict[str, Any]:
    """检查上传 JSON、提取模型并返回验证结果。"""
    # 先执行现有输入检查，保留哈希和记录统计。
    inspection = inspect_input(str(path), str(project_root))
    # 输入检查失败时立即停止后续操作。
    if inspection.get("status") != "inspected":
        return {"status": "failed", "inspection": inspection, "validation": None, "model": None, "error": "输入检查未通过"}
    # 读取已保存的 UTF-8 JSON 内容。
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        model = extract_structural_model(data)
        report = validate_structural_model(model)
    except Exception as error:
        return {"status": "failed", "inspection": inspection, "validation": None, "model": None, "error": f"模型验证失败: {error}"}
    # 将 Pydantic 对象转成后端可复用的 JSON 字典。
    model_data = model.model_dump(mode="json")
    validation = report.model_dump(mode="json")
    # 只允许 valid 模型进入网格和求解步骤。
    status = "valid" if validation.get("status") == "valid" else "pending_confirmation"
    return {"status": status, "inspection": inspection, "validation": validation, "model": model_data, "error": None}


def build_cad_model(geometry: dict[str, Any], parameters: dict[str, Any]) -> dict[str, Any]:
    """使用用户确认参数把 CAD 几何摘要转换为 Canonical Model。"""
    # 读取项目标识和用户确认的构件参数。
    project_id = str(geometry.get("project_id") or "cad-project")
    section = {key: parameters.get(key) for key in ("h", "b", "tw", "tf")}
    steel = parameters.get("steel")
    length = float(parameters.get("length") or geometry.get("length") or 0)
    # 缺少关键工程参数时明确要求人工确认。
    if any(value is None for value in section.values()) or not steel or length <= 0:
        return {"status": "pending_confirmation", "error": "CAD 输入必须确认 h、b、tw、tf、steel 和 length"}
    # 组织与 JSON 输入一致的严格模型数据。
    record = {"project_id": project_id, "id": str(parameters.get("id") or "CAD-B-1"), "type": "steel_beam", "section": section, "steel": str(steel), "length": length, "Lx": float(parameters.get("Lx") or length), "Ly": float(parameters.get("Ly") or length), "N": float(parameters.get("N") or 0), "Mx": float(parameters.get("Mx") or 0), "My": float(parameters.get("My") or 0), "V": float(parameters.get("V") or 0)}
    # 使用统一工作流验证，不复制 Pydantic 规则。
    try:
        model = extract_structural_model(record)
        validation = validate_structural_model(model).model_dump(mode="json")
    except Exception as error:
        return {"status": "invalid", "error": f"CAD 参数无效: {error}"}
    # 返回真实验证状态和模型。
    return {"status": "valid" if validation.get("status") == "valid" else "pending_confirmation", "validation": validation, "model": model.model_dump(mode="json"), "error": None}


def backend_available(backend: str) -> bool:
    """返回指定后端当前是否可用。"""
    # 仅查询既有能力探测结果，不改变后端状态。
    return bool(capabilities().get(backend, False))


def create_mesh(model: dict[str, Any], project_root: str | Path, mesh_size: float) -> dict[str, Any]:
    """生成 Gmsh 网格并尝试生成 PNG 预览。"""
    # 调用现有 Gmsh 适配器，避免 GUI 重复实现网格算法。
    result = build_mesh(model, str(project_root), mesh_size)
    # 只有网格完成且文件存在时才生成预览。
    if result.get("status") == "completed" and result.get("mesh"):
        result["preview"] = render_mesh(result["mesh"])
    # 返回真实状态，禁止在后端失败时伪造完成。
    return result


def submit_backend(model: dict[str, Any], project_root: str | Path, backend: str, solver_input: str | None = None) -> dict[str, Any]:
    """通过既有受控 API 提交 OpenSeesPy 或 CalculiX。"""
    # 拒绝未知后端，避免 GUI 绕过能力清单。
    if backend not in {"openseespy", "calculix"}:
        return {"status": "failed", "error": f"不支持的后端: {backend}"}
    # 提交时保留后端真实返回的 queued、completed、failed 或 not_implemented。
    return submit_simulation(model, str(project_root), backend=backend, solver_input=solver_input)


def build_reports(run_id: str, project_root: str | Path) -> dict[str, Any]:
    """为一次运行生成 Markdown 和 HTML 报告。"""
    # 分别调用既有报告 API，返回各自的真实文件路径。
    return {fmt: generate_report(run_id, str(project_root), fmt=fmt) for fmt in ("markdown", "html")}


def _show_json(st: Any, title: str, value: Any) -> None:
    """在 GUI 中统一显示结构化结果。"""
    # 使用 Streamlit 原生 JSON 查看器，便于工程人员核查字段。
    st.subheader(title)
    st.json(value)


def main() -> None:
    """渲染中文 Streamlit 页面并串联完整流程。"""
    # 延迟导入可选 GUI 依赖。
    import streamlit as st

    # 初始化页面标题和布局。
    st.set_page_config(page_title="CivilFEM Agent", page_icon="🏗️", layout="wide")
    st.title("CivilFEM Agent：多构件有限元工程控制台")
    st.caption("输入检查 → 模型验证 → Gmsh 网格 → 求解 → 结果与报告")
    # 读取项目根配置并显示后端能力。
    project_root = configured_project_root()
    st.info(f"项目根目录：{project_root}")
    st.subheader("后端能力")
    st.json(capabilities())
    # 接收 JSON 或 DXF 图纸并保存到受控目录。
    uploaded = st.file_uploader("上传结构 JSON 或 DXF 图纸", type=["json", "dxf"])
    if uploaded is None:
        st.warning("请先上传 JSON 输入文件。")
        return
    # 缓存上传文件，避免页面刷新时丢失路径。
    raw = uploaded.getvalue()
    try:
        input_path = save_upload(raw, uploaded.name, project_root)
    except Exception as error:
        st.error(f"上传文件保存失败：{error}")
        return
    # 执行输入检查；DXF 先只读摘要，避免从图纸静默猜工程参数。
    if input_path.suffix.lower() == ".dxf":
        cad_inspection = inspect_input(str(input_path), str(project_root))
        _show_json(st, "CAD 图纸检查", cad_inspection)
        if cad_inspection.get("status") != "inspected":
            st.error(cad_inspection.get("issues") or "DXF 检查失败。")
            return
        st.warning("DXF 只提供几何证据；截面、材料、荷载、长度和边界必须人工确认。DWG 请先另存为 DXF。")
        bounds = cad_inspection.get("bounds") or [0.0, 0.0, 0.0, 0.0]
        default_length = max(float(cad_inspection.get("line_length") or 0), float(bounds[2]) - float(bounds[0]))
        with st.form("cad_parameters", border=True):
            st.subheader("确认工程参数")
            cad_id = st.text_input("构件编号", value="CAD-B-1")
            col1, col2 = st.columns(2)
            h = col1.number_input("截面高度 h（mm）", min_value=0.1, value=300.0)
            b = col2.number_input("翼缘宽度 b（mm）", min_value=0.1, value=300.0)
            tw = col1.number_input("腹板厚度 tw（mm）", min_value=0.1, value=10.0)
            tf = col2.number_input("翼缘厚度 tf（mm）", min_value=0.1, value=15.0)
            steel = st.text_input("钢材牌号", value="Q355")
            length = st.number_input("构件长度（mm，需确认）", min_value=0.1, value=max(default_length, 6000.0))
            m_x = st.number_input("弯矩 Mx（kN·m）", value=0.0)
            shear = st.number_input("剪力 V（kN）", value=0.0)
            confirmed = st.form_submit_button("确认 CAD 参数并建立模型", type="primary")
        if not confirmed:
            return
        cad_model = build_cad_model({"project_id": input_path.stem, "length": length}, {"id": cad_id, "h": h, "b": b, "tw": tw, "tf": tf, "steel": steel, "length": length, "Mx": m_x, "V": shear})
        inspection = cad_model
    else:
        # JSON 直接执行输入检查、模型提取和验证。
        inspection = inspect_uploaded_model(input_path, project_root)
    # 保存检查结果并显示验证信息。
    st.session_state["inspection"] = inspection
    _show_json(st, "输入与模型验证", {key: value for key, value in inspection.items() if key != "model"})
    # 非 valid 模型不得继续执行高成本后端。
    if inspection.get("status") != "valid":
        st.error(inspection.get("error") or "模型未通过验证，已停止后续流程。")
        return
    model = inspection["model"]
    # 网格参数和生成按钮。
    st.subheader("Gmsh 网格")
    mesh_size = st.number_input("网格尺寸（mm）", min_value=0.1, value=100.0, step=10.0)
    if st.button("生成网格", type="primary"):
        with st.spinner("正在生成网格和 PNG 预览…"):
            mesh = create_mesh(model, project_root, mesh_size)
        st.session_state["mesh"] = mesh
    mesh = st.session_state.get("mesh")
    if mesh:
        _show_json(st, "网格结果", {key: value for key, value in mesh.items() if key != "preview"})
        if mesh.get("preview", {}).get("status") == "completed":
            st.image(mesh["preview"]["image"], caption="网格 PNG 预览")
        elif mesh.get("status") != "completed":
            st.error(mesh.get("error") or "网格生成失败")
    # 选择求解后端并接收 CalculiX 输入文件。
    st.subheader("求解")
    backend = st.selectbox("求解后端", ("openseespy", "calculix"), format_func=lambda value: "OpenSeesPy" if value == "openseespy" else "CalculiX")
    solver_model = model
    if backend == "openseespy":
        boundary = st.selectbox("边界条件", ("cantilever",), help="当前 OpenSeesPy 适配器要求显式边界条件。")
        elastic_modulus = st.number_input("弹性模量（MPa）", min_value=1.0, value=206000.0, step=1000.0)
        solver_model = copy.deepcopy(model)
        solver_model["analysis"] = {"boundary": boundary, "elastic_modulus": elastic_modulus}
    solver_file = st.file_uploader("CalculiX 输入文件（仅 CalculiX 需要）", type=["inp"], key="solver_input") if backend == "calculix" else None
    if not backend_available(backend):
        st.warning(f"后端不可用：{backend}，请先安装并配置依赖。")
    if st.button("提交求解"):
        solver_path = None
        if backend == "calculix":
            if solver_file is None:
                st.error("CalculiX 求解必须上传 .inp 输入文件。")
                return
            solver_path = str(save_upload(solver_file.getvalue(), solver_file.name, project_root))
        with st.spinner("正在提交求解…"):
            run = submit_backend(solver_model, project_root, backend, solver_path)
        st.session_state["run"] = run
    # 展示运行状态、结果摘要和可下载报告。
    run = st.session_state.get("run")
    if not run:
        return
    _show_json(st, "运行状态", run)
    if run.get("status") in {"failed", "not_implemented", "pending_confirmation"}:
        st.error(run.get("error") or "求解未完成")
        return
    run_id = run.get("run_id")
    if not run_id:
        return
    _show_json(st, "状态查询", get_simulation_status(run_id, str(project_root)))
    _show_json(st, "结果摘要", get_result_summary(run_id, str(project_root)))
    reports = build_reports(run_id, project_root)
    for fmt, report in reports.items():
        report_path = report.get("report")
        if report.get("status") and report_path and Path(report_path).is_file():
            st.download_button(f"下载 {fmt.upper()} 报告", Path(report_path).read_bytes(), file_name=Path(report_path).name, mime="text/markdown" if fmt == "markdown" else "text/html")


if __name__ == "__main__":
    main()
