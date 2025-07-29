"""Main MCP server implementation for Ambari operations."""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from mcp.server.fastmcp import FastMCP, Context
from mcp.server.fastmcp.prompts import base
from pydantic import BaseModel, Field

from .client import AmbariClient, AmbariAPIError
from .config import Settings, MCPModeType
from .modes import MCPModeManager, ModeContext


class OperationResult(BaseModel):
    """Standard result format for operations."""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    request_id: Optional[int] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class ConfirmationRequest(BaseModel):
    """Confirmation request for dangerous operations."""
    operation: str
    target: str
    reason: str
    confirmation_required: bool = True


class AmbariMCPServer:
    """MCP Server for Apache Ambari operations."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.mode_manager = MCPModeManager()
        self.ambari_client: Optional[AmbariClient] = None
        
        # Initialize FastMCP server
        self.mcp = FastMCP(
            name=settings.mcp_server.name,
            version=settings.mcp_server.version
        )
        
        # Set initial mode
        initial_mode = settings.mcp_server.mode
        self.mode_manager.switch_mode(initial_mode)
        
        # Register tools, resources, and prompts
        self._register_tools()
        self._register_resources()
        self._register_prompts()
        
    async def _get_client(self) -> AmbariClient:
        """Get or create Ambari client."""
        if self.ambari_client is None:
            self.ambari_client = AmbariClient(self.settings.ambari)
            await self.ambari_client.connect()
        return self.ambari_client
        
    def _check_operation_allowed(self, operation: str) -> bool:
        """Check if operation is allowed in current mode."""
        return self.mode_manager.can_execute_operation(operation)
        
    def _requires_confirmation(self, operation: str) -> bool:
        """Check if operation requires confirmation."""
        return self.mode_manager.requires_confirmation(operation)
        
    def _register_tools(self):
        """Register all MCP tools."""
        
        # Mode Management Tools
        @self.mcp.tool()
        async def switch_mode(mode: str, context: Context, reason: Optional[str] = None) -> OperationResult:
            """Switch MCP operational mode."""
            try:
                mode_type = MCPModeType(mode.lower())
                mode_context = ModeContext(
                    mode_type=mode_type,
                    session_id=getattr(context, 'session_id', None),
                    initiated_at=datetime.utcnow().isoformat(),
                    metadata={"reason": reason} if reason else {}
                )
                
                new_mode = self.mode_manager.switch_mode(mode_type, mode_context)
                await context.info(f"Switched to {mode_type.value} mode")
                
                return OperationResult(
                    success=True,
                    message=f"Successfully switched to {mode_type.value} mode",
                    data=self.mode_manager.get_mode_info()
                )
            except ValueError as e:
                return OperationResult(success=False, message=str(e))
                
        @self.mcp.tool()
        async def get_current_mode(context: Context) -> OperationResult:
            """Get current operational mode information."""
            return OperationResult(
                success=True,
                message="Current mode information retrieved",
                data=self.mode_manager.get_mode_info()
            )
            
        @self.mcp.tool()
        async def list_available_modes(context: Context) -> OperationResult:
            """List all available operational modes."""
            modes = self.mode_manager.get_available_modes()
            return OperationResult(
                success=True,
                message="Available modes retrieved",
                data={"modes": {k.value: v for k, v in modes.items()}}
            )
        
        # Cluster Operations
        @self.mcp.tool()
        async def get_cluster_status(context: Context, cluster_name: Optional[str] = None) -> OperationResult:
            """Get comprehensive cluster status information."""
            if not self._check_operation_allowed("get_cluster_status"):
                return OperationResult(success=False, message="Operation not allowed in current mode")
                
            try:
                client = await self._get_client()
                cluster_info = await client.get_cluster_info(cluster_name)
                services = await client.get_services(cluster_name)
                hosts = await client.get_hosts(cluster_name)
                
                return OperationResult(
                    success=True,
                    message="Cluster status retrieved successfully",
                    data={
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
            except AmbariAPIError as e:
                return OperationResult(success=False, message=f"Ambari API error: {str(e)}")
            except Exception as e:
                return OperationResult(success=False, message=f"Unexpected error: {str(e)}")
        
        # Service Operations
        @self.mcp.tool()
        async def list_services(context: Context, cluster_name: Optional[str] = None) -> OperationResult:
            """List all services in the cluster."""
            if not self._check_operation_allowed("list_services"):
                return OperationResult(success=False, message="Operation not allowed in current mode")
                
            try:
                client = await self._get_client()
                services = await client.get_services(cluster_name)
                
                return OperationResult(
                    success=True,
                    message="Services retrieved successfully",
                    data={"services": [s.dict() for s in services]}
                )
            except AmbariAPIError as e:
                return OperationResult(success=False, message=f"Ambari API error: {str(e)}")
                
        @self.mcp.tool()
        async def get_service_info(service_name: str, context: Context, cluster_name: Optional[str] = None) -> OperationResult:
            """Get detailed information about a specific service."""
            if not self._check_operation_allowed("get_service_info"):
                return OperationResult(success=False, message="Operation not allowed in current mode")
                
            try:
                client = await self._get_client()
                service_info = await client.get_service_info(service_name, cluster_name)
                components = await client.get_components(service_name, cluster_name)
                
                return OperationResult(
                    success=True,
                    message=f"Service {service_name} information retrieved",
                    data={
                        "service": service_info.dict(),
                        "components": [c.dict() for c in components]
                    }
                )
            except AmbariAPIError as e:
                return OperationResult(success=False, message=f"Ambari API error: {str(e)}")
                
        @self.mcp.tool()
        async def start_service(service_name: str, context: Context, cluster_name: Optional[str] = None) -> OperationResult:
            """Start a service."""
            if not self._check_operation_allowed("start_service"):
                return OperationResult(success=False, message="Operation not allowed in current mode")
                
            if self._requires_confirmation("start_service"):
                await context.info(f"⚠️ Starting service {service_name} - this may take several minutes")
                
            try:
                client = await self._get_client()
                result = await client.start_service(service_name, cluster_name)
                request_id = result.get("Requests", {}).get("id")
                
                await context.info(f"Service start request submitted for {service_name}")
                
                return OperationResult(
                    success=True,
                    message=f"Start request submitted for service {service_name}",
                    data=result,
                    request_id=request_id
                )
            except AmbariAPIError as e:
                return OperationResult(success=False, message=f"Ambari API error: {str(e)}")
                
        @self.mcp.tool()
        async def stop_service(service_name: str, context: Context, cluster_name: Optional[str] = None) -> OperationResult:
            """Stop a service."""
            if not self._check_operation_allowed("stop_service"):
                return OperationResult(success=False, message="Operation not allowed in current mode")
                
            if self._requires_confirmation("stop_service"):
                await context.warning(f"⚠️ Stopping service {service_name} - this will affect cluster functionality")
                
            try:
                client = await self._get_client()
                result = await client.stop_service(service_name, cluster_name)
                request_id = result.get("Requests", {}).get("id")
                
                await context.info(f"Service stop request submitted for {service_name}")
                
                return OperationResult(
                    success=True,
                    message=f"Stop request submitted for service {service_name}",
                    data=result,
                    request_id=request_id
                )
            except AmbariAPIError as e:
                return OperationResult(success=False, message=f"Ambari API error: {str(e)}")
                
        @self.mcp.tool()
        async def restart_service(service_name: str, context: Context, cluster_name: Optional[str] = None) -> OperationResult:
            """Restart a service."""
            if not self._check_operation_allowed("restart_service"):
                return OperationResult(success=False, message="Operation not allowed in current mode")
                
            if self._requires_confirmation("restart_service"):
                await context.warning(f"⚠️ Restarting service {service_name} - this will cause temporary service interruption")
                
            try:
                client = await self._get_client()
                result = await client.restart_service(service_name, cluster_name)
                request_id = result.get("Requests", {}).get("id")
                
                await context.info(f"Service restart request submitted for {service_name}")
                
                return OperationResult(
                    success=True,
                    message=f"Restart request submitted for service {service_name}",
                    data=result,
                    request_id=request_id
                )
            except AmbariAPIError as e:
                return OperationResult(success=False, message=f"Ambari API error: {str(e)}")
        
        # Host Operations
        @self.mcp.tool()
        async def list_hosts(context: Context, cluster_name: Optional[str] = None) -> OperationResult:
            """List all hosts in the cluster."""
            if not self._check_operation_allowed("list_hosts"):
                return OperationResult(success=False, message="Operation not allowed in current mode")
                
            try:
                client = await self._get_client()
                hosts = await client.get_hosts(cluster_name)
                
                return OperationResult(
                    success=True,
                    message="Hosts retrieved successfully",
                    data={"hosts": [h.dict() for h in hosts]}
                )
            except AmbariAPIError as e:
                return OperationResult(success=False, message=f"Ambari API error: {str(e)}")
                
        @self.mcp.tool()
        async def get_host_info(host_name: str, context: Context, cluster_name: Optional[str] = None) -> OperationResult:
            """Get detailed information about a specific host."""
            if not self._check_operation_allowed("get_host_info"):
                return OperationResult(success=False, message="Operation not allowed in current mode")
                
            try:
                client = await self._get_client()
                host_info = await client.get_host_info(host_name, cluster_name)
                
                return OperationResult(
                    success=True,
                    message=f"Host {host_name} information retrieved",
                    data={"host": host_info.dict()}
                )
            except AmbariAPIError as e:
                return OperationResult(success=False, message=f"Ambari API error: {str(e)}")
        
        # Component Operations
        @self.mcp.tool()
        async def get_service_components(service_name: str, context: Context, cluster_name: Optional[str] = None) -> OperationResult:
            """Get all components for a specific service."""
            if not self._check_operation_allowed("get_service_components"):
                return OperationResult(success=False, message="Operation not allowed in current mode")
                
            try:
                client = await self._get_client()
                components = await client.get_components(service_name, cluster_name)
                
                return OperationResult(
                    success=True,
                    message=f"Components for service {service_name} retrieved",
                    data={"components": [c.dict() for c in components]}
                )
            except AmbariAPIError as e:
                return OperationResult(success=False, message=f"Ambari API error: {str(e)}")
        
        # Configuration Operations
        @self.mcp.tool()
        async def get_configurations(config_type: str, context: Context, cluster_name: Optional[str] = None) -> OperationResult:
            """Get configuration for a specific type."""
            if not self._check_operation_allowed("get_configurations"):
                return OperationResult(success=False, message="Operation not allowed in current mode")
                
            try:
                client = await self._get_client()
                config = await client.get_configurations(config_type, cluster_name)
                
                return OperationResult(
                    success=True,
                    message=f"Configuration {config_type} retrieved",
                    data={"configuration": config}
                )
            except AmbariAPIError as e:
                return OperationResult(success=False, message=f"Ambari API error: {str(e)}")
                
        @self.mcp.tool()
        async def update_configuration(config_type: str, properties: str, context: Context, cluster_name: Optional[str] = None) -> OperationResult:
            """Update configuration properties (properties should be JSON string)."""
            if not self._check_operation_allowed("update_configuration"):
                return OperationResult(success=False, message="Operation not allowed in current mode")
                
            if self._requires_confirmation("update_configuration"):
                await context.warning(f"⚠️ Updating configuration {config_type} - this may require service restarts")
                
            try:
                # Parse properties JSON
                props_dict = json.loads(properties)
                
                client = await self._get_client()
                result = await client.update_configuration(config_type, props_dict, cluster_name)
                
                await context.info(f"Configuration {config_type} updated successfully")
                
                return OperationResult(
                    success=True,
                    message=f"Configuration {config_type} updated successfully",
                    data=result
                )
            except json.JSONDecodeError:
                return OperationResult(success=False, message="Invalid JSON format for properties")
            except AmbariAPIError as e:
                return OperationResult(success=False, message=f"Ambari API error: {str(e)}")
        
        # Request Operations
        @self.mcp.tool()
        async def get_request_status(request_id: int, context: Context, cluster_name: Optional[str] = None) -> OperationResult:
            """Get the status of a request."""
            if not self._check_operation_allowed("get_request_status"):
                return OperationResult(success=False, message="Operation not allowed in current mode")
                
            try:
                client = await self._get_client()
                status = await client.get_request_status(request_id, cluster_name)
                
                return OperationResult(
                    success=True,
                    message=f"Request {request_id} status retrieved",
                    data={"request_status": status}
                )
            except AmbariAPIError as e:
                return OperationResult(success=False, message=f"Ambari API error: {str(e)}")
                
        @self.mcp.tool()
        async def list_recent_requests(context: Context, cluster_name: Optional[str] = None, limit: int = 10) -> OperationResult:
            """List recent requests."""
            if not self._check_operation_allowed("list_recent_requests"):
                return OperationResult(success=False, message="Operation not allowed in current mode")
                
            try:
                client = await self._get_client()
                requests = await client.get_recent_requests(cluster_name, limit)
                
                return OperationResult(
                    success=True,
                    message="Recent requests retrieved",
                    data={"requests": requests}
                )
            except AmbariAPIError as e:
                return OperationResult(success=False, message=f"Ambari API error: {str(e)}")
        
        # Health Check
        @self.mcp.tool()
        async def health_check(context: Context) -> OperationResult:
            """Perform comprehensive health check of the Ambari cluster."""
            try:
                client = await self._get_client()
                health_status = await client.health_check()
                
                if health_status["status"] == "healthy":
                    await context.info("✅ Cluster health check passed")
                elif health_status["status"] == "degraded":
                    await context.warning("⚠️ Cluster health check shows degraded status")
                else:
                    await context.error("❌ Cluster health check failed")
                
                return OperationResult(
                    success=True,
                    message="Health check completed",
                    data=health_status
                )
            except AmbariAPIError as e:
                return OperationResult(success=False, message=f"Ambari API error: {str(e)}")
    
    def _register_resources(self):
        """Register MCP resources."""
        
        @self.mcp.resource("ambari://cluster/{cluster_name}/status")
        async def cluster_status_resource(cluster_name: str) -> str:
            """Get cluster status as a resource."""
            try:
                client = await self._get_client()
                cluster_info = await client.get_cluster_info(cluster_name)
                services = await client.get_services(cluster_name)
                
                status_info = {
                    "cluster": cluster_info.dict(),
                    "services_summary": {
                        "total": len(services),
                        "running": len([s for s in services if s.state == "STARTED"]),
                        "stopped": len([s for s in services if s.state == "INSTALLED"])
                    }
                }
                return json.dumps(status_info, indent=2)
            except Exception as e:
                return f"Error retrieving cluster status: {str(e)}"
                
        @self.mcp.resource("ambari://mode/current")
        async def current_mode_resource() -> str:
            """Get current operational mode as a resource."""
            mode_info = self.mode_manager.get_mode_info()
            return json.dumps(mode_info, indent=2)
            
        @self.mcp.resource("ambari://documentation/{doc_type}")
        async def documentation_resource(doc_type: str) -> str:
            """Get documentation for various topics."""
            docs = {
                "modes": """
