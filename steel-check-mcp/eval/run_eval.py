#!/usr/bin/env python3
"""评测脚本 —— 用独立基准值验证校核结果的可靠性

这是本项目最重要的一环，也是简历上最该量化的一句话：
「建立 N 条评测集，校核值与规范例题/手算基准的最大相对偏差 X%」。

运行：
    python eval/run_eval.py
    python eval/run_eval.py --json report.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cli import build  # noqa: E402
from steelcheck import check_member  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def rel_err(got: float, want: float) -> float:
    """相对误差；基准值接近 0 时退化为中心差分。"""
    return abs(got - want) / abs(want) if want else abs(got)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", default=os.path.join(HERE, "cases.json"))
    ap.add_argument("--json", dest="out", help="把评测报告写成 JSON")
    a = ap.parse_args()

    with open(a.cases, encoding="utf-8") as fh:
        spec = json.load(fh)
    tol = spec.get("tolerance", 0.02)

    rows, worst, n_fail = [], 0.0, 0
    print(f"{'用例':<6}{'校核项':<32}{'本条值':>12}{'基准值':>12}{'偏差':>10}  判定")
    print("-" * 82)
    for c in spec["cases"]:
        res = check_member(build(c["input"]))
        by_item = {i["item"]: i for i in res["checks"]}
        for item, exp in c["expected"].items():
            if item not in by_item:
                rows.append({"case": c["id"], "item": item, "status": "MISSING"})
                n_fail += 1
                print(f"{c['id']:<6}{item:<32}{'—':>12}{exp['demand']:>12.2f}"
                      f"{'—':>10}  MISSING")
                continue
            e = rel_err(by_item[item]["demand"], exp["demand"])
            ok = e <= tol
            n_fail += 0 if ok else 1
            worst = max(worst, e)
            rows.append({"case": c["id"], "item": item, "got": by_item[item]["demand"],
                         "want": exp["demand"], "rel_err": round(e, 5),
                         "status": "PASS" if ok else "FAIL"})
            print(f"{c['id']:<6}{item:<32}{by_item[item]['demand']:>12.2f}"
                  f"{exp['demand']:>12.2f}{e*100:>9.2f}%  {'✓' if ok else '✗'}")

        if "expect_verdict" in c:
            ok = res["verdict"] == c["expect_verdict"]
            n_fail += 0 if ok else 1
            rows.append({"case": c["id"], "item": "整体结论",
                         "got": res["verdict"], "want": c["expect_verdict"],
                         "status": "PASS" if ok else "FAIL"})
            print(f"{c['id']:<6}{'整体结论':<32}{res['verdict']:>12}{c['expect_verdict']:>12}"
                  f"{'':>10}  {'✓' if ok else '✗'}")

    print("-" * 82)
    print(f"共 {len(rows)} 条断言，不通过 {n_fail} 条，最大相对偏差 {worst*100:.3f}%"
          f"（容差 {tol*100:.1f}%）")
    if spec.get("todo"):
        print("\n待补基准：")
        for t in spec["todo"]:
            print(f"  · {t}")

    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            json.dump({"tolerance": tol, "n_assertions": len(rows),
                       "n_fail": n_fail, "max_rel_err": round(worst, 6),
                       "rows": rows}, fh, ensure_ascii=False, indent=2)
        print(f"\n报告已写入 {a.out}")
    return 1 if n_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
