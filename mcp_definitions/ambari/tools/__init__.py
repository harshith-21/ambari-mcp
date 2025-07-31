from mcp.server.fastmcp import FastMCP
from .cluster_info import register_tools as register_cluster_info_tools
from .component_management import register_tools as register_component_tools
from .config_management import register_tools as register_config_tools
from .service_checks import register_tools as register_service_check_tools

def register_tools(mcp: FastMCP):
    """Register all Ambari tools with the MCP server"""
    register_cluster_info_tools(mcp)
    register_component_tools(mcp)
    register_config_tools(mcp)
    register_service_check_tools(mcp) 