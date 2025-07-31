from typing import Any, Dict, Optional
import httpx
import json
from mcp.server.fastmcp import FastMCP

def register_tools(mcp: FastMCP):
    """Register configuration management tools with the MCP server"""
    
    @mcp.tool()
    async def get_service_config(server_url: str, cluster_name: str, config_type: str,
                               username: str = "admin", password: str = "admin", port: str = "8080") -> str:
        """Get current configuration for a specific config type.

        Args:
            server_url: The URL of the Ambari server
            cluster_name: Name of the cluster
            config_type: Configuration type (e.g., core-site, hdfs-site, yarn-site)
            username: Username for authentication
            password: Password for authentication
            port: Port of the Ambari server
        """
        async with httpx.AsyncClient() as client:
            # Get the current config tag
            cluster_url = f"{server_url}:{port}/api/v1/clusters/{cluster_name}?fields=Clusters/desired_configs"
            cluster_response = await client.get(
                cluster_url,
                auth=(username, password),
                headers={"X-Requested-By": "ambari-mcp"}
            )
            
            desired_configs = cluster_response.json()["Clusters"]["desired_configs"]
            if config_type not in desired_configs:
                return f"Configuration type {config_type} not found"
            
            current_tag = desired_configs[config_type]["tag"]
            
            # Get the actual configuration
            config_url = f"{server_url}:{port}/api/v1/clusters/{cluster_name}/configurations?type={config_type}&tag={current_tag}"
            config_response = await client.get(
                config_url,
                auth=(username, password),
                headers={"X-Requested-By": "ambari-mcp"}
            )
            
            config_data = config_response.json()["items"][0]
            return json.dumps({
                "type": config_data["type"],
                "tag": config_data["tag"],
                "properties": config_data["properties"]
            }, indent=2)

    @mcp.tool()
    async def update_service_config(server_url: str, cluster_name: str, config_type: str, 
                                  properties: str, service_config_version_note: str = "Updated via MCP",
                                  username: str = "admin", password: str = "admin", port: str = "8080") -> str:
        """Update service configuration with new properties.

        Args:
            server_url: The URL of the Ambari server
            cluster_name: Name of the cluster
            config_type: Configuration type (e.g., core-site, hdfs-site)
            properties: JSON string of properties to update
            service_config_version_note: Note for the configuration version
            username: Username for authentication
            password: Password for authentication
            port: Port of the Ambari server
        """
        async with httpx.AsyncClient() as client:
            import time
            
            # Parse properties JSON
            try:
                props = json.loads(properties)
            except json.JSONDecodeError:
                return "Error: Properties must be valid JSON"
            
            # Create new tag with timestamp
            new_tag = f"version{int(time.time() * 1000)}"
            
            # Update configuration
            url = f"{server_url}:{port}/api/v1/clusters/{cluster_name}"
            payload = {
                "Clusters": {
                    "desired_config": {
                        "type": config_type,
                        "tag": new_tag,
                        "properties": props,
                        "service_config_version_note": service_config_version_note
                    }
                }
            }
            
            response = await client.put(
                url,
                json=payload,
                auth=(username, password),
                headers={"X-Requested-By": "ambari-mcp"}
            )
            
            if response.status_code == 200:
                return f"Configuration {config_type} updated successfully with tag {new_tag}"
            else:
                return f"Failed to update configuration: {response.text}"

    @mcp.tool()
    async def rollback_service_config(server_url: str, cluster_name: str, service_name: str, 
                                    service_config_version: int,
                                    username: str = "admin", password: str = "admin", port: str = "8080") -> str:
        """Rollback service configuration to a previous version.

        Args:
            server_url: The URL of the Ambari server
            cluster_name: Name of the cluster
            service_name: Name of the service (e.g., HDFS, YARN)
            service_config_version: Version number to rollback to
            username: Username for authentication
            password: Password for authentication
            port: Port of the Ambari server
        """
        async with httpx.AsyncClient() as client:
            url = f"{server_url}:{port}/api/v1/clusters/{cluster_name}"
            payload = {
                "Clusters": {
                    "desired_service_config_versions": {
                        "service_name": service_name,
                        "service_config_version": service_config_version,
                        "service_config_version_note": f"Rollback to version {service_config_version} via MCP"
                    }
                }
            }
            
            response = await client.put(
                url,
                json=payload,
                auth=(username, password),
                headers={"X-Requested-By": "ambari-mcp"}
            )
            
            if response.status_code == 200:
                result = response.json()
                new_version = result["resources"][0]["service_config_version"]
                return f"Successfully rolled back {service_name} to version {service_config_version}. New version created: {new_version}"
            else:
                return f"Failed to rollback configuration: {response.text}"

    @mcp.tool()
    async def get_service_config_versions(server_url: str, cluster_name: str, service_name: str = None,
                                        username: str = "admin", password: str = "admin", port: str = "8080") -> str:
        """Get service configuration versions history.

        Args:
            server_url: The URL of the Ambari server
            cluster_name: Name of the cluster
            service_name: Optional service name to filter by
            username: Username for authentication
            password: Password for authentication
            port: Port of the Ambari server
        """
        async with httpx.AsyncClient() as client:
            url = f"{server_url}:{port}/api/v1/clusters/{cluster_name}/configurations/service_config_versions"
            if service_name:
                url += f"?service_name={service_name}"
            
            response = await client.get(
                url,
                auth=(username, password),
                headers={"X-Requested-By": "ambari-mcp"}
            )
            
            versions = response.json()["items"]
            result = []
            
            for version in versions:
                result.append({
                    "service_name": version["service_name"],
                    "version": version["service_config_version"],
                    "is_current": version["is_current"],
                    "user": version["user"],
                    "note": version.get("service_config_version_note", ""),
                    "create_time": version["createtime"]
                })
            
            return json.dumps(result, indent=2)

    @mcp.tool()
    async def update_repository_url(server_url: str, cluster_name: str, stack_name: str, 
                                  stack_version: str, os_type: str, repo_id: str, base_url: str,
                                  username: str = "admin", password: str = "admin", port: str = "8080") -> str:
        """Update repository URL for a stack version.

        Args:
            server_url: The URL of the Ambari server
            cluster_name: Name of the cluster
            stack_name: Stack name (e.g., HDP)
            stack_version: Stack version (e.g., 2.7)
            os_type: Operating system type (e.g., redhat7, ubuntu18)
            repo_id: Repository ID (e.g., HDP-2.7, HDP-UTILS-1.1.0.22)
            base_url: New base URL for the repository
            username: Username for authentication
            password: Password for authentication
            port: Port of the Ambari server
        """
        async with httpx.AsyncClient() as client:
            url = f"{server_url}:{port}/api/v1/clusters/{cluster_name}/stack_versions/{stack_name}-{stack_version}/repository_versions/1"
            
            # First get current repository information
            get_response = await client.get(
                url,
                auth=(username, password),
                headers={"X-Requested-By": "ambari-mcp"}
            )
            
            current_data = get_response.json()
            
            # Update the specific repository
            repositories = current_data["RepositoryVersionInfo"]["repositories"]
            for repo in repositories:
                if repo["Repositories"]["repo_id"] == repo_id and repo["Repositories"]["os_type"] == os_type:
                    repo["Repositories"]["base_url"] = base_url
                    break
            else:
                return f"Repository {repo_id} for {os_type} not found"
            
            # Update the repository version
            payload = {
                "RepositoryVersionInfo": {
                    "repositories": repositories
                }
            }
            
            response = await client.put(
                url,
                json=payload,
                auth=(username, password),
                headers={"X-Requested-By": "ambari-mcp"}
            )
            
            if response.status_code == 200:
                return f"Successfully updated repository {repo_id} URL to {base_url}"
            else:
                return f"Failed to update repository: {response.text}"

    @mcp.tool()
    async def register_repository_version(server_url: str, cluster_name: str, stack_name: str,
                                        stack_version: str, version_definition_file_url: str,
                                        username: str = "admin", password: str = "admin", port: str = "8080") -> str:
        """Register a new repository version using VDF (Version Definition File).

        Args:
            server_url: The URL of the Ambari server
            cluster_name: Name of the cluster
            stack_name: Stack name (e.g., HDP)
            stack_version: Stack version (e.g., 2.7)
            version_definition_file_url: URL to the VDF file
            username: Username for authentication
            password: Password for authentication
            port: Port of the Ambari server
        """
        async with httpx.AsyncClient() as client:
            url = f"{server_url}:{port}/api/v1/clusters/{cluster_name}/stack_versions/{stack_name}-{stack_version}/repository_versions"
            
            payload = {
                "RepositoryVersionInfo": {
                    "version_definition_file_url": version_definition_file_url
                }
            }
            
            response = await client.post(
                url,
                json=payload,
                auth=(username, password),
                headers={"X-Requested-By": "ambari-mcp"}
            )
            
            if response.status_code == 201:
                result = response.json()
                return f"Successfully registered repository version. ID: {result['resources'][0]['RepositoryVersionInfo']['id']}"
            else:
                return f"Failed to register repository version: {response.text}"

    @mcp.tool()
    async def get_cluster_repositories(server_url: str, cluster_name: str,
                                     username: str = "admin", password: str = "admin", port: str = "8080") -> str:
        """Get all repository information for the cluster.

        Args:
            server_url: The URL of the Ambari server
            cluster_name: Name of the cluster
            username: Username for authentication
            password: Password for authentication
            port: Port of the Ambari server
        """
        async with httpx.AsyncClient() as client:
            url = f"{server_url}:{port}/api/v1/clusters/{cluster_name}/stack_versions"
            
            response = await client.get(
                url,
                auth=(username, password),
                headers={"X-Requested-By": "ambari-mcp"}
            )
            
            stack_versions = response.json()["items"]
            result = []
            
            for stack_version in stack_versions:
                stack_info = stack_version["ClusterStackVersionInfo"]
                result.append({
                    "stack_name": stack_info["stack"],
                    "stack_version": stack_info["version"],
                    "state": stack_info["state"],
                    "repository_version": stack_info.get("repository_version", "Unknown")
                })
            
            return json.dumps(result, indent=2) 