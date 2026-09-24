"""网格和求解运行生命周期，记录状态而不伪造结果。"""

# 启用前向注解。
from __future__ import annotations

# 导入标准库运行工具。
import importlib.util
import json
import os
import shutil
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# 导入集中安全边界。
from .security import configured_project_root, validate_run_id


def _now() -> str:
    """返回 UTC ISO 时间。"""
    # 统一使用带时区时间，便于跨机器审计。
    return datetime.now(timezone.utc).isoformat()


def _calculix_executable() -> str | None:
    """返回服务配置或 PATH 中的 CalculiX 可执行文件。"""
    # 优先读取由服务启动方设置的可信可执行文件路径。
    configured = os.environ.get("CIVILFEM_CALCULIX")
    # 仅接受真实文件，避免把无效配置传给子进程。
    if configured and Path(configured).expanduser().is_file():
        # 返回规范化绝对路径。
        return str(Path(configured).expanduser().resolve())
    # 回退到 PATH 中的常见命令名。
    found = next((command for name in ("ccx", "calculix", "CalculiX") if (command := shutil.which(name))), None)
    if found:
        return found
    for candidate in (Path(r"D:\CalculiX\ccx.exe"), Path(r"C:\CalculiX\ccx.exe")):
        if candidate.is_file():
            return str(candidate)
    return None


def capabilities() -> dict[str, bool]:
    """探测本机可用开源网格和求解后端。"""
    # 检查 Gmsh 命令和 Python 模块。
    gmsh = shutil.which("gmsh") is not None or importlib.util.find_spec("gmsh") is not None
    # 检查服务配置或 CalculiX 常见命令名称。
    calculix = _calculix_executable() is not None
    # 检查 OpenSeesPy Python 模块。
    openseespy = importlib.util.find_spec("openseespy") is not None
    # 返回后端能力表。
    return {"gmsh": gmsh, "calculix": calculix, "openseespy": openseespy}


def _rooted(path: str | Path, root: str | Path) -> Path:
    """解析项目根内路径并拒绝越权路径。"""
    # 解析项目根目录。
    base = Path(root).resolve()
    # 解析待检查路径。
    target = Path(path).expanduser().resolve()
    # 确认目标属于根目录。
    try:
        target.relative_to(base)
    except ValueError as error:
        raise ValueError(f"运行路径越权: {target}") from error
    # 返回安全路径。
    return target


def create_run(project_root: str | Path, kind: str, input_hash: str | None = None, backend: str | None = None) -> dict[str, Any]:
    """创建唯一运行目录和 JSON 清单。"""
    # 解析并创建项目根目录。
    root = configured_project_root(project_root)
    root.mkdir(parents=True, exist_ok=True)
    # 生成不可预测的运行标识。
    run_id = f"run-{uuid.uuid4().hex}"
    # 将运行目录固定在项目根下。
    run_dir = _rooted(root / ".civilfem" / "runs" / run_id, root)
    run_dir.mkdir(parents=True, exist_ok=False)
    # 组织最小可追溯运行清单。
    manifest = {"run_id": run_id, "kind": kind, "input_hash": input_hash, "backend": backend, "status": "queued", "created_at": _now(), "run_dir": str(run_dir), "error": None}
    # 写入清单文件。
    (run_dir / "run_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    # 返回清单。
    return manifest


def save_run(manifest: dict[str, Any]) -> dict[str, Any]:
    """将更新后的运行清单写回原运行目录。"""
    # 从已创建的清单读取运行目录。
    run_dir = Path(manifest["run_dir"])
    # 拒绝缺失运行目录。
    if not run_dir.is_dir():
        raise ValueError(f"运行目录不存在: {run_dir}")
    # 原子替换前先写入临时清单。
    temporary = run_dir / "run_manifest.json.tmp"
    temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    # 在同一目录内替换最终清单。
    temporary.replace(run_dir / "run_manifest.json")
    # 返回已保存清单。
    return manifest


def load_run(run_id: str, project_root: str | Path) -> dict[str, Any]:
    """读取项目根内运行清单。"""
    # 只允许简单 run_id，拒绝路径字符。
    try:
        validate_run_id(run_id)
    except ValueError:
        return {"run_id": run_id, "status": "failed", "error": "非法 run_id"}
    # 解析清单路径并校验边界。
    root = configured_project_root(project_root)
    manifest_path = _rooted(root / ".civilfem" / "runs" / run_id / "run_manifest.json", root)
    # 清单缺失时返回明确失败。
    if not manifest_path.is_file():
        return {"run_id": run_id, "status": "failed", "error": "运行清单不存在"}
    # 读取 JSON 清单。
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def submit_run(project_root: str | Path, backend: str, input_hash: str | None = None, solver_input: str | None = None) -> dict[str, Any]:
    """创建网格或求解任务，并在后端不可用时明确停止。"""
    # 探测后端能力。
    available = capabilities().get(backend, False)
    # 创建可审计运行清单。
    manifest = create_run(project_root, "simulation", input_hash, backend)
    # 后端缺失时保留清单并标记未实现。
    if not available:
        manifest.update({"status": "not_implemented", "error": f"后端不可用: {backend}", "finished_at": _now()})
    # 当前没有求解输入时不启动外部程序。
    elif not solver_input:
        manifest.update({"status": "not_implemented", "error": "缺少已验证的求解器输入文件", "finished_at": _now()})
    else:
        # 解析求解输入并限制在项目根目录内。
        try:
            input_path = _rooted(solver_input, project_root)
        except ValueError as error:
            manifest.update({"status": "failed", "error": str(error), "finished_at": _now()})
        else:
            # 仅使用可信配置解析出的固定可执行文件，禁止任意 shell 字符串。
            command = _calculix_executable() if backend == "calculix" else None
            if command is None:
                manifest.update({"status": "not_implemented", "error": f"尚未实现后端执行器: {backend}", "finished_at": _now()})
            else:
                # 以参数数组启动外部求解器。
                completed = subprocess.run([command, input_path.stem], cwd=input_path.parent, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300, check=False)
                # 根据退出码记录完成或失败。
                manifest.update({"status": "completed" if completed.returncode == 0 else "failed", "returncode": completed.returncode, "stdout": completed.stdout[-4000:], "stderr": completed.stderr[-4000:], "finished_at": _now()})
    # 持久化最终状态。
    save_run(manifest)
    # 返回运行标识和状态。
    return manifest
