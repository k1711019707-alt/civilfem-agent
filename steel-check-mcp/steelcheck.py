"""钢结构构件校核核心 —— 依据 GB 50017-2017《钢结构设计标准》

设计原则（三条，都是为了"面试官能自己跑一遍"）：
 1. 零外部依赖（纯标准库）→ pip 装完直接运行，结果可复现
 2. 输出结构化结果（构件ID + 校核项 + 计算值 + 限值 + 应力比 + 结论 + 条文号）
    → 让 Agent 能基于结果继续编排，而不是解析一段自然语言
 3. 截面特性由尺寸解析计算，不查表 → 可处理焊接组合截面，且无数据录入错误

已知偏差：热轧型钢翼缘根部有圆角，解析公式与型钢表存在约 1~3% 偏差。
详见 README「精度说明」。

免责声明：本模块是教学/工程辅助工具，系数与截面分类须对照规范原文复核，
不得直接用于正式工程设计。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import pi, sqrt
from typing import Any

E_STEEL = 206_000.0  # 钢材弹性模量 N/mm²（GB 50017-2017 表 4.4.5）
CODE = "GB 50017-2017"

# GB 50017-2017 表 4.4.1 钢材强度设计值（板厚 ≤ 16mm 档）
# ⚠️ 系数须对照规范原文复核
STEEL_GRADES: dict[str, dict[str, float]] = {
    "Q235": {"f": 215.0, "fv": 125.0, "fy": 235.0},
    "Q355": {"f": 305.0, "fv": 175.0, "fy": 355.0},
    "Q390": {"f": 345.0, "fv": 200.0, "fy": 390.0},
    "Q420": {"f": 375.0, "fv": 215.0, "fy": 420.0},
}

# GB 50017-2017 附录 D 轴压构件稳定系数 φ 拟合参数
# ⚠️ 截面分类必须按 表 7.2.1-1 / 7.2.1-2 逐条判定，此处仅提供计算能力
PHI_PARAMS: dict[str, dict[str, float]] = {
    "a": {"a1": 0.65, "a2": 0.986, "a3": 0.152},
    "b": {"a1": 0.65, "a2": 0.965, "a3": 0.300},
    "c": {"a1": 0.73, "a2": 0.906, "a3": 0.595},
    "d": {"a1": 1.35, "a2": 0.868, "a3": 0.915},
}

# 截面塑性发展系数 γ（GB 50017-2017 表 6.1.1）
# ⚠️ 直接承受动力荷载或需计算疲劳的构件取 γ = 1.0
GAMMA_X = 1.05  # 工字形截面绕 x 轴
GAMMA_Y = 1.20  # 工字形截面绕 y 轴

# 容许长细比（GB 50017-2017 表 7.4.6，节选）
SLENDERNESS_LIMIT = {
    "compression_column": 150,  # 受压构件：柱、桁架受压杆
    "compression_brace": 200,   # 受压构件：支撑、系杆
    "tension": 350,             # 受拉构件（一般）
    "tension_dynamic": 250,     # 受拉构件（直接承受动力荷载）
}


# --------------------------------------------------------------------------
# 截面几何特性
# --------------------------------------------------------------------------
@dataclass
class IH:
    """双轴对称工字形（H 形）截面，单位 mm。焊接组合截面用解析公式精确。"""

    h: float    # 总高
    b: float    # 翼缘宽
    tw: float   # 腹板厚
    tf: float   # 翼缘厚

    def props(self) -> dict[str, float]:
        hw = self.h - 2.0 * self.tf  # 腹板计算高度
        A = 2.0 * self.b * self.tf + hw * self.tw
        Ix = (self.b * self.h**3 - (self.b - self.tw) * hw**3) / 12.0
        Iy = (2.0 * self.tf * self.b**3 + hw * self.tw**3) / 12.0
        return {
            "hw": hw,
            "A": A,                    # mm²
            "Ix": Ix,                  # mm⁴
            "Iy": Iy,                  # mm⁴
            "Wx": 2.0 * Ix / self.h,   # mm³
            "Wy": 2.0 * Iy / self.b,   # mm³
            "ix": sqrt(Ix / A),        # mm
            "iy": sqrt(Iy / A),        # mm
        }

    def label(self) -> str:
        return f"H{self.h:g}×{self.b:g}×{self.tw:g}×{self.tf:g}"


# --------------------------------------------------------------------------
# 单项校核
# --------------------------------------------------------------------------
def _verdict(ratio: float) -> str:
    return "PASS" if ratio <= 1.0 else "FAIL"


def _item(name: str, clause: str, demand: float, capacity: float,
          unit: str, note: str = "") -> dict[str, Any]:
    ratio = demand / capacity if capacity else float("inf")
    d: dict[str, Any] = {
        "item": name,
        "clause": clause,
        "demand": round(demand, 2),
        "capacity": round(capacity, 2),
        "unit": unit,
        "ratio": round(ratio, 3),
        "verdict": _verdict(ratio),
    }
    if note:
        d["note"] = note
    return d


def phi_axial(lam: float, fy: float, curve: str = "b") -> float:
    """轴压构件稳定系数 φ（GB 50017-2017 附录 D 拟合式）"""
    if curve not in PHI_PARAMS:
        raise ValueError(f"未知截面分类 {curve!r}，可选 {list(PHI_PARAMS)}")
    p = PHI_PARAMS[curve]
    lam_n = (lam / pi) * sqrt(fy / E_STEEL)  # 正则化长细比
    if lam_n <= 0.215:
        return 1.0 - p["a1"] * lam_n**2
    t = p["a2"] + p["a3"] * lam_n + lam_n**2
    return (t - sqrt(t**2 - 4.0 * lam_n**2)) / (2.0 * lam_n**2)


# --------------------------------------------------------------------------
# 构件校核（受弯 / 轴压）
# --------------------------------------------------------------------------
@dataclass
class Member:
    member_id: str
    section: IH
    steel: str = "Q355"
    # 内力（kN、kN·m）
    Mx: float = 0.0
    My: float = 0.0
    V: float = 0.0
    N: float = 0.0
    # 几何
    Lx: float = 0.0   # 计算长度 mm（绕 x 轴，用于绕 y 轴失稳）
    Ly: float = 0.0   # 计算长度 mm（绕 y 轴，用于绕 x 轴失稳）
    phi_b: float = 0.0        # 整体稳定系数，0 表示本次不校核
    section_curve: str = "b"  # 轴压稳定截面分类
    slenderness_case: str = "compression_column"


def check_member(m: Member) -> dict[str, Any]:
    """执行校核，返回结构化结果。"""
    if m.steel not in STEEL_GRADES:
        raise ValueError(f"未知钢材牌号 {m.steel!r}，可选 {list(STEEL_GRADES)}")
    g = STEEL_GRADES[m.steel]
    f, fv, fy = g["f"], g["fv"], g["fy"]
    p = m.section.props()
    items: list[dict[str, Any]] = []

    # 6.1.1 抗弯强度（N·mm → N/mm²）
    if m.Mx or m.My:
        sig_b = (m.Mx * 1e6) / (GAMMA_X * p["Wx"]) + (m.My * 1e6) / (GAMMA_Y * p["Wy"])
        items.append(_item("bending_strength", "6.1.1", sig_b, f, "N/mm²"))

    # 6.1.3 抗剪强度（工字形截面近似取腹板平均剪应力）
    if m.V:
        tau = (m.V * 1e3) / (p["hw"] * m.section.tw)
        items.append(_item("shear_strength", "6.1.3", tau, fv, "N/mm²",
                           note="按 τ=V/(hw·tw) 近似"))

    # 7.2.1 轴心受压整体稳定
    if m.N:
        # 绕 y 轴失稳用 iy（对应计算长度 Lx），绕 x 轴失稳用 ix（对应 Ly），取不利者
        lam_x = m.Ly / p["ix"] if m.Ly else 0.0
        lam_y = m.Lx / p["iy"] if m.Lx else 0.0
        lam = max(lam_x, lam_y)
        phi = phi_axial(lam, fy, m.section_curve) if lam else 1.0
        sig_c = (m.N * 1e3) / (phi * p["A"]) if phi else float("inf")
        items.append(_item("axial_stability", "7.2.1", sig_c, f, "N/mm²",
                           note=f"λ={lam:.1f}, φ={phi:.4f}, {m.section_curve} 类截面"))
        # 7.4.6 容许长细比
        limit = SLENDERNESS_LIMIT.get(m.slenderness_case)
        if limit:
            items.append(_item("slenderness", "7.4.6", lam, float(limit), "-",
                               note=m.slenderness_case))

    # 6.2.2 受弯构件整体稳定
    if m.Mx and m.phi_b:
        sig_buck = (m.Mx * 1e6) / (m.phi_b * p["Wx"])
        items.append(_item("lateral_torsional_buckling", "6.2.2", sig_buck, f, "N/mm²",
                           note=f"φb={m.phi_b:.4f}"))

    governing = max(items, key=lambda x: x["ratio"]) if items else None
    return {
        "member_id": m.member_id,
        "code": CODE,
        "section": m.section.label(),
        "steel": m.steel,
        "section_props": {k: round(v, 4) for k, v in p.items()},
        "checks": items,
        "governing_item": governing["item"] if governing else None,
        "max_ratio": governing["ratio"] if governing else None,
        "verdict": "PASS" if all(i["verdict"] == "PASS" for i in items) else "FAIL",
    }


# --------------------------------------------------------------------------
# 演示
# --------------------------------------------------------------------------
if __name__ == "__main__":
    import json

    sec = IH(h=300, b=300, tw=10, tf=15)
    print("=== 截面几何特性（解析计算）===")
    for k, v in sec.props().items():
        print(f"  {k:>4} = {v:,.2f}")

    print("\n=== 焊接组合截面 vs 热轧型钢表（HW300×300×10×15 / Q355）===")
    p = sec.props()
    table = {"A": 11980.0, "Ix": 2.04e8, "Iy": 6.75e7, "Wx": 1.36e6}
    for k, ref in table.items():
        print(f"  {k:>4}: 解析 {p[k]:>14,.2f} | 型钢表 {ref:>14,.2f} | 偏差 {(p[k]/ref-1)*100:+.2f}%")

    print("\n=== 轴压柱校核（N=1200kN, L0=6000mm）===")
    col = Member(member_id="KZ-1", section=sec, steel="Q355",
                 N=1200.0, Lx=6000.0, Ly=6000.0)
    print(json.dumps(check_member(col), ensure_ascii=False, indent=2))

    print("\n=== 受弯梁校核（Mx=150kN·m, V=80kN）===")
    beam = Member(member_id="KL-1", section=sec, steel="Q355",
                  Mx=150.0, V=80.0)
    r = check_member(beam)
    print(json.dumps({k: r[k] for k in ("member_id", "checks", "governing_item",
                                        "max_ratio", "verdict")},
                     ensure_ascii=False, indent=2))
