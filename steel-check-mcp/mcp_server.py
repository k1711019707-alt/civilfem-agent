"""钢结构校核 MCP Server —— 把校核能力暴露给任意 Agent 客户端

依赖（唯一的外部依赖）：
    pip install mcp

启动：
    python mcp_server.py

客户端配置（Claude Code / Codex / Cursor 的 mcp.json）：
    {"mcpServers": {"steel-check": {"command": "python",
      "args": ["<绝对路径>/mcp_server.py"]}}}

设计要点（这是面试的讲点，不只是代码）：
 1. 工具返回**结构化 dict**（校核值 / 限值 / 应力比 / 结论 / 规范条文号），
    而不是一段自然语言 → Agent 能基于结果继续编排、能自己判断是否要重选截面
 2. 每个工具都带 clause（条文号）→ 结论可追溯到规范原文，这是工程场景的硬要求
 3. 工具描述写清**适用边界**（如"仅双轴对称工字形""不含节点验算"），
    避免 Agent 在工具能力范围外调用
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from steelcheck import (
    CODE,
    GAMMA_X,
    GAMMA_Y,
    SLENDERNESS_LIMIT,
    STEEL_GRADES,
    IH,
    Member,
    check_member,
)

mcp = FastMCP("steel-check")


@mcp.tool()
def check_steel_member(
    member_id: str,
    h: float,
    b: float,
    tw: float,
    tf: float,
    steel: str = "Q355",
    N: float = 0.0,
    Mx: float = 0.0,
    My: float = 0.0,
    V: float = 0.0,
    Lx: float = 0.0,
    Ly: float = 0.0,
    section_curve: str = "b",
    slenderness_case: str = "compression_column",
) -> dict[str, Any]:
    """校核双轴对称工字形（H 形）钢构件，依据 GB 50017-2017。

    适用边界：仅双轴对称工字形截面、仅构件层面校核（不含节点、焊缝、螺栓、
    疲劳、抗震构造）。需要 FEA 的场合（节点应力集中、局部屈曲、滞回）不适用。

    参数：
        member_id: 构件编号，如 "KZ-1"
        h,b,tw,tf: 截面总高 / 翼缘宽 / 腹板厚 / 翼缘厚，单位 mm
        steel: 钢材牌号，可选 Q235 / Q355 / Q390 / Q420
        N: 轴力 kN（压力为正）；Mx,My: 弯矩 kN·m；V: 剪力 kN
        Lx: 绕截面 x 轴的计算长度 mm（用于绕 y 轴失稳校核）
        Ly: 绕截面 y 轴的计算长度 mm（用于绕 x 轴失稳校核）
        section_curve: 轴压稳定截面分类 a/b/c/d，需按规范表 7.2.1 判定
        slenderness_case: 长细比限值类别，可选 compression_column / compression_brace
            / tension / tension_dynamic

    返回：含 checks 列表的结构化结果，每项给出 demand（计算值）、capacity（限值）、
    ratio（应力比）、verdict（PASS/FAIL）、clause（规范条文号）。
    """
    m = Member(
        member_id=member_id,
        section=IH(h=h, b=b, tw=tw, tf=tf),
        steel=steel,
        N=N, Mx=Mx, My=My, V=V, Lx=Lx, Ly=Ly,
        section_curve=section_curve,
        slenderness_case=slenderness_case,
    )
    return check_member(m)


@mcp.tool()
def section_properties(h: float, b: float, tw: float, tf: float) -> dict[str, Any]:
    """计算双轴对称工字形（H 形）截面的几何特性。

    返回面积 A(mm²)、惯性矩 Ix/Iy(mm⁴)、截面模量 Wx/Wy(mm³)、回转半径 ix/iy(mm)。
    注意：按解析公式计算，热轧型钢因翼缘圆角会与型钢表存在 1~3% 偏差。
    """
    p = IH(h=h, b=b, tw=tw, tf=tf).props()
    return {k: round(v, 4) for k, v in p.items()}


@mcp.tool()
def list_steel_grades() -> dict[str, Any]:
    """列出本工具支持的钢材牌号及其强度设计值（GB 50017-2017 表 4.4.1，板厚≤16mm）。"""
    return {"code": CODE, "grades": STEEL_GRADES}


@mcp.resource("steel://conventions")
def conventions() -> str:
    """本工具的约定与限制说明（Agent 在规划任务前应先读）。"""
    return f"""依据规范：{CODE}

单位约定：
  - 几何尺寸 mm，力 kN，弯矩 kN·m，应力 N/mm²
  - 轴力 N 以受压为正

截面塑性发展系数：绕 x 轴 γx={GAMMA_X}，绕 y 轴 γy={GAMMA_Y}
  ⚠️ 直接承受动力荷载或需计算疲劳的构件应取 1.0，本工具不自动判定

容许长细比：{SLENDERNESS_LIMIT}

限制（超出请勿调用本工具）：
  - 仅双轴对称工字形截面，不支持箱形、圆管、角钢、T 形、非对称截面
  - 仅构件层面校核，不含节点板、焊缝、螺栓群、疲劳、抗震构造措施
  - 截面分类（a/b/c/d）需由使用者按规范表 7.2.1 判定后传入
  - 所有系数须在正式工程前对照规范原文复核
"""


if __name__ == "__main__":
    mcp.run()
