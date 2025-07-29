"""FastAPI REST interface for Ambari MCP Server demonstration."""

import asyncio
import json
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .server import AmbariMCPServer, OperationResult
from .config import Settings, get_settings, MCPModeType
from .client import AmbariAPIError


# Request/Response Models
class ModeSwitch(BaseModel):
    """Mode switch request."""
    mode: str = Field(..., description="Target mode (normal, cluster_maintenance, scale_up, config_edit, development)")
    reason: Optional[str] = Field(None, description="Reason for mode switch")


class ServiceOperation(BaseModel):
    """Service operation request."""
    service_name: str = Field(..., description="Name of the service")
    cluster_name: Optional[str] = Field(None, description="Cluster name (optional)")


class ConfigurationUpdate(BaseModel):
    """Configuration update request."""
    config_type: str = Field(..., description="Configuration type")
    properties: Dict[str, str] = Field(..., description="Configuration properties")
    cluster_name: Optional[str] = Field(None, description="Cluster name (optional)")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: str
    version: str
    mode: str
    ambari_connection: str


# Global MCP server instance
mcp_server: Optional[AmbariMCPServer] = None


def get_mcp_server() -> AmbariMCPServer:
    """Get the MCP server instance."""
    global mcp_server
    if mcp_server is None:
        raise HTTPException(status_code=500, detail="MCP server not initialized")
    return mcp_server


