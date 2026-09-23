"""
steel2inp —— 钢结构构件参数 → Abaqus / CalculiX INP 文件生成器

用途
----
把一根构件的参数（截面、材质、支座、荷载）直接编译成有限元输入文件，
跳过"几何建模 → 网格划分 → 边界条件设置"三步人工操作。

设计立场
--------
1. 输入格式与 steelcheck.py 完全一致 —— 同一份构件参数，两条独立求解路径：
     规范公式（GB 50017）  vs  有限元（Abaqus / CalculiX）
   两条路径的偏差本身就是一个可量化指标（双算复核，设计院实际存在的流程）。
2. 零第三方依赖（仅标准库）。生成的是纯文本 INP，不依赖任何 Abaqus Python 环境，
   因此可以在没有 commercial license 的机器上生成、校验、版本管理。
3. 单位制统一：mm / N / MPa，质量单位 t。密度 7.85e-9 t/mm³。
   ⚠️ 单位不统一是有限元最常见的错误来源，本文件所有输出均按此单位制。

能力边界（诚实声明）
--------------------
* 本模块生成的是 **梁单元（B31）** 模型，用于构件层面的整体验算：
  强度、刚度（挠度）、稳定（线性屈曲）。
* **不能**用于局部应力集中分析（节点域、相贯节点、焊缝细节）——
  那些需要壳单元或实体单元，本模块不覆盖。
* 生成的 INP 语法经 CalculiX 2.23 实测（见 README「验证记录」）；
  Abaqus 侧未实测，落地前需自行确认版本兼容性。
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from dataclasses import dataclass, field
from typing import Any

# --------------------------------------------------------------------------
# 材料常数
# --------------------------------------------------------------------------
E_STEEL = 206_000.0        # 弹性模量 N/mm²（GB 50017-2017 表 4.4.5）
NU_STEEL = 0.3             # 泊松比
RHO_STEEL = 7.85e-9        # 密度 t/mm³（= 7850 kg/m³）

# 钢材牌号 → 屈服强度 fy（用于线性屈曲参考应力，N/mm²）
FY: dict[str, float] = {
    "Q235": 235.0,
    "Q355": 355.0,
    "Q390": 390.0,
    "Q420": 420.0,
}


# --------------------------------------------------------------------------
# 截面几何特性（与 steelcheck.py 的 IH.props() 用同一组解析式）
# --------------------------------------------------------------------------
@dataclass
class HSection:
    """双轴对称 H 形截面，单位 mm。"""

    h: float
    b: float
    tw: float
    tf: float

    def props(self) -> dict[str, float]:
        hw = self.h - 2.0 * self.tf
        A = 2.0 * self.b * self.tf + hw * self.tw
        Ix = (self.b * self.h**3 - (self.b - self.tw) * hw**3) / 12.0
        Iy = (2.0 * self.tf * self.b**3 + hw * self.tw**3) / 12.0
        # 开口薄壁截面扭转常数（GB 50017-2017 附录 A / 薄壁杆件理论）
        J = (2.0 * self.b * self.tf**3 + hw * self.tw**3) / 3.0
        return {
            "hw": hw,
            "A": A,          # mm²
            "Ix": Ix,        # mm⁴  强轴（腹板平面内弯曲）
            "Iy": Iy,        # mm⁴  弱轴
            "J": J,          # mm⁴  扭转常数
            "Wx": 2.0 * Ix / self.h,
            "Wy": 2.0 * Iy / self.b,
        }

    def label(self) -> str:
        return f"H{self.h:g}x{self.b:g}x{self.tw:g}x{self.tf:g}"

    def section_points(self) -> list[tuple[float, float]]:
        """梁截面输出点，局部坐标 (n, m)。

        构件轴向沿全局 X 时，Abaqus/CalculiX 的梁局部 1 轴落在全局 Z 方向
        （竖直），局部 2 轴落在全局 Y 方向。故 n 对应截面高度方向，
        m 对应截面宽度方向。
        """
        return [
            (self.h / 2.0, -self.b / 2.0),   # 上翼缘左端
            (self.h / 2.0, self.b / 2.0),    # 上翼缘右端
            (0.0, 0.0),                      # 腹板中点
            (-self.h / 2.0, -self.b / 2.0),  # 下翼缘左端
            (-self.h / 2.0, self.b / 2.0),   # 下翼缘右端
        ]


# --------------------------------------------------------------------------
# 支座
# --------------------------------------------------------------------------
# Abaqus/CalculiX 自由度编号：1=Ux 2=Uy 3=Uz 4=URx 5=URy 6=URz
SUPPORTS: dict[str, dict[str, Any]] = {
    "simple": {
        "desc": "简支（一端铰支 + 一端滚动）",
        "start": [1, 2, 3],          # 固定平动
        "start_extra": [4],          # 约束绕自身轴扭转，消除奇异
        "end": [2, 3],               # 仅约束竖向与侧向
        "end_extra": [4],
        "analytic": "简支",
    },
    "cantilever": {
        "desc": "悬臂（一端固接 + 一端自由）",
        "start": [1, 2, 3, 4, 5, 6],
        "start_extra": [],
        "end": [],
        "end_extra": [],
        "analytic": "悬臂",
    },
    "fixed": {
        "desc": "两端固接",
        "start": [1, 2, 3, 4, 5, 6],
        "start_extra": [],
        "end": [2, 3, 5, 6],         # 固接但允许轴向变形，避免轴向约束冗余
        "end_extra": [4],
        "analytic": "两端固接",
    },
}

LOADS: dict[str, str] = {
    "udl": "沿全长均布荷载 q（N/mm，竖向 -Z）",
    "point_center": "跨中集中力 P（N，竖向 -Z）",
    "axial": "轴力 N（N，压为负 / 拉为正，沿构件轴向）",
}


# --------------------------------------------------------------------------
# 构件定义
# --------------------------------------------------------------------------
@dataclass
class MemberFEM:
    """有限元模型定义。"""

    member_id: str
    section: HSection
    steel: str
    length: float                 # mm
    support: str = "simple"
    load_case: str = "udl"
    load_value: float = 0.0       # N/mm 或 N
    mesh_div: int = 20            # 沿长度单元数
    with_section_points: bool = False

    def props(self) -> dict[str, float]:
        return self.section.props()

    # ---- 解析解（用于自检与双算对比）------------------------------------
    def analytic(self) -> dict[str, Any]:
        """返回该工况下材料力学的理论解，作为 FEA 结果的校验基准。

        这些是教科书级闭式解，作用是**验证有限元链路正确性**，
        不是工程验算结果（工程验算由 steelcheck.py 按 GB 50017 给出）。
        """
        p = self.props()
        E, L = E_STEEL, self.length
        # 竖向弯曲由强轴惯性矩控制
        EI = E * p["Ix"]
        out: dict[str, Any] = {"EI_Nmm2": EI, "support": self.support,
                               "load_case": self.load_case}

        if self.load_case == "udl":
            q = self.load_value
            if self.support == "simple":
                out["deflection_mid_mm"] = 5.0 * q * L**4 / (384.0 * EI)
                out["moment_mid_Nmm"] = q * L**2 / 8.0
            elif self.support == "fixed":
                out["deflection_mid_mm"] = q * L**4 / (384.0 * EI)
                out["moment_end_Nmm"] = -q * L**2 / 12.0
                out["moment_mid_Nmm"] = q * L**2 / 24.0
            elif self.support == "cantilever":
                out["deflection_tip_mm"] = q * L**4 / (8.0 * EI)
                out["moment_fix_Nmm"] = -q * L**2 / 2.0
            out["total_load_N"] = q * L

        elif self.load_case == "point_center":
            Pp = self.load_value
            if self.support == "simple":
                out["deflection_mid_mm"] = Pp * L**3 / (48.0 * EI)
                out["moment_mid_Nmm"] = Pp * L / 4.0
            elif self.support == "fixed":
                out["deflection_mid_mm"] = Pp * L**3 / (192.0 * EI)
                out["moment_end_Nmm"] = -Pp * L / 8.0
                out["moment_mid_Nmm"] = Pp * L / 8.0
            elif self.support == "cantilever":
                out["deflection_tip_mm"] = Pp * L**3 / (3.0 * EI)
                out["moment_fix_Nmm"] = -Pp * L

        return out

    # ---- 分析 → 验算的桥梁 ----------------------------------------------
    def internal_forces(self) -> dict[str, float]:
        """由荷载推设计内力，字段与 steelcheck.Member 对齐（kN / kN·m）。

        这一步的意义：steelcheck 需要「已知内力」才能验算，而设计人员手上
        通常只有「荷载」。本方法把荷载转成内力，使 Agent 只需提供荷载即可
        端到端跑完规范校核，无需人工先算一遍内力。

        ⚠️ 仅覆盖本模块支持的静定/简单超静定工况。多跨连续梁、框架等的
        内力需由整体分析给出——那正是有限元路径存在的理由。
        """
        L, q, P = self.length, self.load_value, self.load_value
        M = V = N = 0.0
        if self.load_case == "udl":
            if self.support == "simple":
                M, V = q * L**2 / 8.0, q * L / 2.0
            elif self.support == "fixed":
                M, V = q * L**2 / 12.0, q * L / 2.0   # 端部控制弯矩
            elif self.support == "cantilever":
                M, V = q * L**2 / 2.0, q * L
        elif self.load_case == "point_center":
            if self.support == "simple":
                M, V = P * L / 4.0, P / 2.0
            elif self.support == "fixed":
                M, V = P * L / 8.0, P / 2.0
            elif self.support == "cantilever":
                M, V = P * L, P
        elif self.load_case == "axial":
            N = P
        # N·mm -> kN·m ; N -> kN
        return {"Mx": M / 1e6, "My": 0.0, "V": V / 1e3, "N": N / 1e3}

    # ---- 网格 ----------------------------------------------------------
    def nodes(self) -> list[tuple[int, float]]:
        """沿 X 轴均匀布点，返回 [(节点号, x坐标)]，节点号从 1 开始。"""
        n = self.mesh_div + 1
        step = self.length / self.mesh_div
        return [(i + 1, i * step) for i in range(n)]

    def elements(self) -> list[tuple[int, int, int]]:
        """B31 单元连接。"""
        n = len(self.nodes())
        return [(i + 1, i + 1, i + 2) for i in range(n - 1)]


# --------------------------------------------------------------------------
# INP 生成
# --------------------------------------------------------------------------
def _fmt(v: float) -> str:
    """数值格式化：尽量保留有效精度，避免科学计数法造成的可读性问题。"""
    if v == 0:
        return "0."
    av = abs(v)
    if av >= 1e5 or av < 1e-3:
        return f"{v:.6e}"
    return f"{v:.6f}".rstrip("0").rstrip(".") or "0."


def build_inp(m: MemberFEM, solver: str = "abaqus") -> str:
    """生成 INP。

    solver="abaqus"  用 *BEAM GENERAL SECTION（Abaqus 原生关键字）
    solver="ccx"     用 *BEAM SECTION, SECTION=GENERAL（CalculiX 关键字）
                     —— 这两个关键字**不通用**，是实测确认的约束，见 README。
    """
    if solver not in ("abaqus", "ccx"):
        raise ValueError(f"unknown solver: {solver}")
    p = m.props()
    fy = FY.get(m.steel.upper(), 355.0)
    sup = SUPPORTS[m.support]
    L = []
    a = L.append

    # ---------------- 头部 ----------------
    a(f"*HEADING")
    a(f"steel2inp | member={m.member_id} | section={m.section.label()}"
      f" | steel={m.steel} | L={m.length:g}mm | solver={solver}")
    a(f"** support={sup['desc']} | load={m.load_case}={m.load_value:g}"
      f" | units: mm-N-MPa (mass: t)")
    a(f"** section props  A={p['A']:.4e} mm2  Ix={p['Ix']:.4e} mm4"
      f"  Iy={p['Iy']:.4e} mm4  J={p['J']:.4e} mm4")
    a("**")

    # ---------------- 节点 ----------------
    a("*NODE")
    for nid, x in m.nodes():
        a(f"{nid}, {_fmt(x)}, 0., 0.")
    a("**")

    # ---------------- 单元 ----------------
    a("*ELEMENT, TYPE=B31, ELSET=ALL")
    for eid, n1, n2 in m.elements():
        a(f"{eid}, {n1}, {n2}")
    a("**")

    # 节点/单元集合，供边界条件与结果输出引用
    nodes = m.nodes()
    a("*NSET, NSET=NALL, GENERATE")
    a(f"{nodes[0][0]}, {nodes[-1][0]}, 1")
    a("*NSET, NSET=NSTART")
    a(f"{nodes[0][0]},")
    a("*NSET, NSET=NEND")
    a(f"{nodes[-1][0]},")
    if m.load_case == "point_center":
        a("*NSET, NSET=NMID")
        a(f"{nodes[len(nodes) // 2][0]},")
    if m.load_case == "udl":
        a("*ELSET, ELSET=EALL, GENERATE")
        a(f"{m.elements()[0][0]}, {m.elements()[-1][0]}, 1")
    a("**")

    # ---------------- 截面 ----------------
    # 数据行统一为：A, I11, I12, I22, J（mm / mm⁴）
    # 构件轴向沿全局 X，竖向荷载作用下弯曲发生在竖直平面内，
    # 故截面局部 1 轴取竖直方向：I11 = Ix（强轴），I22 = Iy（弱轴）。
    props_line = (f"{_fmt(p['A'])}, {_fmt(p['Ix'])}, 0., "
                  f"{_fmt(p['Iy'])}, {_fmt(p['J'])}")
    # 方向矢量：截面局部 1 轴指向全局 -Z（竖直向下）
    DIR_VEC = "0., 0., -1."

    if solver == "ccx":
        # CalculiX：*BEAM SECTION + SECTION=GENERAL
        # 第 1 行数据 = 截面特性；第 2 行 = 局部 1 轴方向矢量（3 个分量）
        # 依据：calculix/examples B31.inp、Krande/adapy u1general.inp
        a("*BEAM SECTION, ELSET=ALL, MATERIAL=STEEL, SECTION=GENERAL")
        a(props_line)
        a(DIR_VEC)
    else:
        # Abaqus：*BEAM GENERAL SECTION + SECTION=GENERAL
        a("*BEAM GENERAL SECTION, ELSET=ALL, SECTION=GENERAL, MATERIAL=STEEL")
        a(props_line)
        if m.with_section_points:
            pts = m.section.section_points()
            flat: list[str] = []
            for n_, m_ in pts:
                flat += [_fmt(n_), _fmt(m_)]
            for i in range(0, len(flat), 4):
                a(", ".join(flat[i:i + 4]))
    a("**")

    # ---------------- 材料 ----------------
    a("*MATERIAL, NAME=STEEL")
    a("*ELASTIC")
    a(f"{_fmt(E_STEEL)}, {NU_STEEL}")
    a("*DENSITY")
    a(f"{_fmt(RHO_STEEL)}")
    a("**")

    # ---------------- 边界条件 ----------------
    a("*BOUNDARY")
    for dof in sup["start"] + sup["start_extra"]:
        a(f"NSTART, {dof}, {dof}, 0.")
    if sup["end"] or sup["end_extra"]:
        for dof in sup["end"] + sup["end_extra"]:
            a(f"NEND, {dof}, {dof}, 0.")
    a("**")

    # ---------------- 分析步 ----------------
    a("*STEP, NLGEOM=NO")
    a("*STATIC")
    a("1., 1., 1e-05, 1.")
    a("**")

    if m.load_case == "udl":
        # CalculiX/Abaqus 均支持 Px 型分布荷载（单位长度力）
        a("** 均布荷载：P3 表示沿单元局部 3 方向（此处为全局 -Z）的线荷载")
        a("*DLOAD")
        a(f"EALL, P3, {_fmt(-m.load_value)}")
    elif m.load_case == "point_center":
        a("** 跨中集中力，沿全局 -Z")
        a("*CLOAD")
        a(f"NMID, 3, {_fmt(-m.load_value)}")
    elif m.load_case == "axial":
        a("** 端部轴力，沿 +X（正值受拉，负值受压）")
        a("*CLOAD")
        a(f"NEND, 1, {_fmt(m.load_value)}")
    a("**")

    # ---------------- 输出 ----------------
    if solver == "ccx":
        # CalculiX：*NODE PRINT 把结果写进 .dat（纯文本，可直接被脚本解析比对）
        a("*NODE PRINT, NSET=NALL")
        a("U, RF")
        a("*EL PRINT, ELSET=ALL")
        a("S")
    # *NODE FILE / *EL FILE 两个求解器都认（Abaqus 写 .fil，CalculiX 写 .frd）
    a("*NODE FILE")
    a("U, RF")
    a("*EL FILE")
    a("S")
    a("*END STEP")
    a(f"** 参考屈服强度 fy = {fy:g} N/mm2（{m.steel.upper()}）")
    a("")
    return "\n".join(L)


# --------------------------------------------------------------------------
# 自检：把解析解与实际求解结果对比（由外部求解器产出后回填）
# --------------------------------------------------------------------------
def selfcheck_analytic(m: MemberFEM) -> dict[str, Any]:
    """输出该工况的理论解，供与 FEA 结果比对。

    这是本项目「双算」能力的第一半：规范公式路径由 steelcheck.py 给出，
    有限元路径由本模块 + 求解器给出，理论解用于确认有限元链路本身没搭错。
    """
    return {
        "member_id": m.member_id,
        "section": m.section.label(),
        "props": {k: round(v, 6) for k, v in m.props().items()},
        "analytic": {k: (round(v, 6) if isinstance(v, float) else v)
                     for k, v in m.analytic().items()},
    }


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def dual_report(m: MemberFEM) -> dict[str, Any]:
    """双算复核：同一份构件参数，走两条互相独立的路径。

    路径 A —— 规范公式（steelcheck.py，按 GB 50017 给应力比与判定）
    路径 B —— 有限元（本模块生成 INP，由 Abaqus / CalculiX 给出位移与内力）

    两条路径的偏差本身是可量化指标；解析解作为第三条参照，
    用于确认有限元模型本身没搭错（网格、边界、荷载、单位制）。
    """
    f = m.internal_forces()
    rep: dict[str, Any] = {
        "member_id": m.member_id,
        "section": m.section.label(),
        "steel": m.steel,
        "length_mm": m.length,
        "support": m.support,
        "load": {"case": m.load_case, "value": m.load_value},
        "internal_forces_from_load": {k: round(v, 4) for k, v in f.items()},
        "analytic_reference": {
            k: (round(v, 6) if isinstance(v, float) else v)
            for k, v in m.analytic().items()},
    }
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from steelcheck import IH, Member, check_member  # type: ignore
        sec = IH(h=m.section.h, b=m.section.b, tw=m.section.tw, tf=m.section.tf)
        mem = Member(member_id=m.member_id, section=sec, steel=m.steel,
                     Mx=f["Mx"], My=f["My"], V=f["V"], N=f["N"],
                     Lx=m.length, Ly=m.length)
        rep["code_check"] = check_member(mem)
    except Exception as e:  # 保持模块独立可用，校核缺失不阻断 INP 生成
        rep["code_check_error"] = f"{type(e).__name__}: {e}"
    return rep


def build_from_dict(d: dict[str, Any]) -> MemberFEM:
    sec = d["section"]
    return MemberFEM(
        member_id=d.get("member_id", "M-1"),
        section=HSection(h=float(sec["h"]), b=float(sec["b"]),
                         tw=float(sec["tw"]), tf=float(sec["tf"])),
        steel=d.get("steel", "Q355"),
        length=float(d["length"]),
        support=d.get("support", "simple"),
        load_case=d.get("load_case", "udl"),
        load_value=float(d.get("load_value", 0.0)),
        mesh_div=int(d.get("mesh_div", 20)),
        with_section_points=bool(d.get("with_section_points", False)),
    )


DEMO_CASES: list[dict[str, Any]] = [
    {
        "member_id": "KL-1",
        "section": {"h": 500, "b": 200, "tw": 10, "tf": 16},
        "steel": "Q355", "length": 6000, "mesh_div": 20,
        "support": "simple", "load_case": "udl", "load_value": 30.0,
    },
    {
        "member_id": "KZ-1",
        "section": {"h": 300, "b": 300, "tw": 10, "tf": 15},
        "steel": "Q355", "length": 4000, "mesh_div": 16,
        "support": "cantilever", "load_case": "point_center", "load_value": 50000.0,
    },
]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="钢结构构件参数 → Abaqus / CalculiX INP 文件")
    ap.add_argument("-i", "--input", help="构件参数 JSON 文件（单构件或数组）")
    ap.add_argument("-o", "--outdir", default="inp_out", help="输出目录")
    ap.add_argument("--demo", action="store_true", help="用内置算例演示")
    ap.add_argument("--section-points", action="store_true",
                    help="输出截面点（用于截面应力分布，会略增文件体积）")
    ap.add_argument("--solver", choices=["abaqus", "ccx"], default="abaqus",
                    help="目标求解器：abaqus（默认）或 ccx（CalculiX）")
    ap.add_argument("--check", action="store_true",
                    help="只输出解析解自检信息，不写文件")
    args = ap.parse_args(argv)

    if args.demo:
        cases = DEMO_CASES
    elif args.input:
        raw = json.load(open(args.input, encoding="utf-8"))
        cases = raw if isinstance(raw, list) else [raw]
    else:
        ap.print_help()
        return 1

    outdir = args.outdir if args.solver == "abaqus" else f"{args.outdir}_ccx"
    if not args.check:
        os.makedirs(outdir, exist_ok=True)
    report = []
    for d in cases:
        m = build_from_dict(d)
        m.with_section_points = args.section_points or m.with_section_points
        chk = selfcheck_analytic(m)
        report.append(chk)
        if args.check:
            continue
        text = build_inp(m, solver=args.solver)
        path = os.path.join(outdir, f"{m.member_id}.inp")
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        print(f"[OK] {m.member_id:<8} {m.section.label():<22} -> {path}"
              f"  ({len(text)} chars)")
    print()
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
