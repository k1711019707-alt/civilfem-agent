"""输入资产检查器，保持读取行为确定且可追溯。"""

# 启用前向注解，兼容 Python 3.12 类型写法。
from __future__ import annotations

# 导入哈希、JSON、导入探测和路径工具。
import hashlib
import importlib.util
import json
import math
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

# 导入统一项目根限制。
from .security import configured_project_root

# 首版允许的输入扩展名。
SUPPORTED_FORMATS = {".json", ".ifc", ".dxf", ".step", ".stp", ".fcstd"}
# 限制单个输入文件为 256 MiB。
MAX_INPUT_BYTES = 256 * 1024 * 1024
# 限制 FCStd 核心 XML 解压后为 16 MiB。
MAX_DOCUMENT_XML_BYTES = 16 * 1024 * 1024


def file_sha256(path: Path) -> str:
    """按块计算文件 SHA-256，避免一次性读取大文件。"""
    # 创建哈希对象。
    digest = hashlib.sha256()
    # 以二进制方式读取文件。
    with path.open("rb") as stream:
        # 循环读取固定大小数据块。
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            # 累加当前数据块。
            digest.update(block)
    # 返回十六进制哈希。
    return digest.hexdigest()


def allowed_path(path: str | Path, project_root: str | Path | None = None) -> Path:
    """解析并限制路径位于项目根目录内。"""
    # 将项目根目录解析为绝对路径。
    root = configured_project_root(project_root)
    # 将输入路径解析为绝对路径。
    candidate = Path(path).expanduser().resolve()
    # 计算候选路径相对项目根目录的关系。
    try:
        candidate.relative_to(root)
    except ValueError as error:
        # 拒绝目录外路径，防止越权读取。
        raise ValueError(f"路径不在项目根目录内: {candidate}") from error
    # 返回已解析路径。
    return candidate


def _inspect_json(path: Path) -> dict[str, Any]:
    """检查 JSON 记录数量和顶层字段。"""
    # 读取 UTF-8 JSON 内容。
    data = json.loads(path.read_text(encoding="utf-8"))
    # 统一对象和数组输入。
    records = data if isinstance(data, list) else [data]
    # 只统计字典记录，避免对任意 JSON 结构做错误推断。
    first = records[0] if records and isinstance(records[0], dict) else {}
    # 返回结构化检查结果。
    return {"count": len(records), "keys": sorted(first)}


def _inspect_ifc(path: Path) -> dict[str, Any]:
    """使用 IfcOpenShell 检查 IFC 实体统计。"""
    # 检查可选开源库是否已安装。
    if importlib.util.find_spec("ifcopenshell") is None:
        return {"status": "not_implemented", "reason": "未安装可选依赖 ifcopenshell"}
    # 延迟导入，避免核心包强制依赖 IFC 环境。
    import ifcopenshell
    # 打开 IFC 文件。
    model = ifcopenshell.open(str(path))
    # 统计实体数量和主要结构实体。
    entities = model.by_type("IfcProduct")
    return {"count": len(entities), "entity_types": sorted({entity.is_a() for entity in entities})}


def _inspect_dxf(path: Path) -> dict[str, Any]:
    """使用 ezdxf 检查 DXF 图元和图层。"""
    # 检查可选开源库是否已安装。
    if importlib.util.find_spec("ezdxf") is None:
        return {"status": "not_implemented", "reason": "未安装可选依赖 ezdxf"}
    # 延迟导入，避免核心包强制依赖 DXF 环境。
    import ezdxf
    # 读取 DXF 文档。
    document = ezdxf.readfile(str(path))
    # 获取模型空间实体集合。
    space = document.modelspace()
    # 初始化几何摘要。
    layers: set[str] = set()
    entity_types: set[str] = set()
    points: list[tuple[float, float]] = []
    line_length = 0.0
    # 逐图元提取可确定的二维信息，不猜测工程语义。
    for entity in space:
        layers.add(entity.dxf.layer)
        entity_types.add(entity.dxftype())
        kind = entity.dxftype()
        if kind == "LINE":
            start = (float(entity.dxf.start.x), float(entity.dxf.start.y))
            end = (float(entity.dxf.end.x), float(entity.dxf.end.y))
            points.extend((start, end))
            line_length += math.dist(start, end)
        elif kind in {"LWPOLYLINE", "POLYLINE"}:
            vertices = [(float(point[0]), float(point[1])) for point in entity.get_points("xy")]
            points.extend(vertices)
            line_length += sum(math.dist(a, b) for a, b in zip(vertices, vertices[1:]))
            if getattr(entity, "closed", False) and len(vertices) > 2:
                line_length += math.dist(vertices[-1], vertices[0])
        elif kind == "CIRCLE":
            center = (float(entity.dxf.center.x), float(entity.dxf.center.y))
            radius = float(entity.dxf.radius)
            points.extend([(center[0] - radius, center[1] - radius), (center[0] + radius, center[1] + radius)])
        elif kind == "ARC":
            center = (float(entity.dxf.center.x), float(entity.dxf.center.y))
            radius = float(entity.dxf.radius)
            points.extend([(center[0] - radius, center[1] - radius), (center[0] + radius, center[1] + radius)])
            line_length += math.radians(float(entity.dxf.end_angle - entity.dxf.start_angle) % 360) * radius
    # 为空图纸返回空边界，否则返回 xmin、ymin、xmax、ymax。
    bounds = None if not points else [min(point[0] for point in points), min(point[1] for point in points), max(point[0] for point in points), max(point[1] for point in points)]
    # 返回图元、图层和几何统计。
    return {"count": len(space), "layers": sorted(layers), "entity_types": sorted(entity_types), "bounds": bounds, "line_length": line_length}


