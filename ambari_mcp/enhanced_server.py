"""Enhanced MCP server with context-driven Ambari connections."""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from mcp.server.fastmcp import FastMCP, Context
from pydantic import BaseModel, Field

from .dynamic_client import DynamicAmbariClientManager, AmbariTarget
from .config import Settings
from .modes import MCPModeManager, ModeContext
from .server import OperationResult


class AmbariConnectionContext(BaseModel):
    """Ambari connection context from LLM."""
    target_name: Optional[str] = Field(None, description="Named target identifier")
    ambari_host: str = Field(..., description="Ambari server hostname or IP")
    ambari_port: int = Field(default=8080, description="Ambari server port")
    ambari_username: str = Field(default="admin", description="Ambari username")
    ambari_password: str = Field(default="admin", description="Ambari password")
    ambari_use_ssl: bool = Field(default=False, description="Use SSL for connection")
    cluster_name: Optional[str] = Field(None, description="Target cluster name")
    environment: Optional[str] = Field(None, description="Environment (dev/staging/prod)")


class EnhancedAmbariMCPServer:
    """Enhanced MCP Server with dynamic Ambari connections."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.mode_manager = MCPModeManager()
        self.client_manager = DynamicAmbariClientManager()
        
        # Initialize FastMCP server
        self.mcp = FastMCP(
            name=settings.mcp_server.name,
            version=settings.mcp_server.version
        )
        
        # Set initial mode
        initial_mode = settings.mcp_server.mode
        self.mode_manager.switch_mode(initial_mode)
        
        # Register enhanced tools
        self._register_enhanced_tools()
        self._register_connection_management_tools()
        self._register_resources()
        self._register_prompts()
        
    async def _resolve_target(self, connection_context: Optional[Dict[str, Any]], context: Context) -> str:
        """Resolve target from connection context or discover from registered targets."""
        
        if not connection_context:
            # Try to use default target if only one is registered
            targets = self.client_manager.list_targets()
            if len(targets) == 1:
                return list(targets.keys())[0]
            elif len(targets) == 0:
                raise ValueError("No Ambari targets configured. Please provide connection details.")
            else:
                raise ValueError(f"Multiple targets available: {list(targets.keys())}. Please specify target_name.")
        
        # Try to discover existing target
        target_name = await self.client_manager.discover_targets_from_context(connection_context)
        
        if not target_name:
            # Auto-register from context
            target_name = await self.client_manager.auto_register_from_context(connection_context)
            if target_name:
                await context.info(f"Registered new Ambari target: {target_name}")
            else:
                raise ValueError("Could not resolve or create Ambari target from context")
                
        return target_name
        
    def _register_connection_management_tools(self):
        """Register tools for managing Ambari connections."""
        
        @self.mcp.tool()
        async def register_ambari_target(
            target_name: str,
            ambari_host: str,
            context: Context,
            ambari_port: int = 8080,
            ambari_username: str = "admin", 
            ambari_password: str = "admin",
            ambari_use_ssl: bool = False,
            cluster_name: Optional[str] = None
        ) -> OperationResult:
            """Register a new Ambari cluster target for future operations."""
            try:
                target = AmbariTarget(
                    name=target_name,
                    host=ambari_host,
                    port=ambari_port,
                    username=ambari_username,
                    password=ambari_password,
                    use_ssl=ambari_use_ssl,
                    cluster_name=cluster_name
                )
                
                self.client_manager.register_target(target)
                await context.info(f"Registered Ambari target: {target_name}")
                
                return OperationResult(
                    success=True,
                    message=f"Successfully registered Ambari target '{target_name}'",
                    data={"target_name": target_name, "host": ambari_host, "port": ambari_port}
                )
            except Exception as e:
                return OperationResult(success=False, message=f"Failed to register target: {str(e)}")
                
        @self.mcp.tool()
        async def list_ambari_targets(context: Context) -> OperationResult:
            """List all registered Ambari cluster targets."""
            targets = self.client_manager.list_targets()
            return OperationResult(
                success=True,
                message=f"Found {len(targets)} registered targets",
                data={"targets": targets}
            )
            
        @self.mcp.tool()
        async def test_ambari_connection(
            context: Context,
            target_name: Optional[str] = None,
            ambari_host: Optional[str] = None,
            ambari_port: int = 8080,
            ambari_username: str = "admin",
            ambari_password: str = "admin",
            ambari_use_ssl: bool = False
        ) -> OperationResult:
            """Test connection to an Ambari cluster."""
            try:
                # Build connection context
                conn_context = None
                if ambari_host:
                    conn_context = {
                        "target_name": target_name or f"test-{ambari_host}",
                        "ambari_host": ambari_host,
                        "ambari_port": ambari_port,
                        "ambari_username": ambari_username,
                        "ambari_password": ambari_password,
                        "ambari_use_ssl": ambari_use_ssl
                    }
                elif target_name:
                    conn_context = {"target_name": target_name}
                
                resolved_target = await self._resolve_target(conn_context, context)
                
                async with self.client_manager.client_for_target(resolved_target) as client:
                    health = await client.health_check()
                    
                return OperationResult(
                    success=True,
                    message=f"Connection test successful for target '{resolved_target}'",
                    data={"target": resolved_target, "health": health}
                )
            except Exception as e:
                return OperationResult(success=False, message=f"Connection test failed: {str(e)}")
                
        @self.mcp.tool()
        async def health_check_all_targets(context: Context) -> OperationResult:
            """Health check all registered Ambari targets."""
            try:
                results = await self.client_manager.health_check_all()
                healthy_count = sum(1 for r in results.values() if r["status"] == "healthy")
                
                return OperationResult(
                    success=True,
                    message=f"Health check completed: {healthy_count}/{len(results)} targets healthy",
                    data={"results": results}
                )
            except Exception as e:
                return OperationResult(success=False, message=f"Health check failed: {str(e)}")
        
    def _register_enhanced_tools(self):
        """Register enhanced tools that accept connection context."""
        
        @self.mcp.tool()
        async def get_cluster_status_enhanced(
            context: Context,
            target_name: Optional[str] = None,
            ambari_host: Optional[str] = None,
            ambari_port: int = 8080,
            ambari_username: str = "admin",
            ambari_password: str = "admin",
            ambari_use_ssl: bool = False,
            cluster_name: Optional[str] = None
        ) -> OperationResult:
            """Get comprehensive cluster status with dynamic connection."""
            if not self._check_operation_allowed("get_cluster_status"):
                return OperationResult(success=False, message="Operation not allowed in current mode")
                
            try:
                # Build connection context
                conn_context = None
                if ambari_host:
                    conn_context = {
                        "target_name": target_name,
                        "ambari_host": ambari_host,
                        "ambari_port": ambari_port,
                        "ambari_username": ambari_username,
                        "ambari_password": ambari_password,
                        "ambari_use_ssl": ambari_use_ssl,
                        "cluster_name": cluster_name
                    }
                elif target_name:
                    conn_context = {"target_name": target_name}
                
                resolved_target = await self._resolve_target(conn_context, context)
                
                async with self.client_manager.client_for_target(resolved_target) as client:
                    cluster_info = await client.get_cluster_info(cluster_name)
                    services = await client.get_services(cluster_name)
                    hosts = await client.get_hosts(cluster_name)
                    
                    return OperationResult(
                        success=True,
                        message=f"Cluster status retrieved from {resolved_target}",
                        data={
                            "target": resolved_target,
                            "cluster": cluster_info.dict(),
                            "services": [s.dict() for s in services],
                            "hosts": [h.dict() for h in hosts],
                            "summary": {
                                "total_services": len(services),
                                "running_services": len([s for s in services if s.state == "STARTED"]),
                                "total_hosts": len(hosts),
                                "healthy_hosts": len([h for h in hosts if h.health_status == "HEALTHY"])
                            }
                        }
                    )
            except Exception as e:
                return OperationResult(success=False, message=f"Failed to get cluster status: {str(e)}")
                
        @self.mcp.tool()
        async def start_service_enhanced(
            service_name: str,
            context: Context,
            target_name: Optional[str] = None,
            ambari_host: Optional[str] = None,
            ambari_port: int = 8080,
            ambari_username: str = "admin",
            ambari_password: str = "admin",
            cluster_name: Optional[str] = None
        ) -> OperationResult:
            """Start a service with dynamic connection."""
            if not self._check_operation_allowed("start_service"):
                return OperationResult(success=False, message="Operation not allowed in current mode")
                
            try:
                # Build connection context  
                conn_context = None
                if ambari_host:
                    conn_context = {
                        "target_name": target_name,
                        "ambari_host": ambari_host,
                        "ambari_port": ambari_port,
                        "ambari_username": ambari_username,
                        "ambari_password": ambari_password,
                        "cluster_name": cluster_name
                    }
                elif target_name:
                    conn_context = {"target_name": target_name}
                
                resolved_target = await self._resolve_target(conn_context, context)
                
                if self._requires_confirmation("start_service"):
                    await context.info(f"⚠️ Starting service {service_name} on {resolved_target}")
                
                async with self.client_manager.client_for_target(resolved_target) as client:
                    result = await client.start_service(service_name, cluster_name)
                    request_id = result.get("Requests", {}).get("id")
                    
                    await context.info(f"Service start request submitted for {service_name} on {resolved_target}")
                    
                    return OperationResult(
                        success=True,
                        message=f"Start request submitted for service {service_name} on {resolved_target}",
                        data={"target": resolved_target, "result": result},
                        request_id=request_id
                    )
            except Exception as e:
                return OperationResult(success=False, message=f"Failed to start service: {str(e)}")
        
        # Add more enhanced tools following the same pattern...
        
    def _register_resources(self):
        """Register MCP resources."""
        
        @self.mcp.resource("ambari://targets/list")
        async def targets_list_resource() -> str:
            """Get list of registered Ambari targets as a resource."""
            targets = self.client_manager.list_targets()
            return json.dumps({"targets": targets}, indent=2)
            
        @self.mcp.resource("ambari://target/{target_name}/status")
        async def target_status_resource(target_name: str) -> str:
            """Get target-specific cluster status as a resource."""
            try:
                async with self.client_manager.client_for_target(target_name) as client:
                    cluster_info = await client.get_cluster_info()
                    services = await client.get_services()
                    
                    status_info = {
                        "target": target_name,
                        "cluster": cluster_info.dict(),
                        "services_summary": {
                            "total": len(services),
                            "running": len([s for s in services if s.state == "STARTED"]),
                            "stopped": len([s for s in services if s.state == "INSTALLED"])
                        }
                    }
                    return json.dumps(status_info, indent=2)
            except Exception as e:
                return f"Error retrieving status for target {target_name}: {str(e)}"
        
    def _register_prompts(self):
        """Register enhanced prompts."""
        
        @self.mcp.prompt()
        async def multi_cluster_overview(environment: Optional[str] = None) -> str:
            """Generate multi-cluster overview prompt."""
            return f"""