# MCP Operational Modes

## Normal Mode
- Full access to all operations
- Confirmations required for dangerous operations
- Best for general cluster management

## Cluster Maintenance Mode  
- Restricted to monitoring and safe shutdown operations
- Configuration changes disabled
- Ideal for maintenance windows

## Scale Up Mode
- Optimized for adding capacity
- Service shutdowns disabled
- Higher concurrency limits

## Config Edit Mode
- Focused on configuration management
- Service operations disabled
- Safe configuration editing

## Development Mode
- All operations allowed without confirmation
- Enhanced logging and debugging
- Rapid development and testing
                """,
                "api": """
# Ambari API Operations

## Service Management
- start_service: Start a stopped service
- stop_service: Stop a running service  
- restart_service: Restart a service
- get_service_info: Get detailed service information

## Cluster Operations
- get_cluster_status: Get comprehensive cluster status
- list_services: List all services
- list_hosts: List all hosts
- health_check: Perform cluster health check

## Configuration Management
- get_configurations: Retrieve configuration
- update_configuration: Update configuration properties

## Monitoring
- get_request_status: Check operation status
- list_recent_requests: View recent operations
                """
            }
            return docs.get(doc_type, f"Documentation not found for: {doc_type}")
    
    def _register_prompts(self):
        """Register MCP prompts."""
        
        @self.mcp.prompt()
        async def cluster_overview(cluster_name: Optional[str] = None) -> str:
            """Generate a comprehensive cluster overview prompt."""
            return f"""
