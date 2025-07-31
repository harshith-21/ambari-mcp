from typing import Any
import httpx
import json
from mcp.server.fastmcp import FastMCP

def register_resources(mcp: FastMCP):
    """Register host information resources with the MCP server"""
    
    @mcp.resource("ambari://hosts/{cluster_name}")
    async def get_all_hosts(cluster_name: str) -> str:
        """Get list of all hosts in the cluster with basic information.
        
        Args:
            cluster_name: Name of the cluster
            
        Returns:
            JSON string with host information that can be used by LLMs
        """
        # This is a resource that LLMs can read - it provides structured data
        # In a real implementation, this would connect to Ambari and fetch actual data
        # For now, we'll provide a template that shows the structure
        
        sample_hosts = {
            "cluster_name": cluster_name,
            "total_hosts": 3,
            "hosts": [
                {
                    "host_name": "master1.example.com",
                    "host_status": "HEALTHY",
                    "host_state": "HEALTHY",
                    "ip": "192.168.1.10",
                    "cpu_count": 8,
                    "total_mem": 32768,
                    "os_type": "redhat7",
                    "components": ["NAMENODE", "RESOURCEMANAGER", "ZOOKEEPER_SERVER"],
                    "maintenance_state": "OFF"
                },
                {
                    "host_name": "worker1.example.com", 
                    "host_status": "HEALTHY",
                    "host_state": "HEALTHY",
                    "ip": "192.168.1.11",
                    "cpu_count": 16,
                    "total_mem": 65536,
                    "os_type": "redhat7",
                    "components": ["DATANODE", "NODEMANAGER"],
                    "maintenance_state": "OFF"
                },
                {
                    "host_name": "worker2.example.com",
                    "host_status": "HEALTHY", 
                    "host_state": "HEALTHY",
                    "ip": "192.168.1.12",
                    "cpu_count": 16,
                    "total_mem": 65536,
                    "os_type": "redhat7",
                    "components": ["DATANODE", "NODEMANAGER"],
                    "maintenance_state": "OFF"
                }
            ],
            "note": "This is sample data. Use tools like get_host_health() with actual server credentials to get real-time data."
        }
        
        return json.dumps(sample_hosts, indent=2)
    
    @mcp.resource("ambari://host-components/{cluster_name}")
    async def get_host_components_matrix(cluster_name: str) -> str:
        """Get a matrix view of which components are installed on which hosts.
        
        Args:
            cluster_name: Name of the cluster
            
        Returns:
            JSON string showing component distribution across hosts
        """
        component_matrix = {
            "cluster_name": cluster_name,
            "component_distribution": {
                "HDFS": {
                    "NAMENODE": ["master1.example.com"],
                    "SECONDARY_NAMENODE": ["master1.example.com"], 
                    "DATANODE": ["worker1.example.com", "worker2.example.com"],
                    "HDFS_CLIENT": ["master1.example.com", "worker1.example.com", "worker2.example.com"]
                },
                "YARN": {
                    "RESOURCEMANAGER": ["master1.example.com"],
                    "NODEMANAGER": ["worker1.example.com", "worker2.example.com"],
                    "YARN_CLIENT": ["master1.example.com", "worker1.example.com", "worker2.example.com"]
                },
                "ZOOKEEPER": {
                    "ZOOKEEPER_SERVER": ["master1.example.com"],
                    "ZOOKEEPER_CLIENT": ["master1.example.com", "worker1.example.com", "worker2.example.com"]
                }
            },
            "summary": {
                "total_components": 9,
                "master_components": 3,
                "slave_components": 4,
                "client_components": 2
            },
            "note": "This is sample data showing typical component distribution. Use get_component_health() tool for real-time data."
        }
        
        return json.dumps(component_matrix, indent=2)
    
    @mcp.resource("ambari://host-metrics/{cluster_name}")
    async def get_host_metrics_summary(cluster_name: str) -> str:
        """Get summary of host metrics and resource utilization.
        
        Args:
            cluster_name: Name of the cluster
            
        Returns:
            JSON string with host metrics summary
        """
        metrics_summary = {
            "cluster_name": cluster_name,
            "timestamp": "2024-01-15T10:30:00Z",
            "cluster_totals": {
                "total_cpu_cores": 40,
                "total_memory_gb": 160,
                "total_disk_space_gb": 2000,
                "avg_cpu_utilization": 25.5,
                "avg_memory_utilization": 68.2,
                "avg_disk_utilization": 45.8
            },
            "host_metrics": [
                {
                    "host_name": "master1.example.com",
                    "cpu_utilization": 35.2,
                    "memory_utilization": 72.1,
                    "disk_utilization": 38.5,
                    "network_io_mbps": 12.3,
                    "load_average": 1.8,
                    "status": "normal"
                },
                {
                    "host_name": "worker1.example.com", 
                    "cpu_utilization": 22.1,
                    "memory_utilization": 65.8,
                    "disk_utilization": 48.2,
                    "network_io_mbps": 45.7,
                    "load_average": 2.1,
                    "status": "normal"
                },
                {
                    "host_name": "worker2.example.com",
                    "cpu_utilization": 19.2,
                    "memory_utilization": 66.7,
                    "disk_utilization": 50.8,
                    "network_io_mbps": 42.1,
                    "load_average": 1.9,
                    "status": "normal"
                }
            ],
            "alerts": [
                {
                    "type": "warning",
                    "message": "worker2.example.com disk utilization above 50%",
                    "severity": "MEDIUM"
                }
            ],
            "note": "This is sample metrics data. Use get_cluster_metrics() tool for real-time metrics."
        }
        
        return json.dumps(metrics_summary, indent=2) 