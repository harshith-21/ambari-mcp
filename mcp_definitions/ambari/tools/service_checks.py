from typing import Any, Dict, List, Optional
import httpx
import json
from mcp.server.fastmcp import FastMCP

def register_tools(mcp: FastMCP):
    """Register service check and monitoring tools with the MCP server"""
    
    @mcp.tool()
    async def run_service_check(server_url: str, cluster_name: str, service_name: str,
                              username: str = "admin", password: str = "admin", port: str = "8080") -> str:
        """Run service check for a specific service.

        Args:
            server_url: The URL of the Ambari server
            cluster_name: Name of the cluster
            service_name: Name of the service to check (e.g., HDFS, YARN, HIVE)
            username: Username for authentication
            password: Password for authentication
            port: Port of the Ambari server
        """
        async with httpx.AsyncClient() as client:
            url = f"{server_url}:{port}/api/v1/clusters/{cluster_name}/requests"
            payload = {
                "RequestInfo": {
                    "context": f"Service Check {service_name} via MCP",
                    "command": "SERVICE_CHECK"
                },
                "Requests/resource_filters": [{
                    "service_name": service_name
                }]
            }
            
            response = await client.post(
                url,
                json=payload,
                auth=(username, password),
                headers={"X-Requested-By": "ambari-mcp"}
            )
            
            if response.status_code == 202:
                request_id = response.json()["Requests"]["id"]
                return f"Service check for {service_name} initiated. Request ID: {request_id}"
            else:
                return f"Failed to initiate service check: {response.text}"

    @mcp.tool()
    async def get_service_health(server_url: str, cluster_name: str, service_name: str = None,
                               username: str = "admin", password: str = "admin", port: str = "8080") -> str:
        """Get health status of services in the cluster.

        Args:
            server_url: The URL of the Ambari server
            cluster_name: Name of the cluster
            service_name: Optional specific service name to check
            username: Username for authentication
            password: Password for authentication
            port: Port of the Ambari server
        """
        async with httpx.AsyncClient() as client:
            if service_name:
                url = f"{server_url}:{port}/api/v1/clusters/{cluster_name}/services/{service_name}"
                response = await client.get(
                    url,
                    auth=(username, password),
                    headers={"X-Requested-By": "ambari-mcp"}
                )
                
                service_info = response.json()["ServiceInfo"]
                return json.dumps({
                    "service_name": service_info["service_name"],
                    "state": service_info["state"],
                    "maintenance_state": service_info.get("maintenance_state", "OFF"),
                    "desired_state": service_info.get("desired_state", "UNKNOWN")
                }, indent=2)
            else:
                url = f"{server_url}:{port}/api/v1/clusters/{cluster_name}/services"
                response = await client.get(
                    url,
                    auth=(username, password),
                    headers={"X-Requested-By": "ambari-mcp"}
                )
                
                services = response.json()["items"]
                result = []
                
                for service in services:
                    service_info = service["ServiceInfo"]
                    result.append({
                        "service_name": service_info["service_name"],
                        "state": service_info["state"],
                        "maintenance_state": service_info.get("maintenance_state", "OFF"),
                        "desired_state": service_info.get("desired_state", "UNKNOWN")
                    })
                
                return json.dumps(result, indent=2)

    @mcp.tool()
    async def get_component_health(server_url: str, cluster_name: str, service_name: str = None,
                                 username: str = "admin", password: str = "admin", port: str = "8080") -> str:
        """Get health status of components in the cluster.

        Args:
            server_url: The URL of the Ambari server
            cluster_name: Name of the cluster
            service_name: Optional service name to filter components
            username: Username for authentication
            password: Password for authentication
            port: Port of the Ambari server
        """
        async with httpx.AsyncClient() as client:
            if service_name:
                url = f"{server_url}:{port}/api/v1/clusters/{cluster_name}/services/{service_name}/components"
            else:
                url = f"{server_url}:{port}/api/v1/clusters/{cluster_name}/host_components"
            
            response = await client.get(
                url,
                auth=(username, password),
                headers={"X-Requested-By": "ambari-mcp"}
            )
            
            items = response.json()["items"]
            result = []
            
            for item in items:
                if service_name:
                    # Service components
                    comp_info = item["ServiceComponentInfo"]
                    result.append({
                        "service_name": comp_info["service_name"],
                        "component_name": comp_info["component_name"],
                        "state": comp_info["state"],
                        "total_count": comp_info["total_count"],
                        "started_count": comp_info["started_count"],
                        "installed_count": comp_info["installed_count"]
                    })
                else:
                    # Host components
                    host_role = item["HostRoles"]
                    result.append({
                        "service_name": host_role["service_name"],
                        "component_name": host_role["component_name"],
                        "host_name": host_role["host_name"],
                        "state": host_role["state"],
                        "desired_state": host_role.get("desired_state", "UNKNOWN"),
                        "maintenance_state": host_role.get("maintenance_state", "OFF")
                    })
            
            return json.dumps(result, indent=2)

    @mcp.tool()
    async def get_host_health(server_url: str, cluster_name: str, host_name: str = None,
                            username: str = "admin", password: str = "admin", port: str = "8080") -> str:
        """Get health status of hosts in the cluster.

        Args:
            server_url: The URL of the Ambari server
            cluster_name: Name of the cluster
            host_name: Optional specific host name to check
            username: Username for authentication
            password: Password for authentication
            port: Port of the Ambari server
        """
        async with httpx.AsyncClient() as client:
            if host_name:
                url = f"{server_url}:{port}/api/v1/clusters/{cluster_name}/hosts/{host_name}"
            else:
                url = f"{server_url}:{port}/api/v1/clusters/{cluster_name}/hosts"
            
            response = await client.get(
                url,
                auth=(username, password),
                headers={"X-Requested-By": "ambari-mcp"}
            )
            
            if host_name:
                host_info = response.json()["Hosts"]
                return json.dumps({
                    "host_name": host_info["host_name"],
                    "host_status": host_info["host_status"],
                    "host_state": host_info["host_state"],
                    "maintenance_state": host_info.get("maintenance_state", "OFF"),
                    "public_host_name": host_info.get("public_host_name", ""),
                    "cpu_count": host_info.get("cpu_count", 0),
                    "total_mem": host_info.get("total_mem", 0)
                }, indent=2)
            else:
                hosts = response.json()["items"]
                result = []
                
                for host in hosts:
                    host_info = host["Hosts"]
                    result.append({
                        "host_name": host_info["host_name"],
                        "host_status": host_info["host_status"],
                        "host_state": host_info["host_state"],
                        "maintenance_state": host_info.get("maintenance_state", "OFF"),
                        "public_host_name": host_info.get("public_host_name", ""),
                        "cpu_count": host_info.get("cpu_count", 0),
                        "total_mem": host_info.get("total_mem", 0)
                    })
                
                return json.dumps(result, indent=2)

    @mcp.tool()
    async def get_alerts(server_url: str, cluster_name: str, alert_state: str = None,
                       username: str = "admin", password: str = "admin", port: str = "8080") -> str:
        """Get cluster alerts.

        Args:
            server_url: The URL of the Ambari server
            cluster_name: Name of the cluster
            alert_state: Optional filter by alert state (OK, WARNING, CRITICAL, UNKNOWN)
            username: Username for authentication
            password: Password for authentication
            port: Port of the Ambari server
        """
        async with httpx.AsyncClient() as client:
            url = f"{server_url}:{port}/api/v1/clusters/{cluster_name}/alerts"
            if alert_state:
                url += f"?Alert/state={alert_state}"
            
            response = await client.get(
                url,
                auth=(username, password),
                headers={"X-Requested-By": "ambari-mcp"}
            )
            
            alerts = response.json()["items"]
            result = []
            
            for alert in alerts:
                alert_info = alert["Alert"]
                result.append({
                    "alert_name": alert_info["name"],
                    "service_name": alert_info.get("service_name", ""),
                    "component_name": alert_info.get("component_name", ""),
                    "host_name": alert_info.get("host_name", ""),
                    "state": alert_info["state"],
                    "text": alert_info.get("text", ""),
                    "timestamp": alert_info.get("timestamp", 0),
                    "maintenance_state": alert_info.get("maintenance_state", "OFF")
                })
            
            return json.dumps(result, indent=2)

    @mcp.tool()
    async def get_request_status(server_url: str, cluster_name: str, request_id: int,
                               username: str = "admin", password: str = "admin", port: str = "8080") -> str:
        """Get status of a specific request (operation).

        Args:
            server_url: The URL of the Ambari server
            cluster_name: Name of the cluster
            request_id: ID of the request to check
            username: Username for authentication
            password: Password for authentication
            port: Port of the Ambari server
        """
        async with httpx.AsyncClient() as client:
            url = f"{server_url}:{port}/api/v1/clusters/{cluster_name}/requests/{request_id}"
            
            response = await client.get(
                url,
                auth=(username, password),
                headers={"X-Requested-By": "ambari-mcp"}
            )
            
            request_info = response.json()["Requests"]
            
            # Get task details
            tasks_url = f"{server_url}:{port}/api/v1/clusters/{cluster_name}/requests/{request_id}/tasks"
            tasks_response = await client.get(
                tasks_url,
                auth=(username, password),
                headers={"X-Requested-By": "ambari-mcp"}
            )
            
            tasks = tasks_response.json()["items"]
            task_summary = {}
            
            for task in tasks:
                task_status = task["Tasks"]["status"]
                task_summary[task_status] = task_summary.get(task_status, 0) + 1
            
            return json.dumps({
                "request_id": request_info["id"],
                "request_context": request_info.get("request_context", ""),
                "request_status": request_info["request_status"],
                "progress_percent": request_info.get("progress_percent", 0),
                "start_time": request_info.get("start_time", 0),
                "end_time": request_info.get("end_time", 0),
                "task_summary": task_summary
            }, indent=2)

    @mcp.tool()
    async def get_cluster_metrics(server_url: str, cluster_name: str, metric_name: str = None,
                                username: str = "admin", password: str = "admin", port: str = "8080") -> str:
        """Get cluster-level metrics.

        Args:
            server_url: The URL of the Ambari server
            cluster_name: Name of the cluster
            metric_name: Optional specific metric to retrieve
            username: Username for authentication
            password: Password for authentication
            port: Port of the Ambari server
        """
        async with httpx.AsyncClient() as client:
            if metric_name:
                url = f"{server_url}:{port}/api/v1/clusters/{cluster_name}?fields=metrics/{metric_name}"
            else:
                url = f"{server_url}:{port}/api/v1/clusters/{cluster_name}?fields=metrics"
            
            response = await client.get(
                url,
                auth=(username, password),
                headers={"X-Requested-By": "ambari-mcp"}
            )
            
            cluster_data = response.json()
            metrics = cluster_data.get("metrics", {})
            
            return json.dumps(metrics, indent=2) 