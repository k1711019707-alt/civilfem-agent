import base64
import json
from pathlib import Path

from civilfem.api_client import ApiClientError, edit_image, explain_result
from civilfem.api_config import ApiConfig, load_api_config


class FakeResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.payload


def test_config_environment_precedes_file_and_redacts(monkeypatch, tmp_path):
    config_path = tmp_path / "api.json"
    config_path.write_text(json.dumps({"responses_url": "https://file.invalid", "responses_key": "file-secret"}), encoding="utf-8")
    monkeypatch.setenv("CIVILFEM_API_CONFIG", str(config_path))
    monkeypatch.setenv("CIVILFEM_RESPONSES_URL", "https://env.invalid")
    monkeypatch.setenv("CIVILFEM_RESPONSES_KEY", "env-secret-12345")
    config = load_api_config()
    assert config.responses_url == "https://env.invalid"
    assert "env-secret-12345" not in json.dumps(config.redacted())
    assert config.redacted()["responses_enabled"] is True


def test_explain_result_uses_responses_endpoint_without_leaking_key():
    seen = {}

    def opener(request, timeout):
        seen["url"] = request.full_url
        seen["auth"] = request.get_header("Authorization")
        return FakeResponse({"output_text": "结果仅供工程师复核。"})

    text = explain_result(ApiConfig("https://api.openai.com", "secret-key", "model"), {"max_von_mises": 12}, opener=opener)
    assert text.startswith("结果")
    assert seen["url"].endswith("/v1/responses")
    assert seen["auth"] == "Bearer secret-key"


def test_explain_result_uses_chat_completions_for_compatible_gateway():
    seen = {}

    def opener(request, timeout):
        seen["url"] = request.full_url
        return FakeResponse({"choices": [{"message": {"content": "兼容网关结果。"}}]})

    text = explain_result(ApiConfig("https://gateway.example.test", "secret-key", "gpt-5.6-sol"), {"max_von_mises": 12}, opener=opener)
    assert text == "兼容网关结果。"
    assert seen["url"].endswith("/v1/chat/completions")


def test_image_edit_decodes_base64_and_missing_config_is_safe(tmp_path):
    image = tmp_path / "cloud.png"
    image.write_bytes(b"png")
    encoded = base64.b64encode(b"edited").decode()
    output = edit_image(ApiConfig("", "", fhl_url="https://img.example", fhl_key="secret"), image, "enhance", opener=lambda request, timeout: FakeResponse({"data": [{"b64_json": encoded}]}))
    assert output == b"edited"
    try:
        explain_result(ApiConfig(), {})
    except ApiClientError as error:
        assert "未配置" in str(error)
    else:
        raise AssertionError("missing config must fail safely")