def create_app(settings: Settings) -> FastAPI:
    """Create and configure FastAPI application."""
    
    app = FastAPI(
        title="Ambari MCP Server API",
        description="REST API interface for Ambari Model Context Protocol Server",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Initialize MCP server
    global mcp_server
    mcp_server = AmbariMCPServer(settings)
    
    @app.on_event("startup")
    async def startup_event():
        """Application startup event."""
        pass
        
    @app.on_event("shutdown")
    async def shutdown_event():
        """Application shutdown event."""
        if mcp_server:
            await mcp_server.shutdown()
    
    # Health and Status Endpoints
    @app.get("/health", response_model=HealthResponse)
    async def health_check():
        """Health check endpoint."""
        server = get_mcp_server()
        try:
            # Test Ambari connection
            client = await server._get_client()
            ambari_health = await client.health_check()
            ambari_status = "healthy" if ambari_health["status"] == "healthy" else "degraded"
        except Exception:
            ambari_status = "unhealthy"
            
        return HealthResponse(
            status="healthy",
            timestamp=f"{asyncio.get_event_loop().time()}",
            version=settings.mcp_server.version,
            mode=server.mode_manager.get_current_mode().mode_type.value,
            ambari_connection=ambari_status
        )
    
    @app.get("/status")
    async def get_status():
        """Get comprehensive server status."""
        server = get_mcp_server()
        
        # Get mode information
        mode_info = server.mode_manager.get_mode_info()
        
        # Get cluster status if possible
        cluster_status = None
        try:
            client = await server._get_client()
            cluster_health = await client.health_check()
            cluster_status = cluster_health
        except Exception as e:
            cluster_status = {"status": "error", "reason": str(e)}
        
        return {
            "server": {
                "name": settings.mcp_server.name,
                "version": settings.mcp_server.version,
                "mode": mode_info
            },
            "ambari": {
                "host": settings.ambari.host,
                "port": settings.ambari.port,
                "cluster": cluster_status
            }
        }
    
    # Mode Management Endpoints
    @app.get("/modes")
    async def list_modes():
        """List all available operational modes."""
        server = get_mcp_server()
        modes = server.mode_manager.get_available_modes()
        return {"modes": {k.value: v for k, v in modes.items()}}
    
    @app.get("/modes/current")
    async def get_current_mode():
        """Get current operational mode."""
        server = get_mcp_server()
        return server.mode_manager.get_mode_info()
    
    @app.post("/modes/switch")
    async def switch_mode(request: ModeSwitch):
        """Switch operational mode."""
        server = get_mcp_server()
        try:
            mode_type = MCPModeType(request.mode.lower())
            server.mode_manager.switch_mode(mode_type)
            return {
                "success": True,
                "message": f"Switched to {request.mode} mode",
                "mode": server.mode_manager.get_mode_info()
            }
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    # Cluster Management Endpoints
    @app.get("/cluster/status")
    async def get_cluster_status(cluster_name: Optional[str] = None):
        """Get cluster status."""
        server = get_mcp_server()
        try:
            client = await server._get_client()
            cluster_info = await client.get_cluster_info(cluster_name)
            services = await client.get_services(cluster_name)
            hosts = await client.get_hosts(cluster_name)
            
            return {
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
        except AmbariAPIError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/cluster/health")
    async def cluster_health_check():
        """Perform cluster health check."""
        server = get_mcp_server()
        try:
            client = await server._get_client()
            health_status = await client.health_check()
            return health_status
        except AmbariAPIError as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    # Service Management Endpoints
    @app.get("/services")
    async def list_services(cluster_name: Optional[str] = None):
        """List all services."""
        server = get_mcp_server()
        if not server.mode_manager.can_execute_operation("list_services"):
            raise HTTPException(status_code=403, detail="Operation not allowed in current mode")
            
        try:
            client = await server._get_client()
            services = await client.get_services(cluster_name)
            return {"services": [s.dict() for s in services]}
        except AmbariAPIError as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    @app.get("/services/{service_name}")
    async def get_service_info(service_name: str, cluster_name: Optional[str] = None):
        """Get service information."""
        server = get_mcp_server()
        if not server.mode_manager.can_execute_operation("get_service_info"):
            raise HTTPException(status_code=403, detail="Operation not allowed in current mode")
            
        try:
            client = await server._get_client()
            service_info = await client.get_service_info(service_name, cluster_name)
            components = await client.get_components(service_name, cluster_name)
            
            return {
                "service": service_info.dict(),
                "components": [c.dict() for c in components]
            }
        except AmbariAPIError as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    @app.post("/services/{service_name}/start")
    async def start_service(service_name: str, background_tasks: BackgroundTasks, cluster_name: Optional[str] = None):
        """Start a service."""
        server = get_mcp_server()
        if not server.mode_manager.can_execute_operation("start_service"):
            raise HTTPException(status_code=403, detail="Operation not allowed in current mode")
            
        try:
            client = await server._get_client()
            result = await client.start_service(service_name, cluster_name)
            request_id = result.get("Requests", {}).get("id")
            
            return {
                "success": True,
                "message": f"Start request submitted for service {service_name}",
                "request_id": request_id,
                "result": result
            }
        except AmbariAPIError as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    @app.post("/services/{service_name}/stop")
    async def stop_service(service_name: str, background_tasks: BackgroundTasks, cluster_name: Optional[str] = None):
        """Stop a service."""
        server = get_mcp_server()
        if not server.mode_manager.can_execute_operation("stop_service"):
            raise HTTPException(status_code=403, detail="Operation not allowed in current mode")
            
        try:
            client = await server._get_client()
            result = await client.stop_service(service_name, cluster_name)
            request_id = result.get("Requests", {}).get("id")
            
            return {
                "success": True,
                "message": f"Stop request submitted for service {service_name}",
                "request_id": request_id,
                "result": result
            }
        except AmbariAPIError as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    @app.post("/services/{service_name}/restart")
    async def restart_service(service_name: str, background_tasks: BackgroundTasks, cluster_name: Optional[str] = None):
        """Restart a service."""
        server = get_mcp_server()
        if not server.mode_manager.can_execute_operation("restart_service"):
            raise HTTPException(status_code=403, detail="Operation not allowed in current mode")
            
        try:
            client = await server._get_client()
            result = await client.restart_service(service_name, cluster_name)
            request_id = result.get("Requests", {}).get("id")
            
            return {
                "success": True,
                "message": f"Restart request submitted for service {service_name}",
                "request_id": request_id,
                "result": result
            }
        except AmbariAPIError as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    # Host Management Endpoints
    @app.get("/hosts")
    async def list_hosts(cluster_name: Optional[str] = None):
        """List all hosts."""
        server = get_mcp_server()
        if not server.mode_manager.can_execute_operation("list_hosts"):
            raise HTTPException(status_code=403, detail="Operation not allowed in current mode")
            
        try:
            client = await server._get_client()
            hosts = await client.get_hosts(cluster_name)
            return {"hosts": [h.dict() for h in hosts]}
        except AmbariAPIError as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    @app.get("/hosts/{host_name}")
    async def get_host_info(host_name: str, cluster_name: Optional[str] = None):
        """Get host information."""
        server = get_mcp_server()
        if not server.mode_manager.can_execute_operation("get_host_info"):
            raise HTTPException(status_code=403, detail="Operation not allowed in current mode")
            
        try:
            client = await server._get_client()
            host_info = await client.get_host_info(host_name, cluster_name)
            return {"host": host_info.dict()}
        except AmbariAPIError as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    # Configuration Management Endpoints
    @app.get("/configurations/{config_type}")
    async def get_configurations(config_type: str, cluster_name: Optional[str] = None):
        """Get configuration."""
        server = get_mcp_server()
        if not server.mode_manager.can_execute_operation("get_configurations"):
            raise HTTPException(status_code=403, detail="Operation not allowed in current mode")
            
        try:
            client = await server._get_client()
            config = await client.get_configurations(config_type, cluster_name)
            return {"configuration": config}
        except AmbariAPIError as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    @app.put("/configurations/{config_type}")
    async def update_configuration(config_type: str, request: ConfigurationUpdate):
        """Update configuration."""
        server = get_mcp_server()
        if not server.mode_manager.can_execute_operation("update_configuration"):
            raise HTTPException(status_code=403, detail="Operation not allowed in current mode")
            
        try:
            client = await server._get_client()
            result = await client.update_configuration(config_type, request.properties, request.cluster_name)
            
            return {
                "success": True,
                "message": f"Configuration {config_type} updated successfully",
                "result": result
            }
        except AmbariAPIError as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    # Request Monitoring Endpoints
    @app.get("/requests/{request_id}")
    async def get_request_status(request_id: int, cluster_name: Optional[str] = None):
        """Get request status."""
        server = get_mcp_server()
        try:
            client = await server._get_client()
            status = await client.get_request_status(request_id, cluster_name)
            return {"request_status": status}
        except AmbariAPIError as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    @app.get("/requests")
    async def list_recent_requests(cluster_name: Optional[str] = None, limit: int = 10):
        """List recent requests."""
        server = get_mcp_server()
        try:
            client = await server._get_client()
            requests = await client.get_recent_requests(cluster_name, limit)
            return {"requests": requests}
        except AmbariAPIError as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    # MCP Integration Endpoints
    @app.get("/mcp/tools")
    async def list_mcp_tools():
        """List available MCP tools for current mode."""
        server = get_mcp_server()
        current_mode = server.mode_manager.get_current_mode()
        return {
            "mode": current_mode.mode_type.value,
            "tools": current_mode.get_available_tools(),
            "description": current_mode.get_description()
        }
    
    @app.get("/mcp/resources")
    async def list_mcp_resources():
        """List available MCP resources."""
        return {
            "resources": [
                "ambari://cluster/{cluster_name}/status",
                "ambari://mode/current", 
                "ambari://documentation/{doc_type}"
            ],
            "documentation_types": ["modes", "api"]
        }
    
    @app.get("/mcp/prompts")
    async def list_mcp_prompts():
        """List available MCP prompts."""
        server = get_mcp_server()
        current_mode = server.mode_manager.get_current_mode()
        return {
            "prompts": current_mode.get_context_prompts(),
            "available_prompts": [
                "cluster_overview",
                "service_management", 
                "maintenance_checklist",
                "scale_up_planning",
                "configuration_management"
            ]
        }
    
    return app


# Create the FastAPI app instance
def get_fastapi_app() -> FastAPI:
    """Get configured FastAPI application."""
    settings = get_settings()
    return create_app(settings) 