def _inspect_step(path: Path) -> dict[str, Any]:
    """只读检查 STEP 文本实体和 schema。"""
    # STEP 通常使用 ASCII 或 Latin-1，替换无法解码字符以保留结构。
    text = path.read_text(encoding="latin-1", errors="replace")
    # 验证 ISO-10303 文件签名。
    if "ISO-10303-21" not in text[:2048].upper():
        raise ValueError("文件缺少 ISO-10303-21 签名")
    # 统计 DATA 段中的实体记录。
    entities = re.findall(r"^\s*#\d+\s*=\s*([A-Z0-9_]+)\s*\(", text, flags=re.MULTILINE | re.IGNORECASE)
    # 提取 FILE_SCHEMA 声明。
    schema = re.search(r"FILE_SCHEMA\s*\(\s*\((.*?)\)\s*\)", text, flags=re.IGNORECASE | re.DOTALL)
    # 返回实体数量、类型和 schema 线索。
    return {"count": len(entities), "entity_types": sorted({name.upper() for name in entities}), "schema": schema.group(1).strip() if schema else None}


def _inspect_fcstd(path: Path) -> dict[str, Any]:
    """只读检查 FreeCAD FCStd 压缩文档。"""
    # FCStd 是 ZIP 容器，先验证格式。
    if not zipfile.is_zipfile(path):
        raise ValueError("FCStd 不是有效 ZIP 容器")
    # 打开容器并读取核心 Document.xml。
    with zipfile.ZipFile(path) as archive:
        # 检查 FreeCAD 文档清单。
        if "Document.xml" not in archive.namelist():
            raise ValueError("FCStd 缺少 Document.xml")
        # 检查核心 XML 解压大小，阻止压缩炸弹。
        if archive.getinfo("Document.xml").file_size > MAX_DOCUMENT_XML_BYTES:
            raise ValueError("FCStd Document.xml 超过 16 MiB 限制")
        # 解析 XML 文档。
        root = ET.fromstring(archive.read("Document.xml"))
        # 查找 FreeCAD 对象节点。
        objects = root.findall(".//Object")
        # 返回对象数量、类型和容器条目数。
        return {"count": len(objects), "object_types": sorted({item.attrib.get("type", "unknown") for item in objects}), "archive_entries": len(archive.namelist())}


def inspect_asset(path: str | Path, project_root: str | Path | None = None) -> dict[str, Any]:
    """检查 JSON、IFC 或 DXF 输入资产。"""
    # 解析并校验项目根目录边界。
    try:
        asset = allowed_path(path, project_root)
    except ValueError as error:
        return {"status": "invalid", "issues": [str(error)]}
    # 检查文件是否存在且为普通文件。
    if not asset.is_file():
        return {"status": "invalid", "issues": [f"文件不存在: {asset}"]}
    # 拒绝过大输入，限制解析器内存和 CPU 消耗。
    if asset.stat().st_size > MAX_INPUT_BYTES:
        return {"status": "invalid", "issues": ["输入文件超过 256 MiB 限制"]}
    # 读取扩展名并检查支持范围。
    suffix = asset.suffix.lower()
    if suffix not in SUPPORTED_FORMATS:
        return {"status": "not_implemented", "format": suffix or "unknown", "supported_formats": sorted(SUPPORTED_FORMATS)}
    # 先计算不可变输入哈希。
    result: dict[str, Any] = {"status": "inspected", "format": suffix[1:], "path": str(asset), "sha256": file_sha256(asset)}
    # 执行格式专用检查器。
    try:
        details = {".json": _inspect_json, ".ifc": _inspect_ifc, ".dxf": _inspect_dxf, ".step": _inspect_step, ".stp": _inspect_step, ".fcstd": _inspect_fcstd}[suffix](asset)
    except Exception as error:
        return {**result, "status": "invalid", "issues": [f"解析失败: {error}"]}
    # 合并可选库返回的能力状态。
    result.update(details)
    if result.get("status") == "inspected" and details.get("status") == "not_implemented":
        result["status"] = "not_implemented"
    # 返回结构化结果。
    return result
