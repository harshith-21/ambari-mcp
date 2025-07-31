from typing import Any
import httpx
import json
from mcp.server.fastmcp import FastMCP

def register_resources(mcp: FastMCP):
    """Register service configuration resources with the MCP server"""
    
    @mcp.resource("ambari://services/{cluster_name}")
    async def get_all_services(cluster_name: str) -> str:
        """Get list of all services in the cluster with status information.
        
        Args:
            cluster_name: Name of the cluster
            
        Returns:
            JSON string with service information that LLMs can read
        """
        sample_services = {
            "cluster_name": cluster_name,
            "total_services": 6,
            "services": [
                {
                    "service_name": "HDFS",
                    "display_name": "HDFS",
                    "state": "STARTED",
                    "desired_state": "STARTED",
                    "maintenance_state": "OFF",
                    "components": [
                        {"name": "NAMENODE", "state": "STARTED", "hosts": 1},
                        {"name": "SECONDARY_NAMENODE", "state": "STARTED", "hosts": 1},
                        {"name": "DATANODE", "state": "STARTED", "hosts": 2},
                        {"name": "HDFS_CLIENT", "state": "INSTALLED", "hosts": 3}
                    ],
                    "health": "GOOD",
                    "alerts": 0
                },
                {
                    "service_name": "YARN",
                    "display_name": "YARN",
                    "state": "STARTED", 
                    "desired_state": "STARTED",
                    "maintenance_state": "OFF",
                    "components": [
                        {"name": "RESOURCEMANAGER", "state": "STARTED", "hosts": 1},
                        {"name": "NODEMANAGER", "state": "STARTED", "hosts": 2},
                        {"name": "YARN_CLIENT", "state": "INSTALLED", "hosts": 3}
                    ],
                    "health": "GOOD",
                    "alerts": 0
                },
                {
                    "service_name": "MAPREDUCE2",
                    "display_name": "MapReduce2",
                    "state": "STARTED",
                    "desired_state": "STARTED", 
                    "maintenance_state": "OFF",
                    "components": [
                        {"name": "HISTORYSERVER", "state": "STARTED", "hosts": 1},
                        {"name": "MAPREDUCE2_CLIENT", "state": "INSTALLED", "hosts": 3}
                    ],
                    "health": "GOOD",
                    "alerts": 0
                },
                {
                    "service_name": "ZOOKEEPER",
                    "display_name": "ZooKeeper", 
                    "state": "STARTED",
                    "desired_state": "STARTED",
                    "maintenance_state": "OFF",
                    "components": [
                        {"name": "ZOOKEEPER_SERVER", "state": "STARTED", "hosts": 1},
                        {"name": "ZOOKEEPER_CLIENT", "state": "INSTALLED", "hosts": 3}
                    ],
                    "health": "GOOD",
                    "alerts": 0
                },
                {
                    "service_name": "HIVE",
                    "display_name": "Hive",
                    "state": "STARTED",
                    "desired_state": "STARTED",
                    "maintenance_state": "OFF", 
                    "components": [
                        {"name": "HIVE_METASTORE", "state": "STARTED", "hosts": 1},
                        {"name": "HIVE_SERVER", "state": "STARTED", "hosts": 1},
                        {"name": "HIVE_CLIENT", "state": "INSTALLED", "hosts": 3}
                    ],
                    "health": "GOOD",
                    "alerts": 0
                },
                {
                    "service_name": "AMBARI_METRICS",
                    "display_name": "Ambari Metrics",
                    "state": "STARTED",
                    "desired_state": "STARTED",
                    "maintenance_state": "OFF",
                    "components": [
                        {"name": "METRICS_COLLECTOR", "state": "STARTED", "hosts": 1},
                        {"name": "METRICS_MONITOR", "state": "STARTED", "hosts": 3}
                    ],
                    "health": "GOOD", 
                    "alerts": 0
                }
            ],
            "cluster_health": {
                "services_started": 6,
                "services_stopped": 0,
                "services_in_maintenance": 0,
                "total_alerts": 0,
                "overall_status": "HEALTHY"
            },
            "note": "This is sample service data. Use get_service_health() tool for real-time service status."
        }
        
        return json.dumps(sample_services, indent=2)
    
    @mcp.resource("ambari://config-types/{cluster_name}")
    async def get_configuration_types(cluster_name: str) -> str:
        """Get list of all configuration types available in the cluster.
        
        Args:
            cluster_name: Name of the cluster
            
        Returns:
            JSON string with configuration types information
        """
        config_types = {
            "cluster_name": cluster_name,
            "configuration_types": {
                "core_hadoop": [
                    {
                        "type": "core-site",
                        "description": "Hadoop core configuration",
                        "service": "HDFS",
                        "version": "version1640995200000",
                        "properties_count": 25,
                        "last_modified": "2024-01-10T14:30:00Z"
                    },
                    {
                        "type": "hdfs-site", 
                        "description": "HDFS configuration",
                        "service": "HDFS",
                        "version": "version1640995200000",
                        "properties_count": 45,
                        "last_modified": "2024-01-10T14:30:00Z"
                    },
                    {
                        "type": "yarn-site",
                        "description": "YARN configuration", 
                        "service": "YARN",
                        "version": "version1640995200000",
                        "properties_count": 38,
                        "last_modified": "2024-01-10T14:30:00Z"
                    },
                    {
                        "type": "mapred-site",
                        "description": "MapReduce configuration",
                        "service": "MAPREDUCE2", 
                        "version": "version1640995200000",
                        "properties_count": 22,
                        "last_modified": "2024-01-10T14:30:00Z"
                    }
                ],
                "service_specific": [
                    {
                        "type": "hive-site",
                        "description": "Hive configuration",
                        "service": "HIVE",
                        "version": "version1640995200000", 
                        "properties_count": 67,
                        "last_modified": "2024-01-12T09:15:00Z"
                    },
                    {
                        "type": "zoo.cfg",
                        "description": "ZooKeeper configuration",
                        "service": "ZOOKEEPER",
                        "version": "version1640995200000",
                        "properties_count": 12,
                        "last_modified": "2024-01-10T14:30:00Z"
                    }
                ],
                "environment": [
                    {
                        "type": "hadoop-env",
                        "description": "Hadoop environment variables",
                        "service": "HDFS",
                        "version": "version1640995200000",
                        "properties_count": 8,
                        "last_modified": "2024-01-10T14:30:00Z"
                    },
                    {
                        "type": "yarn-env",
                        "description": "YARN environment variables", 
                        "service": "YARN",
                        "version": "version1640995200000",
                        "properties_count": 6,
                        "last_modified": "2024-01-10T14:30:00Z"
                    }
                ]
            },
            "summary": {
                "total_config_types": 8,
                "core_hadoop_configs": 4,
                "service_specific_configs": 2,
                "environment_configs": 2
            },
            "note": "This is sample configuration data. Use get_service_config() tool to retrieve actual configuration values."
        }
        
        return json.dumps(config_types, indent=2)
    
    @mcp.resource("ambari://alerts/{cluster_name}")
    async def get_cluster_alerts(cluster_name: str) -> str:
        """Get current alerts and their status in the cluster.
        
        Args:
            cluster_name: Name of the cluster
            
        Returns:
            JSON string with alerts information
        """
        alerts_data = {
            "cluster_name": cluster_name,
            "timestamp": "2024-01-15T10:30:00Z",
            "alert_summary": {
                "OK": 45,
                "WARNING": 2,
                "CRITICAL": 0,
                "UNKNOWN": 1,
                "total": 48
            },
            "active_alerts": [
                {
                    "alert_name": "DataNode Web UI",
                    "service_name": "HDFS",
                    "component_name": "DATANODE",
                    "host_name": "worker2.example.com",
                    "state": "WARNING",
                    "text": "HTTP 200 response time is 3.456 seconds",
                    "timestamp": 1642248600,
                    "repeat_tolerance": 2,
                    "repeat_tolerance_remaining": 1
                },
                {
                    "alert_name": "Percent NodeManagers Available",
                    "service_name": "YARN", 
                    "component_name": "RESOURCEMANAGER",
                    "host_name": "master1.example.com",
                    "state": "WARNING",
                    "text": "affected: 0, total: 2",
                    "timestamp": 1642248600,
                    "repeat_tolerance": 1,
                    "repeat_tolerance_remaining": 0
                },
                {
                    "alert_name": "Ambari Agent Disk Usage",
                    "service_name": "AMBARI",
                    "component_name": "AMBARI_AGENT", 
                    "host_name": "worker1.example.com",
                    "state": "UNKNOWN",
                    "text": "Unable to determine disk usage",
                    "timestamp": 1642248300,
                    "repeat_tolerance": 5,
                    "repeat_tolerance_remaining": 4
                }
            ],
            "alert_groups": [
                {
                    "group_name": "HDFS",
                    "alerts_count": 12,
                    "ok": 10,
                    "warning": 1,
                    "critical": 0,
                    "unknown": 1
                },
                {
                    "group_name": "YARN",
                    "alerts_count": 8,
                    "ok": 7,
                    "warning": 1, 
                    "critical": 0,
                    "unknown": 0
                },
                {
                    "group_name": "ZOOKEEPER",
                    "alerts_count": 3,
                    "ok": 3,
                    "warning": 0,
                    "critical": 0,
                    "unknown": 0
                }
            ],
            "recommendations": [
                "Investigate DataNode response time on worker2.example.com",
                "Check NodeManager connectivity issues",
                "Verify Ambari Agent status on worker1.example.com"
            ],
            "note": "This is sample alerts data. Use get_alerts() tool for real-time alert information."
        }
        
        return json.dumps(alerts_data, indent=2) 