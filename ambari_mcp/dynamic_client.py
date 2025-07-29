"""Dynamic Ambari client manager for context-driven connections."""

import asyncio
from typing import Dict, Optional, Any
from dataclasses import dataclass
from contextlib import asynccontextmanager

from .client import AmbariClient, AmbariAPIError
from .config import AmbariConfig


@dataclass
class AmbariTarget:
    """Represents an Ambari cluster target."""
    name: str
    host: str
    port: int = 8080
    username: str = "admin"
    password: str = "admin"
    use_ssl: bool = False
    cluster_name: Optional[str] = None
    
    def to_config(self) -> AmbariConfig:
        """Convert to AmbariConfig."""
        return AmbariConfig(
            host=self.host,
            port=self.port,
            username=self.username,
            password=self.password,
            cluster_name=self.cluster_name,
            use_ssl=self.use_ssl
        )


class DynamicAmbariClientManager:
    """Manages connections to multiple Ambari clusters dynamically."""
    
    def __init__(self):
        self._clients: Dict[str, AmbariClient] = {}
        self._targets: Dict[str, AmbariTarget] = {}
        
    def register_target(self, target: AmbariTarget):
        """Register an Ambari cluster target."""
        self._targets[target.name] = target
        
    def unregister_target(self, name: str):
        """Unregister an Ambari cluster target."""
        if name in self._targets:
            del self._targets[name]
        if name in self._clients:
            # Clean up existing client
            asyncio.create_task(self._clients[name].disconnect())
            del self._clients[name]
            
    async def get_client(self, target_name: str) -> AmbariClient:
        """Get or create client for target."""
        if target_name not in self._targets:
            raise ValueError(f"Unknown Ambari target: {target_name}")
            
        if target_name not in self._clients:
            target = self._targets[target_name]
            config = target.to_config()
            client = AmbariClient(config)
            await client.connect()
            self._clients[target_name] = client
            
        return self._clients[target_name]
        
    @asynccontextmanager
    async def client_for_target(self, target_name: str):
        """Context manager for getting client."""
        client = await self.get_client(target_name)
        try:
            yield client
        except Exception:
            # Optionally reconnect on errors
            if target_name in self._clients:
                await self._clients[target_name].disconnect()
                del self._clients[target_name]
            raise
            
    def list_targets(self) -> Dict[str, Dict[str, Any]]:
        """List all registered targets."""
        return {
            name: {
                "host": target.host,
                "port": target.port,
                "cluster_name": target.cluster_name,
                "use_ssl": target.use_ssl
            }
            for name, target in self._targets.items()
        }
        
    async def discover_targets_from_context(self, context: Dict[str, Any]) -> Optional[str]:
        """Discover appropriate target from LLM context."""
        # Extract cluster hints from context
        cluster_hints = []
        
        # Look for explicit cluster references
        if "cluster" in context:
            cluster_hints.append(context["cluster"])
        if "ambari_host" in context:
            cluster_hints.append(context["ambari_host"])
        if "environment" in context:
            env = context["environment"].lower()
            cluster_hints.extend([env, f"{env}-cluster", f"ambari-{env}"])
            
        # Try to match against registered targets
        for hint in cluster_hints:
            if hint in self._targets:
                return hint
            # Fuzzy matching
            for target_name, target in self._targets.items():
                if (hint.lower() in target_name.lower() or 
                    hint.lower() in target.host.lower() or
                    (target.cluster_name and hint.lower() in target.cluster_name.lower())):
                    return target_name
                    
        return None
        
    async def auto_register_from_context(self, context: Dict[str, Any]) -> Optional[str]:
        """Auto-register target from LLM-provided context."""
        required_fields = ["ambari_host"]
        if not all(field in context for field in required_fields):
            return None
            
        # Create target from context
        target_name = context.get("target_name", f"dynamic-{context['ambari_host']}")
        
        target = AmbariTarget(
            name=target_name,
            host=context["ambari_host"],
            port=context.get("ambari_port", 8080),
            username=context.get("ambari_username", "admin"),
            password=context.get("ambari_password", "admin"),
            use_ssl=context.get("ambari_use_ssl", False),
            cluster_name=context.get("cluster_name")
        )
        
        self.register_target(target)
        return target_name
        
    async def health_check_all(self) -> Dict[str, Dict[str, Any]]:
        """Health check all registered targets."""
        results = {}
        
        for target_name in self._targets:
            try:
                async with self.client_for_target(target_name) as client:
                    health = await client.health_check()
                    results[target_name] = {
                        "status": "healthy",
                        "details": health
                    }
            except Exception as e:
                results[target_name] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
                
        return results
        
    async def cleanup(self):
        """Cleanup all clients."""
        for client in self._clients.values():
            await client.disconnect()
        self._clients.clear() 