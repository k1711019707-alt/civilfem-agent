"""CalculiX 三维实体有限元适配器。"""

from __future__ import annotations

import math
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any


def _find_executable(executable: str | None = None) -> str | None:
    configured = executable or os.environ.get("CIVILFEM_CALCULIX")
    if configured:
        return str(Path(configured).resolve()) if Path(configured).is_file() else None
    found = next((shutil.which(name) for name in ("ccx", "calculix", "CalculiX") if shutil.which(name)), None)
    if found:
        return found
    for candidate in (Path(r"D:\CalculiX\ccx.exe"), Path(r"C:\CalculiX\ccx.exe")):
        if candidate.is_file():
            return str(candidate)
    return None


def _mesh_lines(mesh: dict[str, Any]) -> tuple[list[str], list[str]]:
    points = mesh["points"]
    cells = mesh["cells"]
    nodes = [f"{i}, {float(p[0]):.12g}, {float(p[1]):.12g}, {float(p[2]):.12g}" for i, p in enumerate(points, 1)]
    elements: list[str] = []
    element_id = 1
    for block in cells:
        cell_type = block["type"]
        if cell_type not in {"tetra", "tetra10"}:
            continue
        ccx_type = "C3D4" if cell_type == "tetra" else "C3D10"
        for connectivity in block["data"]:
            elements.append(f"{element_id}, {', '.join(str(int(index) + 1) for index in connectivity)}")
            element_id += 1
    if not elements:
        raise ValueError("网格不含 tetra/tetra10 单元")
    return nodes, elements


def _wrapped(values: list[int], width: int = 12) -> list[str]:
    return [", ".join(str(value) for value in values[index:index + width]) for index in range(0, len(values), width)]


def build_calculix_input(mesh: dict[str, Any], output_path: str | Path, *, youngs_modulus: float = 206000.0, poisson_ratio: float = 0.3, load: tuple[float, float, float] = (0.0, 0.0, 0.0), moment_x: float = 0.0) -> Path:
    """将 meshio 风格网格写为可执行的 CalculiX 输入文件。"""
    nodes, elements = _mesh_lines(mesh)
    element_type = "C3D10" if len(elements[0].split(",")) == 11 else "C3D4"
    points = mesh["points"]
    min_x = min(float(point[0]) for point in points)
    max_x = max(float(point[0]) for point in points)
    fixed = [i + 1 for i, point in enumerate(points) if abs(float(point[0]) - min_x) <= 1e-8]
    loaded = [i + 1 for i, point in enumerate(points) if abs(float(point[0]) - max_x) <= 1e-8]
    if not fixed or not loaded:
        raise ValueError("网格缺少可识别的固定端或加载端")
    lines = [
        "*HEADING", "CivilFEM 3D FEM", "*NODE", *nodes,
        f"*ELEMENT, TYPE={element_type}, ELSET=EALL", *elements,
        "*NSET, NSET=FIXED", *_wrapped(fixed),
        "*NSET, NSET=LOADED", *_wrapped(loaded),
        "*ELSET, ELSET=EALL", *_wrapped(list(range(1, len(elements) + 1))),
        "*MATERIAL, NAME=STEEL", "*ELASTIC", f"{youngs_modulus}, {poisson_ratio}",
        "*SOLID SECTION, ELSET=EALL, MATERIAL=STEEL", ",",
        "*STEP", "*STATIC", "1., 1., 1e-05, 1.",
        "*BOUNDARY", "FIXED, 1, 3",
        "*CLOAD",
    ]
    for node in loaded:
        for dof, value in enumerate(load, 1):
            if value:
                lines.append(f"{node}, {dof}, {value / len(loaded):.12g}")
    if moment_x:
        z_values = {node: float(points[node - 1][2]) for node in loaded}
        mean_z = sum(z_values.values()) / len(z_values)
        denominator = sum((z - mean_z) ** 2 for z in z_values.values())
        if denominator <= 0:
            raise ValueError("加载端节点无法形成 X 轴弯矩力偶")
        for node, z in z_values.items():
            lines.append(f"{node}, 2, {-moment_x * (z - mean_z) / denominator:.12g}")
    lines += ["*NODE FILE", "U", "*EL FILE", "S", "*END STEP", ""]
    target = Path(output_path).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines), encoding="ascii")
    return target


def run_calculix(input_path: str | Path, executable: str | None = None, timeout: int = 300) -> dict[str, Any]:
    source = Path(input_path).resolve()
    command = _find_executable(executable)
    if command is None:
        return {"status": "not_implemented", "error": "未找到 CalculiX 可执行文件"}
    try:
        completed = subprocess.run([command, source.stem], cwd=source.parent, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"status": "failed", "error": f"CalculiX 执行失败: {error}"}
    frd = source.with_suffix(".frd")
    status = "completed" if completed.returncode == 0 and frd.is_file() else "failed"
    result = {"status": status, "returncode": completed.returncode, "stdout": completed.stdout[-4000:], "stderr": completed.stderr[-4000:], "frd": str(frd) if frd.is_file() else None}
    if status != "completed":
        result["error"] = "CalculiX 未生成有效 .frd 结果"
    return result


def _von_mises(values: list[float]) -> float:
    sx, sy, sz, txy, tyz, tzx = (values + [0.0] * 6)[:6]
    return math.sqrt(0.5 * ((sx - sy) ** 2 + (sy - sz) ** 2 + (sz - sx) ** 2 + 6 * (txy**2 + tyz**2 + tzx**2)))


def parse_frd_results(frd_path: str | Path) -> dict[str, Any]:
    path = Path(frd_path)
    if not path.is_file():
        raise FileNotFoundError(f"FRD 文件不存在: {path}")
    mode = None
    displacements: dict[int, list[float]] = {}
    stresses: dict[int, list[float]] = {}
    for raw in path.read_text(encoding="ascii", errors="replace").splitlines():
        line = raw.strip()
        upper = line.upper()
        if "DISP" in upper:
            mode = "disp"
            continue
        if "STRESS" in upper:
            mode = "stress"
            continue
        if line == "-3" or line == "-1":
            mode = None
            continue
        if not (line.startswith("-1") or line.startswith("-5")) or mode is None:
            continue
        fields = re.findall(r"[+-]?(?:\d+\.\d*|\.\d+|\d+)(?:[Ee][+-]?\d+)?", line)
        if len(fields) < 5:
            continue
        try:
            node = int(fields[1])
            values = [float(value) for value in fields[2:]]
        except ValueError:
            continue
        (displacements if mode == "disp" else stresses)[node] = values
    if not displacements and not stresses:
        raise ValueError("FRD 未包含可解析的位移或应力记录")
    displacement_norms = {node: math.sqrt(sum(value * value for value in values[:3])) for node, values in displacements.items()}
    von_mises = {node: _von_mises(values) for node, values in stresses.items()}
    return {
        "displacement": displacements,
        "stress": stresses,
        "von_mises": von_mises,
        "max_displacement": max(displacement_norms.values(), default=0.0),
        "max_displacement_node": max(displacement_norms, key=displacement_norms.get) if displacement_norms else None,
        "max_von_mises": max(von_mises.values(), default=0.0),
        "max_von_mises_node": max(von_mises, key=von_mises.get) if von_mises else None,
        "displacement_units": "mm",
        "stress_units": "MPa",
    }
