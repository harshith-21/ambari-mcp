from mcp.server.fastmcp import FastMCP
from .cluster_status import register_resources as register_cluster_status_resources
from .service_configs import register_resources as register_service_config_resources
from .host_info import register_resources as register_host_info_resources

def register_resources(mcp: FastMCP):
    """Register all Ambari resources with the MCP server"""
    register_cluster_status_resources(mcp)
    register_service_config_resources(mcp)
    register_host_info_resources(mcp) 