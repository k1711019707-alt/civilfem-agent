"""可选工程辅助 API 客户端；不参与 FEM 数值计算。"""
from __future__ import annotations

import base64
import json
import mimetypes
import uuid
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .api_config import ApiConfig


class ApiClientError(RuntimeError):
    """脱敏后的 API 错误。"""


def _endpoint(url: str, suffix: str) -> str:
    value = str(url or "").strip().rstrip("/")
    if not value:
        raise ApiClientError("API 地址未配置")
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ApiClientError("API 地址无效")
    if parsed.path.endswith(suffix):
        return value
    return value + suffix


def _request_json(request: Request, opener: Callable[..., Any] = urlopen, timeout: float = 30.0) -> dict[str, Any]:
    try:
        with opener(request, timeout=timeout) as response:
            raw = response.read()
    except HTTPError as error:
        raise ApiClientError(f"API HTTP 错误：{error.code}") from None
    except (URLError, TimeoutError, OSError) as error:
        raise ApiClientError(f"API 连接失败：{type(error).__name__}") from None
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ApiClientError(f"API 响应不是有效 JSON：{type(error).__name__}") from None
    if not isinstance(value, dict):
        raise ApiClientError("API 响应格式无效")
    return value


def _extract_text(result: dict[str, Any]) -> str:
    text = result.get("output_text")
    if text:
        return str(text)
    output = result.get("output") or []
    if isinstance(output, list):
        text = " ".join(str(item.get("text", "")) for item in output if isinstance(item, dict))
        if text:
            return text
    choices = result.get("choices") or []
    if choices and isinstance(choices[0], dict):
        message = choices[0].get("message") or {}
        if isinstance(message, dict) and message.get("content"):
            return str(message["content"])
    return ""


def explain_result(
    config: ApiConfig,
    summary: dict[str, Any],
    *,
    opener: Callable[..., Any] = urlopen,
    timeout: float = 30.0,
) -> str:
    if not config.responses_enabled:
        raise ApiClientError("Responses API 未配置")
    host = (urlparse(config.responses_url).hostname or "").lower()
    prompt = "请用简体中文解释以下 FEM 工程结果，明确说明仅供工程师复核，不得修改数值：" + json.dumps(summary, ensure_ascii=False)

    def post(url: str, payload: dict[str, Any]) -> dict[str, Any]:
        request = Request(url, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"), method="POST")
        request.add_header("Authorization", f"Bearer {config.responses_key}")
        request.add_header("Content-Type", "application/json")
        return _request_json(request, opener=opener, timeout=timeout)

    # 海之子对非 OpenAI 域名优先使用兼容 Chat Completions；保留 Responses
    # 路由作为标准端点，避免中继网关把长连接请求静默丢弃。
    if host and host != "api.openai.com":
        result = post(_endpoint(config.responses_url, "/v1/chat/completions"), {
            "model": config.responses_model,
            "messages": [
                {"role": "system", "content": "你是有限元工程结果解释助手。不得修改或伪造数值，必须提示工程师复核。"},
                {"role": "user", "content": prompt},
            ],
        })
    else:
        result = post(_endpoint(config.responses_url, "/v1/responses"), {"model": config.responses_model, "input": prompt})
    text = _extract_text(result)
    if not text:
        raise ApiClientError("工程分析 API 未返回可读文本")
    return text


def edit_image(
    config: ApiConfig,
    image_path: str | Path,
    prompt: str,
    *,
    opener: Callable[..., Any] = urlopen,
    timeout: float = 60.0,
) -> bytes:
    if not config.fhl_enabled:
        raise ApiClientError("FHL Images API 未配置")
    url = _endpoint(config.fhl_url, "/v1/images/edits")
    path = Path(image_path)
    boundary = f"----CivilFEM{uuid.uuid4().hex}"
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    parts = []

    def field(name: str, value: str) -> None:
        parts.extend([f"--{boundary}\r\n".encode(), f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(), value.encode(), b"\r\n"])

    field("model", "gpt-image-2")
    field("prompt", prompt)
    parts.extend([f"--{boundary}\r\n".encode(), f'Content-Disposition: form-data; name="image"; filename="{path.name}"\r\nContent-Type: {mime}\r\n\r\n'.encode(), path.read_bytes(), b"\r\n", f"--{boundary}--\r\n".encode()])
    request = Request(url, data=b"".join(parts), method="POST")
    request.add_header("Authorization", f"Bearer {config.fhl_key}")
    request.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    result = _request_json(request, opener=opener, timeout=timeout)
    try:
        encoded = result["data"][0]["b64_json"]
        return base64.b64decode(encoded)
    except (KeyError, IndexError, TypeError, ValueError) as error:
        raise ApiClientError(f"FHL Images 响应格式无效：{type(error).__name__}") from None
