"""MCP 高层工具函数；SDK层仅负责协议暴露。"""

# 导入类型。
from typing import Any

# 导入工作流服务和插件。
from .workflow import inspect_input, extract_structural_model, validate_structural_model
from .plugins import PLUGINS


def build_mesh(model: dict[str, Any]) -> dict[str, Any]:
    """调用插件网格接口。"""
    # 首版只返回明确未实现状态。
    return {"status": "not_implemented", "reason": "Gmsh 网格服务尚未接入", "project_id": model.get("project_id")}


def submit_simulation(model: dict[str, Any]) -> dict[str, Any]:
    """提交求解任务占位接口。"""
    # 首版不启动外部进程，避免伪造求解结果。
    return {"status": "not_implemented", "reason": "CalculiX/OpenSeesPy 执行器尚未接入"}


def get_simulation_status(run_id: str) -> dict[str, Any]:
    """查询求解任务状态占位接口。"""
    # 未接入任务存储时返回失败状态。
    return {"run_id": run_id, "status": "failed", "reason": "运行存储尚未接入"}


def get_result_summary(run_id: str) -> dict[str, Any]:
    """读取结果摘要占位接口。"""
    # 未生成结果时禁止返回假数据。
    return {"run_id": run_id, "status": "not_implemented", "reason": "结果解析器尚未接入"}


def generate_report(run_id: str) -> dict[str, Any]:
    """生成报告占位接口。"""
    # 报告必须等结果验证完成后生成。
    return {"run_id": run_id, "status": "not_implemented", "reason": "报告模板尚未接入"}
