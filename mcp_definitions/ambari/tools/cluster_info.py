import httpx
import json
from typing import Any, Dict, Optional
from mcp.server.fastmcp import FastMCP

def register_tools(mcp: FastMCP):
    """Register cluster information tools with the MCP server"""
    
    @mcp.tool()
    async def get_cluster_name(
        server_url: str,
        username: str = "admin",
        password: str = "admin", 
        port: str = "8080"
    ) -> str:
        """Get the cluster name from Ambari server.
        
        Args:
            server_url: Ambari server URL (e.g., http://ambari-server.example.com)
            username: Ambari username (default: admin)
            password: Ambari password (default: admin)
            port: Ambari server port (default: 8080)
            
        Returns:
            Cluster name or error message
        """
        try:
            # Construct the full URL
            base_url = f"{server_url}:{port}"
            if not base_url.startswith(('http://', 'https://')):
                base_url = f"http://{base_url}"
            
            url = f"{base_url}/api/v1/clusters"
            
            # Make authenticated request
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    auth=(username, password),
                    headers={'X-Requested-By': 'ambari'},
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if 'items' in data and len(data['items']) > 0:
                        cluster_name = data['items'][0]['Clusters']['cluster_name']
                        return f"Cluster name: {cluster_name}"
                    else:
                        return "No clusters found"
                else:
                    return f"Error: HTTP {response.status_code} - {response.text}"
                    
        except Exception as e:
            return f"Error connecting to Ambari server: {str(e)}"

    @mcp.tool()
    async def get_all_hosts(
        server_url: str,
        cluster_name: str,
        username: str = "admin",
        password: str = "admin",
        port: str = "8080"
    ) -> str:
        """Get list of all hosts in the cluster using Ambari REST API.
        
        Args:
            server_url: Ambari server URL (e.g., http://ambari-server.example.com)
            cluster_name: Name of the cluster (e.g., ODP_Quantum)
            username: Ambari username (default: admin)
            password: Ambari password (default: admin)
            port: Ambari server port (default: 8080)
            
        Returns:
            JSON string with all hosts information
        """
        try:
            # Construct the full URL
            base_url = f"{server_url}:{port}"
            if not base_url.startswith(('http://', 'https://')):
                base_url = f"http://{base_url}"
            
            # Use the exact API endpoint: GET /api/v1/clusters/{cluster_name}/hosts
            url = f"{base_url}/api/v1/clusters/{cluster_name}/hosts"
            
            # Make authenticated request
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    auth=(username, password),
                    headers={'X-Requested-By': 'ambari'},
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Format the response for better readability
                    formatted_data = {
                        "cluster_name": cluster_name,
                        "total_hosts": len(data.get('items', [])),
                        "hosts": []
                    }
                    
                    for item in data.get('items', []):
                        host_info = item.get('Hosts', {})
                        formatted_data["hosts"].append({
                            "host_name": host_info.get('host_name'),
                            "host_status": host_info.get('host_status'),
                            "host_state": host_info.get('host_state'),
                            "ip": host_info.get('ip'),
                            "cpu_count": host_info.get('cpu_count'),
                            "total_mem": host_info.get('total_mem'),
                            "os_type": host_info.get('os_type'),
                            "os_arch": host_info.get('os_arch'),
                            "os_family": host_info.get('os_family'),
                            "maintenance_state": host_info.get('maintenance_state'),
                            "last_heartbeat_time": host_info.get('last_heartbeat_time'),
                            "disk_info": host_info.get('disk_info', [])
                        })
                    
                    return json.dumps(formatted_data, indent=2)
                else:
                    return f"Error: HTTP {response.status_code} - {response.text}"
                    
        except Exception as e:
            return f"Error connecting to Ambari server: {str(e)}"

    @mcp.tool()
    async def get_host_details(
        server_url: str,
        cluster_name: str,
        hostname: str,
        username: str = "admin",
        password: str = "admin",
        port: str = "8080"
    ) -> str:
        """Get detailed host metrics including memory info using Ambari REST API.
        
        Args:
            server_url: Ambari server URL (e.g., http://ambari-server.example.com)
            cluster_name: Name of the cluster (e.g., ODP_Quantum)
            hostname: Hostname to get details for
            username: Ambari username (default: admin)
            password: Ambari password (default: admin)
            port: Ambari server port (default: 8080)
            
        Returns:
            JSON string with detailed host metrics including memory info
        """
        try:
            # Construct the full URL
            base_url = f"{server_url}:{port}"
            if not base_url.startswith(('http://', 'https://')):
                base_url = f"http://{base_url}"
            
            # Use the exact API endpoint: GET /api/v1/clusters/{cluster_name}/hosts/{hostname}
            url = f"{base_url}/api/v1/clusters/{cluster_name}/hosts/{hostname}"
            
            # Make authenticated request with fields to get detailed metrics
            params = {
                "fields": "Hosts,host_components,metrics/cpu,metrics/memory,metrics/disk,metrics/network,metrics/load"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    auth=(username, password),
                    headers={'X-Requested-By': 'ambari'},
                    params=params,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Extract host information
                    host_info = data.get('Hosts', {})
                    metrics = data.get('metrics', {})
                    host_components = data.get('host_components', [])
                    
                    # Format the response with detailed metrics
                    formatted_data = {
                        "cluster_name": cluster_name,
                        "host_name": hostname,
                        "basic_info": {
                            "host_status": host_info.get('host_status'),
                            "host_state": host_info.get('host_state'),
                            "ip": host_info.get('ip'),
                            "cpu_count": host_info.get('cpu_count'),
                            "total_mem": host_info.get('total_mem'),
                            "os_type": host_info.get('os_type'),
                            "os_arch": host_info.get('os_arch'),
                            "os_family": host_info.get('os_family'),
                            "maintenance_state": host_info.get('maintenance_state'),
                            "last_heartbeat_time": host_info.get('last_heartbeat_time'),
                            "disk_info": host_info.get('disk_info', [])
                        },
                        "components": [
                            {
                                "component_name": comp.get('HostRoles', {}).get('component_name'),
                                "service_name": comp.get('HostRoles', {}).get('service_name'),
                                "state": comp.get('HostRoles', {}).get('state'),
                                "desired_state": comp.get('HostRoles', {}).get('desired_state')
                            }
                            for comp in host_components
                        ],
                        "metrics": {
                            "cpu": metrics.get('cpu', {}),
                            "memory": metrics.get('memory', {}),
                            "disk": metrics.get('disk', {}),
                            "network": metrics.get('network', {}),
                            "load": metrics.get('load', {})
                        }
                    }
                    
                    return json.dumps(formatted_data, indent=2)
                else:
                    return f"Error: HTTP {response.status_code} - {response.text}"
                    
        except Exception as e:
            return f"Error connecting to Ambari server: {str(e)}"

    @mcp.tool()
    async def get_host_components(
        server_url: str,
        cluster_name: str,
        hostname: str,
        username: str = "admin",
        password: str = "admin",
        port: str = "8080"
    ) -> str:
        """Get all components installed on a specific host.
        
        Args:
            server_url: Ambari server URL (e.g., http://ambari-server.example.com)
            cluster_name: Name of the cluster (e.g., ODP_Quantum)
            hostname: Hostname to get components for
            username: Ambari username (default: admin)
            password: Ambari password (default: admin)
            port: Ambari server port (default: 8080)
            
        Returns:
            JSON string with all components on the host
        """
        try:
            # Construct the full URL
            base_url = f"{server_url}:{port}"
            if not base_url.startswith(('http://', 'https://')):
                base_url = f"http://{base_url}"
            
            # API endpoint for host components
            url = f"{base_url}/api/v1/clusters/{cluster_name}/hosts/{hostname}/host_components"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    auth=(username, password),
                    headers={'X-Requested-By': 'ambari'},
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    formatted_data = {
                        "cluster_name": cluster_name,
                        "host_name": hostname,
                        "total_components": len(data.get('items', [])),
                        "components": []
                    }
                    
                    for item in data.get('items', []):
                        host_roles = item.get('HostRoles', {})
                        formatted_data["components"].append({
                            "component_name": host_roles.get('component_name'),
                            "service_name": host_roles.get('service_name'),
                            "state": host_roles.get('state'),
                            "desired_state": host_roles.get('desired_state'),
                            "stack_id": host_roles.get('stack_id'),
                            "maintenance_state": host_roles.get('maintenance_state')
                        })
                    
                    return json.dumps(formatted_data, indent=2)
                else:
                    return f"Error: HTTP {response.status_code} - {response.text}"
                    
        except Exception as e:
            return f"Error connecting to Ambari server: {str(e)}" 

    @mcp.tool()
    async def get_cluster_host_summary(
        server_url: str,
        cluster_name: str,
        username: str = "admin",
        password: str = "admin",
        port: str = "8080"
    ) -> str:
        """Get cluster-wide host summary with aggregated metrics and health status.
        
        Args:
            server_url: Ambari server URL (e.g., http://ambari-server.example.com)
            cluster_name: Name of the cluster (e.g., ODP_Quantum)
            username: Ambari username (default: admin)
            password: Ambari password (default: admin)
            port: Ambari server port (default: 8080)
            
        Returns:
            JSON string with cluster host summary and aggregated metrics
        """
        try:
            # Construct the full URL
            base_url = f"{server_url}:{port}"
            if not base_url.startswith(('http://', 'https://')):
                base_url = f"http://{base_url}"
            
            # Get hosts with metrics fields
            url = f"{base_url}/api/v1/clusters/{cluster_name}/hosts"
            params = {
                "fields": "Hosts/host_name,Hosts/host_status,Hosts/host_state,Hosts/cpu_count,Hosts/total_mem,Hosts/os_type,Hosts/maintenance_state,Hosts/last_heartbeat_time,metrics/cpu,metrics/memory,metrics/disk,metrics/load"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    auth=(username, password),
                    headers={'X-Requested-By': 'ambari'},
                    params=params,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    hosts = data.get('items', [])
                    
                    # Aggregate cluster metrics
                    total_hosts = len(hosts)
                    healthy_hosts = 0
                    total_cpu = 0
                    total_memory = 0
                    hosts_in_maintenance = 0
                    
                    host_details = []
                    
                    for item in hosts:
                        host_info = item.get('Hosts', {})
                        metrics = item.get('metrics', {})
                        
                        # Count healthy hosts
                        if host_info.get('host_status') == 'HEALTHY':
                            healthy_hosts += 1
                        
                        # Count maintenance hosts
                        if host_info.get('maintenance_state') == 'ON':
                            hosts_in_maintenance += 1
                        
                        # Aggregate resources
                        cpu_count = host_info.get('cpu_count', 0) or 0
                        total_mem = host_info.get('total_mem', 0) or 0
                        total_cpu += cpu_count
                        total_memory += total_mem
                        
                        # Extract current metrics if available
                        cpu_metrics = metrics.get('cpu', {})
                        memory_metrics = metrics.get('memory', {})
                        load_metrics = metrics.get('load', {})
                        
                        host_details.append({
                            "host_name": host_info.get('host_name'),
                            "host_status": host_info.get('host_status'),
                            "host_state": host_info.get('host_state'),
                            "cpu_count": cpu_count,
                            "total_mem_mb": total_mem,
                            "os_type": host_info.get('os_type'),
                            "maintenance_state": host_info.get('maintenance_state'),
                            "last_heartbeat": host_info.get('last_heartbeat_time'),
                            "current_metrics": {
                                "cpu_usage": cpu_metrics.get('cpu_user', {}).get('_avg') if cpu_metrics else None,
                                "memory_usage": memory_metrics.get('mem_total', {}).get('_avg') if memory_metrics else None,
                                "load_avg": load_metrics.get('load_one', {}).get('_avg') if load_metrics else None
                            }
                        })
                    
                    # Create summary
                    formatted_data = {
                        "cluster_name": cluster_name,
                        "summary": {
                            "total_hosts": total_hosts,
                            "healthy_hosts": healthy_hosts,
                            "unhealthy_hosts": total_hosts - healthy_hosts,
                            "hosts_in_maintenance": hosts_in_maintenance,
                            "cluster_resources": {
                                "total_cpu_cores": total_cpu,
                                "total_memory_gb": round(total_memory / 1024, 2) if total_memory else 0,
                                "avg_cpu_per_host": round(total_cpu / total_hosts, 2) if total_hosts else 0,
                                "avg_memory_per_host_gb": round((total_memory / 1024) / total_hosts, 2) if total_hosts and total_memory else 0
                            },
                            "health_percentage": round((healthy_hosts / total_hosts) * 100, 2) if total_hosts else 0
                        },
                        "hosts": host_details
                    }
                    
                    return json.dumps(formatted_data, indent=2)
                else:
                    return f"Error: HTTP {response.status_code} - {response.text}"
                    
        except Exception as e:
            return f"Error connecting to Ambari server: {str(e)}" 