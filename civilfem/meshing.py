"""使用开源 Gmsh 生成 H 型钢构件三维实体网格。"""

# 启用前向注解。
from __future__ import annotations

# 导入哈希、JSON 和路径工具。
import hashlib
from pathlib import Path
from typing import Any

# 导入运行清单创建函数。
from .runtime import create_run, save_run


def _hash(path: Path) -> str:
    """计算网格文件 SHA-256。"""
    # 读取网格文件并返回哈希。
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mesh_h_section(model: dict[str, Any], project_root: str | Path = ".", mesh_size: float = 100.0) -> dict[str, Any]:
    """为首个钢梁或钢柱生成四面体实体网格。"""
    # 创建网格运行清单。
    manifest = create_run(project_root, "mesh", model.get("input_hash") or model.get("project_id"), "gmsh")
    # 校验网格尺寸。
    if mesh_size <= 0:
        manifest.update({"status": "failed", "error": "mesh_size 必须大于 0"})
        return save_run(manifest)
    # 读取首个构件。
    components = model.get("components") or []
    if not components:
        manifest.update({"status": "failed", "error": "模型没有构件"})
        return save_run(manifest)
    # 读取构件和截面参数。
    component = components[0]
    section = component.get("section") or {}
    # 读取几何尺寸并允许长度回退到计算长度。
    try:
        h = float(section["h"])
        b = float(section["b"])
        tw = float(section["tw"])
        tf = float(section["tf"])
        length = float(component.get("length") or component.get("Lx") or 0)
    except (KeyError, TypeError, ValueError) as error:
        manifest.update({"status": "failed", "error": f"截面参数无效: {error}"})
        return save_run(manifest)
    # 拒绝退化或重叠几何。
    if min(h, b, tw, tf, length) <= 0 or h <= 2 * tf or b < tw:
        manifest.update({"status": "failed", "error": "H 型截面或长度参数无效"})
        return save_run(manifest)
    # 估算网格规模并限制资源消耗。
    estimated_cells = max(1.0, length / mesh_size) * max(1.0, b / mesh_size) * max(1.0, h / mesh_size) * 12
    if estimated_cells > 2_000_000:
        manifest.update({"status": "failed", "error": "预计网格超过 2,000,000 单元限制"})
        return save_run(manifest)
    # 延迟导入 Gmsh，使核心模型仍可独立运行。
    try:
        import gmsh
    except ImportError:
        manifest.update({"status": "not_implemented", "error": "未安装 gmsh"})
        return save_run(manifest)
    # 确定网格输出路径。
    mesh_path = Path(manifest["run_dir"]) / "mesh.msh"
    # 初始化 Gmsh 生命周期。
    gmsh.initialize(interruptible=False)
    try:
        # 禁止终端噪声，日志由运行清单负责。
        gmsh.option.setNumber("General.Terminal", 0)
        # 创建模型。
        gmsh.model.add(component.get("id", "component"))
        # 创建下翼缘实体。
        bottom = gmsh.model.occ.addBox(0, -b / 2, -h / 2, length, b, tf)
        # 创建腹板实体。
        web = gmsh.model.occ.addBox(0, -tw / 2, -h / 2 + tf, length, tw, h - 2 * tf)
        # 创建上翼缘实体。
        top = gmsh.model.occ.addBox(0, -b / 2, h / 2 - tf, length, b, tf)
        # 融合三个实体为单一 H 型钢体。
        volumes, _ = gmsh.model.occ.fuse([(3, bottom), (3, web)], [(3, top)])
        # 同步 OpenCASCADE 几何到 Gmsh 模型。
        gmsh.model.occ.synchronize()
        # 建立实体物理组，便于求解器识别。
        gmsh.model.addPhysicalGroup(3, [tag for dimension, tag in volumes if dimension == 3], name=component.get("id", "component"))
        # 设置全局网格尺寸。
        gmsh.option.setNumber("Mesh.MeshSizeMin", mesh_size)
        gmsh.option.setNumber("Mesh.MeshSizeMax", mesh_size)
        # 生成三维四面体网格。
        gmsh.model.mesh.generate(3)
        # 获取节点和单元数量。
        node_tags, _, _ = gmsh.model.mesh.getNodes()
        element_types, element_tags, _ = gmsh.model.mesh.getElements(3)
        element_count = sum(len(tags) for tags in element_tags)
        # 写出 Gmsh 标准网格文件。
        gmsh.write(str(mesh_path))
        # 更新成功清单。
        manifest.update({"status": "completed", "mesh": str(mesh_path), "mesh_hash": _hash(mesh_path), "node_count": len(node_tags), "element_count": element_count, "element_types": [int(value) for value in element_types], "mesh_size": mesh_size})
    except Exception as error:
        # 将几何或网格错误记录为失败。
        manifest.update({"status": "failed", "error": f"Gmsh 失败: {error}"})
    finally:
        # 始终释放 Gmsh 全局状态。
        gmsh.finalize()
    # 保存并返回最终清单。
    return save_run(manifest)