Please provide a comprehensive overview across all registered Ambari clusters{f' in {environment} environment' if environment else ''}.

For each cluster:
1. Overall cluster health status
2. Service states and any issues
3. Host health and capacity
4. Recent operations or changes
5. Cross-cluster comparison and recommendations

Use the list_ambari_targets and health_check_all_targets tools to gather information across all clusters.
            """.strip()
            
        @self.mcp.prompt()
        async def context_driven_operation(operation: str, context_hints: str) -> str:
            """Generate context-driven operation prompt."""
            return f"""
I need to perform the operation '{operation}' but I'm not sure which Ambari cluster to target.

Context hints: {context_hints}

Please help me:
1. Identify the appropriate Ambari cluster based on the context
2. If connection details are needed, guide me on what information to provide
3. Execute the operation safely with proper confirmations
4. Monitor the operation progress

Available options:
- Use registered targets if available (check with list_ambari_targets)
- Provide connection details directly in the tool call
- Register a new target for future use
            """.strip()
    
    def _check_operation_allowed(self, operation: str) -> bool:
        """Check if operation is allowed in current mode."""
        return self.mode_manager.can_execute_operation(operation)
        
    def _requires_confirmation(self, operation: str) -> bool:
        """Check if operation requires confirmation."""
        return self.mode_manager.requires_confirmation(operation)
        
    async def run_stdio(self):
        """Run the MCP server with stdio transport."""
        await self.mcp.run(transport="stdio")
        
    async def run_sse(self, host: str = "0.0.0.0", port: int = 8001):
        """Run the MCP server with SSE transport."""
        await self.mcp.run(transport="sse", host=host, port=port)
        
    async def run_streamable_http(self, host: str = "0.0.0.0", port: int = 8001):
        """Run the MCP server with streamable HTTP transport."""
        await self.mcp.run(transport="streamable-http", host=host, port=port)
        
    async def shutdown(self):
        """Shutdown the server and cleanup resources."""
        await self.client_manager.cleanup() 