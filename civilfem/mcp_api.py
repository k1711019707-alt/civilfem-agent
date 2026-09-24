"""MCP 高层工具函数；SDK层仅负责协议暴露。"""

# 导入类型。
from typing import Any
from pathlib import Path
import shutil

# 导入工作流服务和插件。
from .workflow import inspect_input, extract_structural_model, validate_structural_model
from .runtime import capabilities, submit_run, load_run, create_run, save_run
from .reports import generate_report as generate_run_report
from .meshing import mesh_h_section
from .solvers import solve_opensees_beam
from .fem import build_calculix_input, parse_frd_results, run_calculix
from .visualization import render_stress_cloud


def _result_summary(result: dict[str, Any] | None) -> dict[str, Any] | None:
    if not result:
        return result
    summary = {key: value for key, value in result.items() if key not in {"displacement", "stress", "von_mises"}}
    summary["displacement_node_count"] = len(result.get("displacement") or {})
    summary["stress_node_count"] = len(result.get("stress") or {})
    summary["von_mises_node_count"] = len(result.get("von_mises") or {})
    return summary


def build_mesh(model: dict[str, Any], project_root: str = ".", mesh_size: float = 100.0) -> dict[str, Any]:
    """使用 Gmsh 生成 H 型钢实体网格。"""
    # 读取后端能力，避免伪造网格完成状态。
    available = capabilities()["gmsh"]
    # 返回后端缺失状态。
    if not available:
        return {"status": "not_implemented", "reason": "未安装 Gmsh 或 gmsh Python 模块", "capabilities": capabilities()}
    # 调用确定性 H 型钢几何和网格适配器。
    return mesh_h_section(model, project_root, mesh_size)


def submit_simulation(model: dict[str, Any], project_root: str = ".", backend: str = "calculix", solver_input: str | None = None) -> dict[str, Any]:
    """提交受控求解任务并返回运行清单。"""
    # OpenSeesPy 使用确定性梁单元适配器。
    if backend == "openseespy":
        return solve_opensees_beam(model, project_root)
    # 使用模型哈希或项目标识作为输入追踪值。
    input_hash = model.get("input_hash") or model.get("project_id")
    # 委托运行生命周期管理器。
    return submit_run(project_root, backend, input_hash, solver_input)


def run_fem_analysis(model: dict[str, Any], project_root: str = ".", mesh_path: str | None = None, mesh_size: float = 100.0) -> dict[str, Any]:
    """生成三维 CalculiX 输入、执行求解、解析应力并生成云图。"""
    manifest = create_run(project_root, "simulation", model.get("input_hash") or model.get("project_id"), "calculix-3d")
    try:
        if not mesh_path:
            mesh_result = mesh_h_section(model, project_root, mesh_size)
            mesh_path = mesh_result.get("mesh")
        if not mesh_path:
            raise ValueError("缺少有效 Gmsh 网格")
        import meshio
        mesh = meshio.read(mesh_path)
        mesh_data = {"points": mesh.points.tolist(), "cells": [{"type": block.type, "data": block.data.tolist()} for block in mesh.cells]}
        component = (model.get("components") or [{}])[0]
        input_path = build_calculix_input(
            mesh_data,
            Path(manifest["run_dir"]) / "analysis.inp",
            load=(float(component.get("N", 0)) * 1000, -float(component.get("V", 0)) * 1000, 0.0),
            moment_x=float(component.get("Mx", 0)) * 1_000_000,
        )
        execution = run_calculix(input_path)
        manifest.update(execution)
        if execution.get("status") != "completed":
            return save_run(manifest)
        result = parse_frd_results(execution["frd"])
        component_length = float(component.get("length") or component.get("Lx") or 0.0)
        mesh_size_value = float(mesh_size)
        result["quality"] = {
            "mesh_element_type": "C3D4",
            "mesh_size_mm": mesh_size_value,
            "mesh_size_to_length_ratio": mesh_size_value / component_length if component_length else None,
            "warning": "当前使用线性四面体 C3D4；网格尺寸过大时应力峰值仅作工程辅助参考。" if mesh_size_value / component_length > 0.05 else None,
        }
        rendered_cloud = render_stress_cloud(mesh_path, result["von_mises"])
        cloud = rendered_cloud
        if rendered_cloud.get("status") == "completed":
            report_cloud = Path(manifest["run_dir"]) / "stress_cloud.png"
            shutil.copy2(rendered_cloud["image"], report_cloud)
            cloud = {**rendered_cloud, "image": str(report_cloud)}
        result["stress_cloud"] = cloud
        manifest.update({"status": "completed", "result": result, "mesh": str(mesh_path), "input": str(input_path), "error": None})
    except Exception as error:
        manifest.update({"status": "failed", "error": f"三维 FEM 失败: {error}"})
    return save_run(manifest)


def get_simulation_status(run_id: str, project_root: str = ".") -> dict[str, Any]:
    """查询运行清单状态。"""
    # 从项目根目录读取运行清单。
    return load_run(run_id, project_root)


def get_result_summary(run_id: str, project_root: str = ".") -> dict[str, Any]:
    """读取统一结果摘要。"""
    # 读取运行清单，结果解析器接入前只返回真实状态。
    manifest = load_run(run_id, project_root)
    return {"run_id": run_id, "status": manifest.get("status"), "result": _result_summary(manifest.get("result")), "error": manifest.get("error")}


def generate_report(run_id: str, project_root: str = ".", fmt: str = "markdown") -> dict[str, Any]:
    """生成 Markdown 或 HTML 工程辅助报告。"""
    # 委托报告模块，并保留失败状态和限制声明。
    return generate_run_report(run_id, project_root, fmt=fmt)
