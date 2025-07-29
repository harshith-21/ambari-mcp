"""Ambari API client for interacting with Apache Ambari REST API."""

import asyncio
import json
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urljoin

import httpx
from pydantic import BaseModel, Field

from .config import AmbariConfig


class AmbariAPIError(Exception):
    """Custom exception for Ambari API errors."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[Dict] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class ServiceInfo(BaseModel):
    """Service information model."""
    service_name: str
    state: str = Field(default="UNKNOWN")
    maintenance_state: str = Field(default="OFF")


class HostInfo(BaseModel):
    """Host information model."""
    host_name: str = Field(alias="host_name")
    host_state: str = Field(alias="host_state") 
    health_status: str = Field(alias="health_status")
    maintenance_state: str = Field(alias="maintenance_state", default="OFF")
    
    class Config:
        allow_population_by_field_name = True


class ComponentInfo(BaseModel):
    """Component information model."""
    component_name: str = Field(alias="component_name")
    service_name: str = Field(alias="service_name")
    state: str
    host_name: str = Field(alias="host_name")
    
    class Config:
        allow_population_by_field_name = True


class ClusterInfo(BaseModel):
    """Cluster information model."""
    cluster_name: str = Field(alias="cluster_name")
    version: str
    total_hosts: int = Field(alias="total_hosts")
    health: str = Field(default="UNKNOWN")
    
    class Config:
        allow_population_by_field_name = True


class AmbariClient:
    """Asynchronous client for Ambari REST API operations."""
    
    def __init__(self, config: AmbariConfig):
        self.config = config
        self.client: Optional[httpx.AsyncClient] = None
        self._session_id: Optional[str] = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
        
    async def connect(self) -> None:
        """Initialize the HTTP client and authenticate."""
        if self.client is None:
            timeout = httpx.Timeout(self.config.timeout)
            # Don't set default headers - Ambari is picky about Accept headers
            self.client = httpx.AsyncClient(
                auth=(self.config.username, self.config.password),
                timeout=timeout,
                verify=self.config.use_ssl
            )
            
    async def disconnect(self) -> None:
        """Close the HTTP client."""
        if self.client:
            await self.client.aclose()
            self.client = None
            
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make an authenticated request to Ambari API."""
        if not self.client:
            await self.connect()
            
        url = urljoin(self.config.base_url + '/', endpoint.lstrip('/'))
        
        for attempt in range(self.config.max_retries):
            try:
                # Prepare headers for this request
                request_headers = {}
                
                # Add CSRF protection header for write operations
                if method.upper() in ['POST', 'PUT', 'DELETE']:
                    request_headers["X-Requested-By"] = "ambari-mcp-client"
                
                # Add content-type header if we have data
                if data is not None:
                    request_headers["Content-Type"] = "application/json"
                
                response = await self.client.request(
                    method=method,
                    url=url,
                    json=data,
                    params=params,
                    headers=request_headers
                )
                
                if response.status_code == 401:
                    raise AmbariAPIError("Authentication failed", 401)
                elif response.status_code == 403:
                    raise AmbariAPIError("Access forbidden", 403)
                elif response.status_code == 404:
                    raise AmbariAPIError("Resource not found", 404)
                elif response.status_code >= 400:
                    error_msg = f"API request failed with status {response.status_code}"
                    try:
                        error_data = response.json()
                        if "message" in error_data:
                            error_msg += f": {error_data['message']}"
                    except:
                        error_msg += f": {response.text}"
                    raise AmbariAPIError(error_msg, response.status_code, response.json() if response.content else None)
                
                return response.json() if response.content else {}
                
            except httpx.RequestError as e:
                if attempt == self.config.max_retries - 1:
                    raise AmbariAPIError(f"Request failed after {self.config.max_retries} attempts: {str(e)}")
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                
    # Cluster Operations
    async def get_clusters(self) -> List[ClusterInfo]:
        """Get all clusters."""
        response = await self._make_request("GET", "/clusters")
        clusters = []
        for item in response.get("items", []):
            cluster_data = item["Clusters"]
            clusters.append(ClusterInfo(
                cluster_name=cluster_data["cluster_name"],
                version=cluster_data.get("version", "unknown"),
                total_hosts=cluster_data.get("total_hosts", 0)
            ))
        return clusters
        
    async def get_cluster_info(self, cluster_name: Optional[str] = None) -> ClusterInfo:
        """Get detailed cluster information."""
        cluster = cluster_name or self.config.cluster_name
        if not cluster:
            clusters = await self.get_clusters()
            if not clusters:
                raise AmbariAPIError("No clusters found")
            cluster = clusters[0].cluster_name
            
        response = await self._make_request("GET", f"/clusters/{cluster}")
        cluster_data = response["Clusters"]
        return ClusterInfo(
            cluster_name=cluster_data["cluster_name"],
            version=cluster_data.get("version", "unknown"),
            total_hosts=cluster_data.get("total_hosts", 0),
            health=cluster_data.get("health", "UNKNOWN")
        )
        
    # Service Operations
    async def get_services(self, cluster_name: Optional[str] = None) -> List[ServiceInfo]:
        """Get all services in a cluster."""
        cluster = cluster_name or self.config.cluster_name
        if not cluster:
            cluster_info = await self.get_cluster_info()
            cluster = cluster_info.cluster_name
            
        response = await self._make_request("GET", f"/clusters/{cluster}/services", params={"fields": "ServiceInfo/state"})
        services = []
        for item in response.get("items", []):
            service_data = item["ServiceInfo"]
            services.append(ServiceInfo(
                service_name=service_data["service_name"],
                state=service_data.get("state", "UNKNOWN"),
                maintenance_state=service_data.get("maintenance_state", "OFF")
            ))
        return services
        
    async def get_service_info(self, service_name: str, cluster_name: Optional[str] = None) -> ServiceInfo:
        """Get detailed service information."""
        cluster = cluster_name or self.config.cluster_name
        if not cluster:
            cluster_info = await self.get_cluster_info()
            cluster = cluster_info.cluster_name
            
        response = await self._make_request("GET", f"/clusters/{cluster}/services/{service_name}")
        service_data = response["ServiceInfo"]
        return ServiceInfo(
            service_name=service_data["service_name"],
            state=service_data["state"],
            maintenance_state=service_data.get("maintenance_state", "OFF")
        )
        
    async def start_service(self, service_name: str, cluster_name: Optional[str] = None) -> Dict[str, Any]:
        """Start a service."""
        cluster = cluster_name or self.config.cluster_name
        if not cluster:
            cluster_info = await self.get_cluster_info()
            cluster = cluster_info.cluster_name
            
        data = {
            "RequestInfo": {
                "context": f"Start {service_name} via MCP"
            },
            "Body": {
                "ServiceInfo": {
                    "state": "STARTED"
                }
            }
        }
        return await self._make_request("PUT", f"/clusters/{cluster}/services/{service_name}", data)
        
    async def stop_service(self, service_name: str, cluster_name: Optional[str] = None) -> Dict[str, Any]:
        """Stop a service."""
        cluster = cluster_name or self.config.cluster_name
        if not cluster:
            cluster_info = await self.get_cluster_info()
            cluster = cluster_info.cluster_name
            
        data = {
            "RequestInfo": {
                "context": f"Stop {service_name} via MCP"
            },
            "Body": {
                "ServiceInfo": {
                    "state": "INSTALLED"
                }
            }
        }
        return await self._make_request("PUT", f"/clusters/{cluster}/services/{service_name}", data)
        
    async def restart_service(self, service_name: str, cluster_name: Optional[str] = None) -> Dict[str, Any]:
        """Restart a service."""
        # First stop, then start
        await self.stop_service(service_name, cluster_name)
        await asyncio.sleep(5)  # Wait for stop to complete
        return await self.start_service(service_name, cluster_name)
        
    # Host Operations
    async def get_hosts(self, cluster_name: Optional[str] = None) -> List[HostInfo]:
        """Get all hosts in a cluster."""
        cluster = cluster_name or self.config.cluster_name
        if not cluster:
            cluster_info = await self.get_cluster_info()
            cluster = cluster_info.cluster_name
            
        response = await self._make_request("GET", f"/clusters/{cluster}/hosts", params={"fields": "Hosts/host_status,Hosts/host_state,Hosts/maintenance_state"})
        hosts = []
        for item in response.get("items", []):
            host_data = item["Hosts"]
            hosts.append(HostInfo(
                host_name=host_data["host_name"],
                host_state=host_data.get("host_state", "UNKNOWN"),
                health_status=host_data.get("host_status", "UNKNOWN"),  # Changed from health_status to host_status
                maintenance_state=host_data.get("maintenance_state", "OFF")
            ))
        return hosts
        
    async def get_host_info(self, host_name: str, cluster_name: Optional[str] = None) -> HostInfo:
        """Get detailed host information."""
        cluster = cluster_name or self.config.cluster_name
        if not cluster:
            cluster_info = await self.get_cluster_info()
            cluster = cluster_info.cluster_name
            
        response = await self._make_request("GET", f"/clusters/{cluster}/hosts/{host_name}")
        host_data = response["Hosts"]
        return HostInfo(
            host_name=host_data["host_name"],
            host_state=host_data.get("host_state", "UNKNOWN"),
            health_status=host_data.get("health_status", "UNKNOWN"),
            maintenance_state=host_data.get("maintenance_state", "OFF")
        )
        
    # Component Operations
    async def get_components(self, service_name: str, cluster_name: Optional[str] = None) -> List[ComponentInfo]:
        """Get all components for a service."""
        cluster = cluster_name or self.config.cluster_name
        if not cluster:
            cluster_info = await self.get_cluster_info()
            cluster = cluster_info.cluster_name
            
        response = await self._make_request("GET", f"/clusters/{cluster}/services/{service_name}/components")
        components = []
        for item in response.get("items", []):
            comp_data = item["ServiceComponentInfo"]
            components.append(ComponentInfo(
                component_name=comp_data["component_name"],
                service_name=comp_data["service_name"],
                state=comp_data.get("state", "UNKNOWN"),
                host_name=comp_data.get("host_name", "")
            ))
        return components
        
    # Configuration Operations
    async def get_configurations(self, config_type: str, cluster_name: Optional[str] = None) -> Dict[str, Any]:
        """Get configuration for a specific type."""
        cluster = cluster_name or self.config.cluster_name
        if not cluster:
            cluster_info = await self.get_cluster_info()
            cluster = cluster_info.cluster_name
            
        response = await self._make_request("GET", f"/clusters/{cluster}/configurations", 
                                          params={"type": config_type})
        return response
        
    async def update_configuration(self, config_type: str, properties: Dict[str, str], 
                                 cluster_name: Optional[str] = None) -> Dict[str, Any]:
        """Update configuration properties."""
        cluster = cluster_name or self.config.cluster_name
        if not cluster:
            cluster_info = await self.get_cluster_info()
            cluster = cluster_info.cluster_name
            
        data = {
            "Clusters": {
                "desired_config": {
                    "type": config_type,
                    "tag": f"version{int(asyncio.get_event_loop().time())}",
                    "properties": properties
                }
            }
        }
        return await self._make_request("PUT", f"/clusters/{cluster}", data)
        
    # Request Operations
    async def get_request_status(self, request_id: int, cluster_name: Optional[str] = None) -> Dict[str, Any]:
        """Get the status of a request."""
        cluster = cluster_name or self.config.cluster_name
        if not cluster:
            cluster_info = await self.get_cluster_info()
            cluster = cluster_info.cluster_name
            
        return await self._make_request("GET", f"/clusters/{cluster}/requests/{request_id}")
        
    async def get_recent_requests(self, cluster_name: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent requests."""
        cluster = cluster_name or self.config.cluster_name
        if not cluster:
            cluster_info = await self.get_cluster_info()
            cluster = cluster_info.cluster_name
            
        response = await self._make_request("GET", f"/clusters/{cluster}/requests", 
                                          params={"to": "end", "page_size": str(limit)})
        return response.get("items", [])
        
    # Health Check Operations
    async def health_check(self) -> Dict[str, Any]:
        """Perform a comprehensive health check."""
        try:
            # Test basic connectivity
            clusters = await self.get_clusters()
            if not clusters:
                return {"status": "unhealthy", "reason": "No clusters found"}
                
            cluster = clusters[0]
            
            # Get services status
            services = await self.get_services(cluster.cluster_name)
            unhealthy_services = [s for s in services if s.state not in ["STARTED", "INSTALLED"]]
            
            # Get hosts status  
            hosts = await self.get_hosts(cluster.cluster_name)
            unhealthy_hosts = [h for h in hosts if h.health_status not in ["HEALTHY", "LIVE"]]
            
            return {
                "status": "healthy" if not unhealthy_services and not unhealthy_hosts else "degraded",
                "cluster": cluster.cluster_name,
                "total_services": len(services),
                "unhealthy_services": len(unhealthy_services),
                "total_hosts": len(hosts),
                "unhealthy_hosts": len(unhealthy_hosts),
                "details": {
                    "unhealthy_services": [s.service_name for s in unhealthy_services],
                    "unhealthy_hosts": [h.host_name for h in unhealthy_hosts]
                }
            }
        except Exception as e:
            return {"status": "unhealthy", "reason": str(e)} 