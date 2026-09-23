"""生成带限制声明的 Markdown 和 HTML 工程辅助报告。"""

# 导入哈希、HTML 转义、JSON 和路径工具。
from __future__ import annotations
import hashlib
import html
import json
from pathlib import Path
from typing import Any

from .runtime import load_run
from .security import configured_project_root, validate_run_id


def _sha256(path: Path) -> str:
    """计算报告文件哈希。"""
    # 读取报告二进制内容并计算哈希。
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _markdown(manifest: dict[str, Any], result: dict[str, Any] | None = None) -> str:
    """构造 Markdown 报告正文。"""
    # 将运行状态和错误写入报告。
    status = manifest.get("status", "unknown")
    error = manifest.get("error") or "无"
    # 将结果字典格式化为可读 JSON。
    result_text = json.dumps(result or {}, ensure_ascii=False, indent=2)
    # 返回固定章节报告。
    return f"""# CivilFEM 工程辅助报告

## 运行信息

- 运行标识：`{manifest.get('run_id', 'unknown')}`
- 后端：`{manifest.get('backend') or '未指定'}`
- 状态：`{status}`
- 输入哈希：`{manifest.get('input_hash') or '未提供'}`
- 错误：{error}

## 结果摘要

```json
{result_text}
```

## 限制

本报告用于工程辅助分析。报告不替代人工复核、规范验算或正式审查。未完成、未实现或缺少输入的任务不得解释为通过。
"""


def generate_report(run_id: str, project_root: str | Path = ".", result: dict[str, Any] | None = None, fmt: str = "markdown") -> dict[str, Any]:
    """从运行清单生成 Markdown 或 HTML 报告。"""
    # 读取运行清单。
    manifest = load_run(run_id, project_root)
    # 限制报告格式为两种明确格式。
    if fmt not in {"markdown", "html"}:
        return {"run_id": run_id, "status": "invalid", "error": "format 必须是 markdown 或 html"}
    # 报告只能写入运行目录。
    # 由项目根和 run_id 重建目录，避免信任可编辑清单中的路径。
    # 校验运行标识格式。
    try:
        validate_run_id(run_id)
    except ValueError:
        return {"run_id": run_id, "status": "failed", "error": "非法 run_id"}
    # 解析受配置约束的项目根。
    try:
        root = configured_project_root(project_root)
    except ValueError as error:
        return {"run_id": run_id, "status": "failed", "error": str(error)}
    run_dir = (root / ".civilfem" / "runs" / run_id).resolve()
    # 拒绝目录穿越。
    try:
        run_dir.relative_to(root)
    except ValueError:
        return {"run_id": run_id, "status": "failed", "error": "运行目录越权"}
    if not run_dir.is_dir():
        return {"run_id": run_id, "status": "failed", "error": "运行目录不存在"}
    # 先生成 Markdown 原文。
    markdown = _markdown(manifest, result if result is not None else manifest.get("result"))
    # 根据格式生成报告内容。
    suffix = ".md"
    content = markdown
    if fmt == "html":
        suffix = ".html"
        content = "<html><head><meta charset='utf-8'><title>CivilFEM Report</title></head><body><pre>" + html.escape(markdown) + "</pre></body></html>"
    # 写入运行目录下的固定文件名。
    report_path = run_dir / f"report{suffix}"
    report_path.write_text(content, encoding="utf-8")
    # 返回报告路径和哈希。
    return {"run_id": run_id, "status": manifest.get("status"), "report": str(report_path), "sha256": _sha256(report_path)}
