"""集中实现项目根目录和资源边界。"""

# 导入环境变量、正则和路径工具。
from __future__ import annotations
import os
import re
from pathlib import Path

# 运行标识固定为内部生成的 UUID 格式。
RUN_ID_PATTERN = re.compile(r"^run-[0-9a-f]{32}$")


def configured_project_root(requested: str | Path | None = None) -> Path:
    """返回配置项目根，并限制请求目录位于根内。"""
    # 由服务启动环境或当前目录确定不可由工具调用覆盖的根。
    base = Path(os.environ.get("CIVILFEM_PROJECT_ROOT", Path.cwd())).expanduser().resolve()
    # 确保配置根存在。
    base.mkdir(parents=True, exist_ok=True)
    # 未请求子目录时直接使用配置根。
    if requested is None or str(requested) in {"", "."}:
        return base
    # 解析请求目录。
    candidate = Path(requested).expanduser().resolve()
    # 检查请求目录没有越过配置根。
    try:
        candidate.relative_to(base)
    except ValueError as error:
        raise ValueError(f"请求目录不在配置项目根内: {candidate}") from error
    # 返回安全子目录。
    return candidate


def validate_run_id(run_id: str) -> str:
    """只接受内部 UUID 运行标识。"""
    # 使用完整匹配拒绝路径片段和保留设备名。
    if RUN_ID_PATTERN.fullmatch(run_id) is None:
        raise ValueError("非法 run_id")
    # 返回已验证标识。
    return run_id
