from mcp.server.fastmcp import FastMCP
from .troubleshooting import register_prompts as register_troubleshooting_prompts
# Import other prompt modules as they're created
# from .deployment import register_prompts as register_deployment_prompts
# from .maintenance import register_prompts as register_maintenance_prompts

def register_prompts(mcp: FastMCP):
    """Register all Ambari prompts with the MCP server"""
    register_troubleshooting_prompts(mcp)
    # Register other prompt modules as they're created
    # register_deployment_prompts(mcp)
    # register_maintenance_prompts(mcp) 