Please provide a comprehensive overview of the Ambari cluster{f' "{cluster_name}"' if cluster_name else ''}. 

Include:
1. Overall cluster health status
2. Service states and any issues
3. Host health and capacity
4. Recent operations or changes
5. Recommendations for any issues found

Use the available tools to gather this information and present it in a clear, actionable format.
            """.strip()
            
        @self.mcp.prompt()
        async def service_management(service_name: str, operation: str = "status") -> str:
            """Generate service management prompts."""
            return f"""
Please help manage the {service_name} service with the following operation: {operation}

Steps to follow:
1. Check current service status
2. Verify service dependencies
3. {'Execute the operation safely' if operation != 'status' else 'Provide detailed status information'}
4. Monitor the operation progress
5. Verify successful completion

Consider the current operational mode and any restrictions that may apply.
            """.strip()
            
        @self.mcp.prompt()
        async def maintenance_checklist(cluster_name: Optional[str] = None) -> List[base.Message]:
            """Generate maintenance checklist prompt."""
            return [
                base.UserMessage("I need to perform cluster maintenance. Please guide me through the process."),
                base.AssistantMessage("""
I'll help you with cluster maintenance. Here's a systematic approach:

**Pre-Maintenance Checklist:**
1. Switch to cluster_maintenance mode for safety
2. Check current cluster health status
3. Identify running services and their dependencies
4. Review recent operations for any ongoing tasks
5. Plan service shutdown sequence

