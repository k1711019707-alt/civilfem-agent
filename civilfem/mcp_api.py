"""MCP 高层工具函数；SDK层仅负责协议暴露。"""

# 导入类型。
from typing import Any

# 导入工作流服务和插件。
from .workflow import inspect_input, extract_structural_model, validate_structural_model
from .runtime import capabilities, submit_run, load_run
from .reports import generate_report as generate_run_report
from .meshing import mesh_h_section
from .solvers import solve_opensees_beam


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


def get_simulation_status(run_id: str, project_root: str = ".") -> dict[str, Any]:
    """查询运行清单状态。"""
    # 从项目根目录读取运行清单。
    return load_run(run_id, project_root)


def get_result_summary(run_id: str, project_root: str = ".") -> dict[str, Any]:
    """读取统一结果摘要。"""
    # 读取运行清单，结果解析器接入前只返回真实状态。
    manifest = load_run(run_id, project_root)
    return {"run_id": run_id, "status": manifest.get("status"), "result": manifest.get("result"), "error": manifest.get("error")}


def generate_report(run_id: str, project_root: str = ".", fmt: str = "markdown") -> dict[str, Any]:
    """生成 Markdown 或 HTML 工程辅助报告。"""
    # 委托报告模块，并保留失败状态和限制声明。
    return generate_run_report(run_id, project_root, fmt=fmt)
