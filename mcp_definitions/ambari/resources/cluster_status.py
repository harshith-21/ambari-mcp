from typing import Any
import httpx
import json
from mcp.server.fastmcp import FastMCP

def register_resources(mcp: FastMCP):
    """Register cluster status resources with the MCP server"""
    
    @mcp.resource("ambari://cluster-overview/{cluster_name}")
    async def get_cluster_overview(cluster_name: str) -> str:
        """Get comprehensive cluster overview including services, hosts, and alerts.
        
        Args:
            cluster_name: Name of the cluster
        """
        # For now, return a simple response since we need server connection details
        # In a real implementation, these would be passed via context or configuration
        return json.dumps({
            "cluster_name": cluster_name,
            "status": "This resource requires server connection details",
            "note": "Use the tools instead for full functionality with server_url, username, password parameters"
        }, indent=2)
    
    @mcp.resource("ambari://service-status/{cluster_name}/{service_name}")
    async def get_service_status_resource(cluster_name: str, service_name: str) -> str:
        """Get detailed service status including components and configuration.
        
        Args:
            cluster_name: Name of the cluster
            service_name: Name of the service
        """
        return json.dumps({
            "cluster_name": cluster_name,
            "service_name": service_name,
            "status": "This resource requires server connection details",
            "note": "Use the get_service_health tool instead for full functionality with server connection parameters"
        }, indent=2)
    
    @mcp.resource("ambari://host-details/{cluster_name}/{host_name}")
    async def get_host_details_resource(cluster_name: str, host_name: str) -> str:
        """Get detailed host information including components and metrics.
        
        Args:
            cluster_name: Name of the cluster
            host_name: Name of the host
        """
        return json.dumps({
            "cluster_name": cluster_name,
            "host_name": host_name,
            "status": "This resource requires server connection details",
            "note": "Use the get_host_health tool instead for full functionality with server connection parameters"
        }, indent=2) 