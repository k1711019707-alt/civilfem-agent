"""使用 PyVista 离屏渲染网格截图。"""

# 导入路径和类型工具。
from __future__ import annotations
from pathlib import Path
from typing import Any


def render_mesh(mesh_path: str | Path, output_path: str | Path | None = None) -> dict[str, Any]:
    """将 Gmsh 网格渲染为 PNG。"""
    # 解析输入网格路径。
    source = Path(mesh_path).resolve()
    # 检查输入网格是否存在。
    if not source.is_file():
        return {"status": "failed", "error": f"网格不存在: {source}"}
    # 设置输出截图路径。
    target = Path(output_path).resolve() if output_path else source.with_suffix(".png")
    # 限制截图写入网格所在目录，防止任意路径写入。
    try:
        target.relative_to(source.parent)
    except ValueError:
        return {"status": "failed", "error": "截图路径必须位于网格目录内"}
    # 延迟导入开源可视化库。
    try:
        import meshio
        import numpy as np
        import pyvista as pv
    except ImportError as error:
        return {"status": "not_implemented", "error": f"缺少可视化依赖: {error}"}
    # 读取 Gmsh 网格。
    mesh = meshio.read(source)
    # 收集四面体单元块。
    tetrahedra = [block.data for block in mesh.cells if block.type in {"tetra", "tetra10"}]
    # 当前视图要求实体单元。
    if not tetrahedra:
        return {"status": "failed", "error": "网格不含四面体单元"}
    # 合并四面体连接表。
    connectivity = np.vstack(tetrahedra)
    # 将 meshio 连接表转换为 VTK 单元数组。
    cells = np.hstack([np.full((len(connectivity), 1), connectivity.shape[1]), connectivity]).ravel()
    # 选择 VTK 四面体类型。
    cell_type = pv.CellType.TETRA if connectivity.shape[1] == 4 else pv.CellType.QUADRATIC_TETRA
    # 创建 PyVista 非结构网格。
    grid = pv.UnstructuredGrid(cells, np.full(len(connectivity), cell_type), mesh.points)
    # 创建离屏绘图器。
    plotter = pv.Plotter(off_screen=True, window_size=(1280, 720))
    # 添加网格和边线。
    plotter.add_mesh(grid, color="steelblue", show_edges=True)
    # 使用等轴测视角。
    plotter.view_isometric()
    # 缩放到全部结构。
    plotter.reset_camera()
    # 保存截图并关闭绘图器。
    plotter.show(screenshot=str(target), auto_close=True)
    # 返回截图资产。
    return {"status": "completed", "image": str(target), "cell_count": grid.n_cells, "point_count": grid.n_points}


def render_stress_cloud(mesh_path: str | Path, von_mises: dict[int, float], output_path: str | Path | None = None) -> dict[str, Any]:
    """将节点 von Mises 应力渲染为 PNG 云图。"""
    source = Path(mesh_path).resolve()
    if not source.is_file():
        return {"status": "failed", "error": f"网格不存在: {source}"}
    target = Path(output_path).resolve() if output_path else source.with_name("stress_cloud.png")
    try:
        target.relative_to(source.parent)
    except ValueError:
        return {"status": "failed", "error": "云图路径必须位于网格目录内"}
    try:
        import meshio
        import numpy as np
        import pyvista as pv
    except ImportError as error:
        return {"status": "not_implemented", "error": f"缺少可视化依赖: {error}"}
    mesh = meshio.read(source)
    tetrahedra = [block.data for block in mesh.cells if block.type in {"tetra", "tetra10"}]
    if not tetrahedra:
        return {"status": "failed", "error": "网格不含四面体单元"}
    connectivity = np.vstack(tetrahedra)
    cells = np.hstack([np.full((len(connectivity), 1), connectivity.shape[1]), connectivity]).ravel()
    cell_type = pv.CellType.TETRA if connectivity.shape[1] == 4 else pv.CellType.QUADRATIC_TETRA
    grid = pv.UnstructuredGrid(cells, np.full(len(connectivity), cell_type), mesh.points)
    values = np.array([float(von_mises.get(index + 1, 0.0)) for index in range(grid.n_points)])
    grid.point_data["von Mises (MPa)"] = values
    plotter = pv.Plotter(off_screen=True, window_size=(1400, 900))
    plotter.add_mesh(grid, scalars="von Mises (MPa)", cmap="turbo", show_edges=False, smooth_shading=True, scalar_bar_args={"title": "von Mises (MPa)"})
    plotter.view_isometric()
    plotter.reset_camera()
    plotter.show(screenshot=str(target), auto_close=True)
    return {"status": "completed", "image": str(target), "field": "von Mises (MPa)", "max_value": float(values.max(initial=0.0)), "cell_count": grid.n_cells, "point_count": grid.n_points}
