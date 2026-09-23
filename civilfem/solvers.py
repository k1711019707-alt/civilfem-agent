"""OpenSeesPy 弹性梁求解适配器。"""

# 启用前向注解。
from __future__ import annotations

# 导入路径和类型工具。
from pathlib import Path
from typing import Any

# 导入运行清单函数。
from .runtime import create_run, save_run


def _section_properties(section: dict[str, Any]) -> tuple[float, float]:
    """计算 H 型截面面积和强轴惯性矩。"""
    # 读取截面尺寸。
    h = float(section["h"])
    b = float(section["b"])
    tw = float(section["tw"])
    tf = float(section["tf"])
    # 计算腹板净高。
    web_height = h - 2 * tf
    # 校验基本几何。
    if min(h, b, tw, tf, web_height) <= 0 or b < tw:
        raise ValueError("H 型截面参数无效")
    # 计算截面面积。
    area = 2 * b * tf + web_height * tw
    # 计算强轴惯性矩。
    inertia = (b * h**3 - (b - tw) * web_height**3) / 12
    # 返回截面属性。
    return area, inertia


def solve_opensees_beam(model: dict[str, Any], project_root: str | Path = ".") -> dict[str, Any]:
    """按明确的悬臂梁假设执行二维线弹性静力分析。"""
    # 创建可追溯运行清单。
    manifest = create_run(project_root, "simulation", model.get("input_hash") or model.get("project_id"), "openseespy")
    # 获取首个构件。
    components = model.get("components") or []
    if not components:
        manifest.update({"status": "failed", "error": "模型没有构件"})
        return save_run(manifest)
    # 读取构件和长度。
    component = components[0]
    length = float(component.get("length") or component.get("Lx") or 0)
    # 要求显式使用当前支持的边界假设。
    boundary = (model.get("analysis") or {}).get("boundary")
    if boundary != "cantilever":
        manifest.update({"status": "pending_confirmation", "error": "analysis.boundary 必须显式设为 cantilever"})
        return save_run(manifest)
    # 延迟导入 OpenSeesPy。
    try:
        import openseespy.opensees as ops
    except ImportError:
        manifest.update({"status": "not_implemented", "error": "未安装 openseespy"})
        return save_run(manifest)
    # 读取截面并执行求解。
    try:
        area, inertia = _section_properties(component["section"])
        if length <= 0:
            raise ValueError("构件长度必须大于 0")
        # 读取弹性模量，默认采用结构钢 206000 MPa。
        elastic_modulus = float((model.get("analysis") or {}).get("elastic_modulus", 206000.0))
        # 将构件作用转换为节点荷载。
        axial = float(component.get("N", 0)) * 1000
        shear = float(component.get("V", 0)) * 1000
        moment = float(component.get("Mx", 0)) * 1_000_000
        # 清理 OpenSees 全局模型。
        ops.wipe()
        # 创建二维三自由度模型。
        ops.model("basic", "-ndm", 2, "-ndf", 3)
        # 创建固定端和自由端节点。
        ops.node(1, 0.0, 0.0)
        ops.node(2, length, 0.0)
        # 固定根部三个自由度。
        ops.fix(1, 1, 1, 1)
        # 定义线性几何变换。
        ops.geomTransf("Linear", 1)
        # 创建弹性梁柱单元。
        ops.element("elasticBeamColumn", 1, 1, 2, area, elastic_modulus, inertia, 1)
        # 定义线性荷载时程。
        ops.timeSeries("Linear", 1)
        # 创建静力荷载模式。
        ops.pattern("Plain", 1, 1)
        # 对自由端施加轴力、剪力和弯矩。
        ops.load(2, axial, -shear, moment)
        # 配置线性静力分析。
        ops.system("BandGeneral")
        ops.numberer("Plain")
        ops.constraints("Plain")
        ops.integrator("LoadControl", 1.0)
        ops.algorithm("Linear")
        ops.analysis("Static")
        # 执行单步求解。
        code = ops.analyze(1)
        # 计算约束反力。
        ops.reactions()
        # 读取自由端位移和根部反力。
        displacement = [float(value) for value in ops.nodeDisp(2)]
        reaction = [float(value) for value in ops.nodeReaction(1)]
        # 组织统一结果。
        result = {"displacement": displacement, "reaction": reaction, "analysis": "linear_static", "model_order": "beam", "assumption": "二维线弹性悬臂梁；构件 N/V/Mx 作为自由端节点荷载", "units": "N-mm-MPa"}
        # 保存求解状态和结果。
        manifest.update({"status": "completed" if code == 0 else "failed", "returncode": int(code), "result": result, "error": None if code == 0 else "OpenSees 求解失败"})
    except Exception as error:
        # 捕获输入或求解错误并保留证据。
        manifest.update({"status": "failed", "error": f"OpenSeesPy 失败: {error}"})
    finally:
        # 释放 OpenSees 全局模型状态。
        ops.wipe()
    # 保存并返回最终清单。
    return save_run(manifest)
