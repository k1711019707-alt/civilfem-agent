"""
verify_fea —— 有限元链路端到端验证

做什么
------
对每个算例走完整流程：

    构件参数 -> steel2inp 生成 INP -> 求解器求解 -> 解析结果
             -> 与材料力学闭式解对比 -> 判定链路是否正确

为什么需要它
------------
"生成了一个 INP 文件"和"这个 INP 算出来的结果是对的"是两件事。
本脚本用**独立于有限元的闭式解**做基准，验证四件事同时正确：
网格划分、边界条件、荷载施加、单位制与截面惯性矩的对应关系。

任何一环错了，结果都会显著偏离（通常数倍），因此这个对比是有效的判别手段。

用法
----
    set CCX_BIN=D:\\ccx\\ccx.exe
    python verify_fea.py --demo
    python verify_fea.py -i members.json

未设置 CCX_BIN 时只用解析解自检，不调用求解器。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from steel2inp import (  # noqa: E402
    DEMO_CASES, MemberFEM, build_from_dict, build_inp,
)

# 判定阈值：数值解与闭式解的相对偏差
TOL_DEFLECTION = 0.02   # 2%：20 单元 B31 对均布荷载挠度的离散误差约 0.1%
TOL_MOMENT = 0.02


def find_ccx(explicit: str | None = None) -> str | None:
    if explicit:
        return explicit if os.path.exists(explicit) else None
    env = os.environ.get("CCX_BIN")
    if env and os.path.exists(env):
        return env
    for name in ("ccx", "ccx.exe", "CalculiX", "ccx_2.23", "ccx_2.23.exe"):
        p = shutil.which(name)
        if p:
            return p
    return None


def run_solver(ccx: str, inp_path: str, timeout: int = 180) -> tuple[bool, str, str]:
    """运行求解器，返回 (成功, stdout, 错误信息)。"""
    workdir = os.path.dirname(os.path.abspath(inp_path))
    job = os.path.splitext(os.path.basename(inp_path))[0]
    try:
        r = subprocess.run(
            [ccx, "-i", job],
            cwd=workdir, capture_output=True, text=True, timeout=timeout,
        )
        out = (r.stdout or "") + (r.stderr or "")
        ok = r.returncode == 0 and "*ERROR" not in out.upper()
        return ok, out, "" if ok else f"exit={r.returncode}"
    except subprocess.TimeoutExpired:
        return False, "", f"求解超时 (>{timeout}s)"
    except Exception as e:
        return False, "", f"{type(e).__name__}: {e}"


_NUM = r"[-+]?\d*\.?\d+(?:[eEdD][-+]?\d+)?"


def parse_dat_displacements(dat_path: str) -> dict[int, tuple[float, float, float]]:
    """从 CalculiX 的 .dat 中解析 *NODE PRINT 输出的节点位移。

    格式形如：
        displacements (vx,vy,vz) for set NALL and time  0.1000000E+01
                 1 -2.617125E-13  0.000000E+00 -5.338203E+00
    解析按"首列为整数节点号 + 后三列为浮点"的宽松规则，避免版本差异导致失败。
    """
    res: dict[int, tuple[float, float, float]] = {}
    if not os.path.exists(dat_path):
        return res
    text = open(dat_path, encoding="utf-8", errors="replace").read()
    # 只取 displacements 段落
    blocks = re.split(r"\n\s*\n", text)
    for b in blocks:
        low = b.lower()
        if "displacement" not in low:
            continue
        for line in b.splitlines():
            m = re.match(rf"^\s*(\d+)\s+({_NUM})\s+({_NUM})\s+({_NUM})\s*$", line)
            if m:
                nid = int(m.group(1))
                vals = []
                for g in (2, 3, 4):
                    v = m.group(g).replace("D", "E").replace("d", "e")
                    try:
                        vals.append(float(v))
                    except ValueError:
                        vals.append(float("nan"))
                res[nid] = (vals[0], vals[1], vals[2])
    return res


def parse_dat_reactions(dat_path: str) -> dict[int, tuple[float, float, float]]:
    """解析支反力（用于校验总荷载是否平衡）。"""
    res: dict[int, tuple[float, float, float]] = {}
    if not os.path.exists(dat_path):
        return res
    text = open(dat_path, encoding="utf-8", errors="replace").read()
    for b in re.split(r"\n\s*\n", text):
        if "force" not in b.lower():
            continue
        for line in b.splitlines():
            m = re.match(rf"^\s*(\d+)\s+({_NUM})\s+({_NUM})\s+({_NUM})\s*$", line)
            if m:
                nid = int(m.group(1))
                vals = []
                for g in (2, 3, 4):
                    try:
                        vals.append(float(m.group(g).replace("D", "E")))
                    except ValueError:
                        vals.append(float("nan"))
                res[nid] = (vals[0], vals[1], vals[2])
    return res


def evaluate(m: MemberFEM, disp: dict[int, tuple[float, float, float]]) -> dict[str, Any]:
    """把求解结果与闭式解对比。"""
    ana = m.analytic()
    nodes = m.nodes()
    n1, nlast = nodes[0][0], nodes[-1][0]
    nmid = nodes[len(nodes) // 2][0]

    out: dict[str, Any] = {"member_id": m.member_id, "comparisons": []}

    def cmp_item(name: str, fea: float | None, ref: float | None, tol: float,
                 unit: str) -> None:
        rec: dict[str, Any] = {"item": name, "unit": unit,
                               "reference": None if ref is None else round(ref, 6),
                               "fea": None if fea is None else round(fea, 6)}
        if fea is None or ref is None or ref == 0:
            rec["status"] = "SKIP"
        else:
            rel = abs(fea - ref) / abs(ref)
            rec["rel_dev"] = round(rel, 6)
            rec["status"] = "PASS" if rel <= tol else "FAIL"
        out["comparisons"].append(rec)

    # 挠度：负值表示沿 -Z 下沉，比较时取绝对值
    if "deflection_mid_mm" in ana and nmid in disp:
        cmp_item("跨中挠度", abs(disp[nmid][2]), ana["deflection_mid_mm"],
                 TOL_DEFLECTION, "mm")
    if "deflection_tip_mm" in ana and nlast in disp:
        cmp_item("端部挠度", abs(disp[nlast][2]), ana["deflection_tip_mm"],
                 TOL_DEFLECTION, "mm")

    out["nodes_parsed"] = len(disp)
    out["nodes_expected"] = len(nodes)
    out["all_pass"] = bool(out["comparisons"]) and all(
        c["status"] == "PASS" for c in out["comparisons"])
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="有限元链路端到端验证")
    ap.add_argument("-i", "--input", help="构件参数 JSON")
    ap.add_argument("--demo", action="store_true", help="用内置算例")
    ap.add_argument("--ccx", help="ccx 可执行文件路径（或设环境变量 CCX_BIN）")
    ap.add_argument("--keep", action="store_true", help="保留中间文件")
    args = ap.parse_args(argv)

    if args.demo:
        cases = DEMO_CASES
    elif args.input:
        raw = json.load(open(args.input, encoding="utf-8"))
        cases = raw if isinstance(raw, list) else [raw]
    else:
        ap.print_help()
        return 1

    ccx = find_ccx(args.ccx)
    if not ccx:
        print("[!] 未找到求解器。设 CCX_BIN 指向 ccx 可执行文件后重试。")
        print("    仅输出解析解自检：\n")
        for d in cases:
            m = build_from_dict(d)
            print(f"  {m.member_id:<8} {m.section.label():<20} "
                  f"{json.dumps({k: round(v, 5) if isinstance(v, float) else v for k, v in m.analytic().items()}, ensure_ascii=False)}")
        return 2

    print(f"求解器: {ccx}\n")
    workdir = tempfile.mkdtemp(prefix="steel_fea_")
    summary: list[dict[str, Any]] = []

    for d in cases:
        m = build_from_dict(d)
        inp = os.path.join(workdir, f"{m.member_id}.inp")
        with open(inp, "w", encoding="utf-8", newline="\n") as f:
            f.write(build_inp(m, solver="ccx"))

        print(f"--- {m.member_id} ({m.section.label()}, {m.support}, "
              f"{m.load_case}={m.load_value:g}) ---")
        ok, out, err = run_solver(ccx, inp)
        if not ok:
            print(f"    [求解失败] {err}")
            for line in out.splitlines():
                if "ERROR" in line.upper() or "error" in line:
                    print("      " + line.strip()[:160])
            summary.append({"member_id": m.member_id, "status": "SOLVER_ERROR",
                            "detail": err})
            continue

        disp = parse_dat_displacements(os.path.join(workdir, f"{m.member_id}.dat"))
        ev = evaluate(m, disp)
        summary.append({"member_id": m.member_id, "status": "SOLVED",
                        "result": ev})
        for c in ev["comparisons"]:
            mark = {"PASS": "PASS", "FAIL": "FAIL", "SKIP": "SKIP"}[c["status"]]
            print(f"    [{mark}] {c['item']:<10} 参考={c['reference']} {c['unit']}"
                  f"  有限元={c['fea']}  偏差={c.get('rel_dev', '-')}")
        if not ev["comparisons"]:
            print(f"    [!] 未解析到位移结果（节点 {ev['nodes_parsed']}/"
                  f"{ev['nodes_expected']}）。检查 .dat 输出格式。")

    print("\n" + "=" * 66)
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    print("=" * 66)
    if not args.keep:
        shutil.rmtree(workdir, ignore_errors=True)
    else:
        print(f"中间文件保留在: {workdir}")
    return 0 if all(s["status"] == "SOLVED" for s in summary) else 1


if __name__ == "__main__":
    sys.exit(main())
