"""CivilFEM MCP Server；无 MCP SDK 时仍可导入核心函数。"""

# 导入核心高层函数。
from civilfem.mcp_api import build_mesh, submit_simulation, get_simulation_status, get_result_summary, generate_report
from civilfem.workflow import inspect_input, extract_structural_model, validate_structural_model

# 尝试加载官方 MCP SDK，缺失时保留可测试降级模式。
try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    FastMCP = None

# 仅在 SDK 可用时创建协议服务。
mcp = FastMCP("civilfem-agent") if FastMCP else None

if mcp:
    # 注册输入检查工具。
    mcp.tool()(inspect_input)
    # 注册统一模型提取工具。
    mcp.tool()(extract_structural_model)
    # 注册模型验证工具。
    mcp.tool()(validate_structural_model)
    # 注册网格工具。
    mcp.tool()(build_mesh)
    # 注册求解提交工具。
    mcp.tool()(submit_simulation)
    # 注册状态查询工具。
    mcp.tool()(get_simulation_status)
    # 注册结果摘要工具。
    mcp.tool()(get_result_summary)
    # 注册报告工具。
    mcp.tool()(generate_report)


if __name__ == "__main__":
    # 缺少 SDK 时给出明确安装提示。
    if mcp is None:
        raise SystemExit("请在 fangzhen 环境安装 mcp 后启动 MCP Server")
    # 使用官方 SDK 启动标准输入输出传输。
    mcp.run()