**During Maintenance:**
1. Stop services in proper order (applications first, then infrastructure)
2. Monitor each shutdown operation
3. Verify all services are properly stopped
4. Perform your maintenance tasks

**Post-Maintenance:**
1. Start services in reverse order (infrastructure first)
2. Verify all services are healthy
3. Run comprehensive health check
4. Switch back to normal operational mode

Would you like me to start by checking the current cluster status?
                """),
            ]
            
        @self.mcp.prompt()
        async def scale_up_planning(target_capacity: Optional[str] = None) -> str:
            """Generate scale-up planning prompt."""
            return f"""
Please help plan a cluster scale-up operation{f' to {target_capacity}' if target_capacity else ''}.

Analysis needed:
1. Current cluster capacity and utilization
2. Service distribution across hosts
3. Resource bottlenecks and constraints
4. Configuration changes needed for scaling
5. Service restart requirements

Switch to scale_up mode and provide a detailed scaling plan with step-by-step instructions.
            """.strip()
            
        @self.mcp.prompt()
        async def configuration_management(config_type: str, operation: str = "view") -> str:
            """Generate configuration management prompts."""
            return f"""
Please help with {config_type} configuration management - operation: {operation}

Process:
1. Switch to config_edit mode for safety
2. Retrieve current {config_type} configuration
3. {'Analyze configuration and suggest improvements' if operation == 'view' else f'Prepare for {operation} operation'}
4. {'Show configuration in readable format' if operation == 'view' else 'Execute configuration changes safely'}
5. Validate configuration changes
6. Document changes made

Ensure all changes follow best practices and maintain cluster stability.
            """.strip()

    async def run_stdio(self):
        """Run the MCP server with stdio transport."""
        await self.mcp.run_stdio_async()
        
    async def run_sse(self, host: str = "0.0.0.0", port: int = 8001):
        """Run the MCP server with SSE transport."""
        await self.mcp.run_sse_async(host=host, port=port)
        
    async def run_streamable_http(self, host: str = "0.0.0.0", port: int = 8001):
        """Run the MCP server with streamable HTTP transport."""
        await self.mcp.run_streamable_http_async(host=host, port=port)
        
    async def shutdown(self):
        """Shutdown the server and cleanup resources."""
        if self.ambari_client:
            await self.ambari_client.disconnect()
            self.ambari_client = None 