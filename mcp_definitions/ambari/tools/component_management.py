from typing import Any, List, Dict, Optional
import httpx
from mcp.server.fastmcp import FastMCP

def register_tools(mcp: FastMCP):
    """Register component management tools with the MCP server"""
    
    @mcp.tool()
    async def start_service(server_url: str, cluster_name: str, service_name: str, 
                           username: str = "admin", password: str = "admin", port: str = "8080") -> str:
        """Start a specific service in the cluster.

        Args:
            server_url: The URL of the Ambari server
            cluster_name: Name of the cluster
            service_name: Name of the service to start (e.g., HDFS, YARN, HIVE)
            username: Username for authentication
            password: Password for authentication
            port: Port of the Ambari server
        """
        async with httpx.AsyncClient() as client:
            url = f"{server_url}:{port}/api/v1/clusters/{cluster_name}/services/{service_name}"
            payload = {
                "RequestInfo": {"context": f"Start {service_name} via MCP"},
                "Body": {"ServiceInfo": {"state": "STARTED"}}
            }
            response = await client.put(
                url, 
                json=payload, 
                auth=(username, password),
                headers={"X-Requested-By": "ambari-mcp"}
            )
            return f"Start request for {service_name} submitted. Request ID: {response.json().get('Requests', {}).get('id', 'Unknown')}"

    @mcp.tool()
    async def stop_service(server_url: str, cluster_name: str, service_name: str,
                          username: str = "admin", password: str = "admin", port: str = "8080") -> str:
        """Stop a specific service in the cluster.

        Args:
            server_url: The URL of the Ambari server
            cluster_name: Name of the cluster
            service_name: Name of the service to stop (e.g., HDFS, YARN, HIVE)
            username: Username for authentication
            password: Password for authentication
            port: Port of the Ambari server
        """
        async with httpx.AsyncClient() as client:
            url = f"{server_url}:{port}/api/v1/clusters/{cluster_name}/services/{service_name}"
            payload = {
                "RequestInfo": {"context": f"Stop {service_name} via MCP"},
                "Body": {"ServiceInfo": {"state": "INSTALLED"}}
            }
            response = await client.put(
                url, 
                json=payload, 
                auth=(username, password),
                headers={"X-Requested-By": "ambari-mcp"}
            )
            return f"Stop request for {service_name} submitted. Request ID: {response.json().get('Requests', {}).get('id', 'Unknown')}"

    @mcp.tool()
    async def restart_service(server_url: str, cluster_name: str, service_name: str,
                             username: str = "admin", password: str = "admin", port: str = "8080") -> str:
        """Restart a specific service in the cluster (single operation).

        Args:
            server_url: The URL of the Ambari server
            cluster_name: Name of the cluster
            service_name: Name of the service to restart (e.g., HDFS, YARN, HIVE)
            username: Username for authentication
            password: Password for authentication
            port: Port of the Ambari server
        """
        async with httpx.AsyncClient() as client:
            # First get all components for the service
            components_url = f"{server_url}:{port}/api/v1/clusters/{cluster_name}/services/{service_name}/components"
            components_response = await client.get(
                components_url,
                auth=(username, password),
                headers={"X-Requested-By": "ambari-mcp"}
            )
            
            components = components_response.json().get("items", [])
            resource_filters = []
            
            for component in components:
                component_name = component["ServiceComponentInfo"]["component_name"]
                # Get hosts for this component
                hosts_url = f"{server_url}:{port}/api/v1/clusters/{cluster_name}/services/{service_name}/components/{component_name}"
                hosts_response = await client.get(
                    hosts_url + "?fields=host_components/HostRoles/host_name",
                    auth=(username, password),
                    headers={"X-Requested-By": "ambari-mcp"}
                )
                
                host_components = hosts_response.json().get("host_components", [])
                for host_component in host_components:
                    host_name = host_component["HostRoles"]["host_name"]
                    resource_filters.append({
                        "service_name": service_name,
                        "component_name": component_name,
                        "hosts": host_name
                    })
            
            # Execute restart command
            restart_url = f"{server_url}:{port}/api/v1/clusters/{cluster_name}/requests"
            payload = {
                "RequestInfo": {
                    "command": "RESTART",
                    "context": f"Restart {service_name} via MCP",
                    "operation_level": {"level": "SERVICE", "cluster_name": cluster_name}
                },
                "Requests/resource_filters": resource_filters
            }
            
            response = await client.post(
                restart_url,
                json=payload,
                auth=(username, password),
                headers={"X-Requested-By": "ambari-mcp"}
            )
            
            return f"Restart request for {service_name} submitted. Request ID: {response.json().get('Requests', {}).get('id', 'Unknown')}"

    @mcp.tool()
    async def restart_component(server_url: str, cluster_name: str, service_name: str, 
                              component_name: str, host_name: str,
                              username: str = "admin", password: str = "admin", port: str = "8080") -> str:
        """Restart a specific component on a specific host.

        Args:
            server_url: The URL of the Ambari server
            cluster_name: Name of the cluster
            service_name: Name of the service (e.g., HDFS, YARN)
            component_name: Name of the component (e.g., DATANODE, NODEMANAGER)
            host_name: FQDN of the host
            username: Username for authentication
            password: Password for authentication
            port: Port of the Ambari server
        """
        async with httpx.AsyncClient() as client:
            url = f"{server_url}:{port}/api/v1/clusters/{cluster_name}/requests"
            payload = {
                "RequestInfo": {
                    "command": "RESTART",
                    "context": f"Restart {component_name} on {host_name} via MCP",
                    "operation_level": {"level": "HOST_COMPONENT", "cluster_name": cluster_name}
                },
                "Requests/resource_filters": [{
                    "service_name": service_name,
                    "component_name": component_name,
                    "hosts": host_name
                }]
            }
            
            response = await client.post(
                url,
                json=payload,
                auth=(username, password),
                headers={"X-Requested-By": "ambari-mcp"}
            )
            
            return f"Restart request for {component_name} on {host_name} submitted. Request ID: {response.json().get('Requests', {}).get('id', 'Unknown')}"

    @mcp.tool()
    async def start_component(server_url: str, cluster_name: str, host_name: str, 
                             component_name: str,
                             username: str = "admin", password: str = "admin", port: str = "8080") -> str:
        """Start a specific component on a host.

        Args:
            server_url: The URL of the Ambari server
            cluster_name: Name of the cluster
            host_name: FQDN of the host
            component_name: Name of the component to start
            username: Username for authentication
            password: Password for authentication
            port: Port of the Ambari server
        """
        async with httpx.AsyncClient() as client:
            url = f"{server_url}:{port}/api/v1/clusters/{cluster_name}/hosts/{host_name}/host_components/{component_name}"
            payload = {"HostRoles": {"state": "STARTED"}}
            
            response = await client.put(
                url,
                json=payload,
                auth=(username, password),
                headers={"X-Requested-By": "ambari-mcp"}
            )
            
            return f"Start request for {component_name} on {host_name} submitted. Status: {response.status_code}"

    @mcp.tool()
    async def stop_component(server_url: str, cluster_name: str, host_name: str, 
                            component_name: str,
                            username: str = "admin", password: str = "admin", port: str = "8080") -> str:
        """Stop a specific component on a host.

        Args:
            server_url: The URL of the Ambari server
            cluster_name: Name of the cluster
            host_name: FQDN of the host
            component_name: Name of the component to stop
            username: Username for authentication
            password: Password for authentication
            port: Port of the Ambari server
        """
        async with httpx.AsyncClient() as client:
            url = f"{server_url}:{port}/api/v1/clusters/{cluster_name}/hosts/{host_name}/host_components/{component_name}"
            payload = {"HostRoles": {"state": "INSTALLED"}}
            
            response = await client.put(
                url,
                json=payload,
                auth=(username, password),
                headers={"X-Requested-By": "ambari-mcp"}
            )
            
            return f"Stop request for {component_name} on {host_name} submitted. Status: {response.status_code}"

    @mcp.tool()
    async def get_service_status(server_url: str, cluster_name: str, service_name: str,
                               username: str = "admin", password: str = "admin", port: str = "8080") -> str:
        """Get the current status of a service.

        Args:
            server_url: The URL of the Ambari server
            cluster_name: Name of the cluster
            service_name: Name of the service
            username: Username for authentication
            password: Password for authentication
            port: Port of the Ambari server
        """
        async with httpx.AsyncClient() as client:
            url = f"{server_url}:{port}/api/v1/clusters/{cluster_name}/services/{service_name}"
            response = await client.get(
                url,
                auth=(username, password),
                headers={"X-Requested-By": "ambari-mcp"}
            )
            
            service_info = response.json()["ServiceInfo"]
            return f"Service {service_name} status: {service_info['state']} (Maintenance: {service_info.get('maintenance_state', 'OFF')})" 