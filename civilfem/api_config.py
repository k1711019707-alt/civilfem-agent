"""本机 API 配置加载与脱敏。"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ApiConfig:
    responses_url: str = ""
    responses_key: str = ""
    responses_model: str = "gpt-5.6-sol"
    fhl_url: str = ""
    fhl_key: str = ""

    @property
    def responses_enabled(self) -> bool:
        return bool(self.responses_url and self.responses_key)

    @property
    def fhl_enabled(self) -> bool:
        return bool(self.fhl_url and self.fhl_key)

    def redacted(self) -> dict[str, Any]:
        def mask(value: str) -> str:
            if not value:
                return ""
            return f"{value[:4]}…{value[-4:]}" if len(value) > 10 else "已配置"

        return {
            "responses_url": self.responses_url,
            "responses_model": self.responses_model,
            "responses_key": mask(self.responses_key),
            "responses_enabled": self.responses_enabled,
            "fhl_url": self.fhl_url,
            "fhl_key": mask(self.fhl_key),
            "fhl_enabled": self.fhl_enabled,
        }


def _read_file(path: str | Path | None) -> dict[str, Any]:
    if not path:
        return {}
    try:
        value = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def load_api_config() -> ApiConfig:
    """环境变量优先；外部文件仅作本机运行时回退。"""
    # 仓库不携带任何 URL 或密钥；默认配置保存在用户本机应用数据目录。
    local_root = os.getenv("LOCALAPPDATA")
    local_config = Path(local_root) / "CivilFEM" / "api_config.json" if local_root else None
    file_data = _read_file(os.getenv("CIVILFEM_API_CONFIG") or local_config)

    def get(name: str, key: str, default: str = "") -> str:
        return str(os.getenv(name) or file_data.get(key) or default).strip()

    return ApiConfig(
        responses_url=get("CIVILFEM_RESPONSES_URL", "responses_url"),
        responses_key=get("CIVILFEM_RESPONSES_KEY", "responses_key"),
        responses_model=get("CIVILFEM_RESPONSES_MODEL", "responses_model", "gpt-5.6-sol"),
        fhl_url=get("CIVILFEM_FHL_URL", "fhl_url"),
        fhl_key=get("CIVILFEM_FHL_KEY", "fhl_key"),
    )
