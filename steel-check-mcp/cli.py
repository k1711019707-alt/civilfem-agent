#!/usr/bin/env python3
"""钢结构校核 CLI —— 让任何人都能复现你的结果

用法：
  python cli.py --demo
  python cli.py --in member.json
  python cli.py --in member.json --out result.json
  echo '{"member_id":"KZ-1",...}' | python cli.py --stdin
"""

from __future__ import annotations

import argparse
import json
import sys

from steelcheck import IH, Member, check_member


def build(d: dict) -> Member:
    """从 JSON 字典构造构件。

    截面尺寸支持两种写法（便于与 MCP 工具参数保持一致）：
      "section": {"h":300,"b":300,"tw":10,"tf":15}
      或直接平铺 "h":300,"b":300,"tw":10,"tf":15
    """
    sec_d = d.get("section") or {k: d[k] for k in ("h", "b", "tw", "tf") if k in d}
    missing = [k for k in ("h", "b", "tw", "tf") if k not in sec_d]
    if missing:
        raise ValueError(f"{d.get('member_id', '?')} 缺少截面参数：{missing}")
    sec = IH(**{k: float(sec_d[k]) for k in ("h", "b", "tw", "tf")})
    return Member(
        member_id=d.get("member_id", "unnamed"),
        section=sec,
        steel=d.get("steel", "Q355"),
        Mx=float(d.get("Mx", 0.0)),
        My=float(d.get("My", 0.0)),
        V=float(d.get("V", 0.0)),
        N=float(d.get("N", 0.0)),
        Lx=float(d.get("Lx", 0.0)),
        Ly=float(d.get("Ly", 0.0)),
        phi_b=float(d.get("phi_b", 0.0)),
        section_curve=d.get("section_curve", "b"),
        slenderness_case=d.get("slenderness_case", "compression_column"),
    )


DEMO = [
    {"member_id": "KZ-1", "section": {"h": 300, "b": 300, "tw": 10, "tf": 15},
     "steel": "Q355", "N": 1200, "Lx": 6000, "Ly": 6000},
    {"member_id": "KZ-2", "section": {"h": 400, "b": 400, "tw": 13, "tf": 21},
     "steel": "Q355", "N": 2400, "Lx": 7200, "Ly": 7200},
    {"member_id": "KL-1", "section": {"h": 500, "b": 200, "tw": 10, "tf": 16},
     "steel": "Q355", "Mx": 320, "V": 110},
]


def main() -> int:
    ap = argparse.ArgumentParser(description="钢结构构件校核 (GB 50017-2017)")
    ap.add_argument("--in", dest="infile", help="输入 JSON 文件（对象或数组）")
    ap.add_argument("--out", dest="outfile", help="输出 JSON 文件")
    ap.add_argument("--stdin", action="store_true", help="从标准输入读取 JSON")
    ap.add_argument("--demo", action="store_true", help="运行内置算例")
    ap.add_argument("--indent", type=int, default=2, help="JSON 缩进（0 表示紧凑）")
    a = ap.parse_args()

    if a.demo:
        data = DEMO
    elif a.stdin:
        data = json.load(sys.stdin)
    elif a.infile:
        with open(a.infile, encoding="utf-8") as fh:
            data = json.load(fh)
    else:
        ap.print_help()
        return 1

    records = data if isinstance(data, list) else [data]
    results = [check_member(build(r)) for r in records]

    indent = a.indent or None
    text = json.dumps(results if isinstance(data, list) else results[0],
                      ensure_ascii=False, indent=indent)

    if a.outfile:
        with open(a.outfile, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
        print(f"已写入 {a.outfile}", file=sys.stderr)
    else:
        print(text)

    # 汇总到 stderr，不污染 stdout 的 JSON
    n_fail = sum(1 for r in results if r["verdict"] == "FAIL")
    print(f"\n共 {len(results)} 个构件，不通过 {n_fail} 个", file=sys.stderr)
    for r in results:
        flag = "✓" if r["verdict"] == "PASS" else "✗"
        print(f"  {flag} {r['member_id']:<8} {r['section']:<22} "
              f"控制项 {r['governing_item']:<24} 应力比 {r['max_ratio']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
