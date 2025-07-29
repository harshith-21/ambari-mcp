#!/usr/bin/env python3
"""
FastAPI Demo for Ambari MCP Server.

This script demonstrates how to interact with the Ambari MCP Server
through its REST API interface.
"""

import asyncio
import json
import sys
from typing import Dict, Any

import httpx


class AmbariMCPAPIClient:
    """Client for interacting with Ambari MCP Server REST API."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """Initialize the API client."""
        self.base_url = base_url.rstrip('/')
        self.client = httpx.AsyncClient()
        
    async def __aenter__(self):
        """Async context manager entry."""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.aclose()
        
    async def get(self, endpoint: str) -> Dict[str, Any]:
        """Make a GET request."""
        url = f"{self.base_url}{endpoint}"
        response = await self.client.get(url)
        response.raise_for_status()
        return response.json()
        
    async def post(self, endpoint: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make a POST request."""
        url = f"{self.base_url}{endpoint}"
        response = await self.client.post(url, json=data or {})
        response.raise_for_status()
        return response.json()
        
    async def put(self, endpoint: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make a PUT request."""
        url = f"{self.base_url}{endpoint}"
        response = await self.client.put(url, json=data or {})
        response.raise_for_status()
        return response.json()


async def demo_health_and_status(client: AmbariMCPAPIClient):
    """Demonstrate health and status endpoints."""
    print("🏥 === Health and Status Demo ===")
    
    # Health check
    print("1. Checking server health...")
    try:
        health = await client.get("/health")
        print(f"Server status: {health['status']}")
        print(f"Version: {health['version']}")
        print(f"Current mode: {health['mode']}")
        print(f"Ambari connection: {health['ambari_connection']}")
    except Exception as e:
        print(f"Health check failed: {e}")
        
    # Comprehensive status
    print("\n2. Getting comprehensive status...")
    try:
        status = await client.get("/status")
        server_info = status['server']
        ambari_info = status['ambari']
        
        print(f"Server: {server_info['name']} v{server_info['version']}")
        print(f"Mode: {server_info['mode']['mode_type']}")
        print(f"Ambari: {ambari_info['host']}:{ambari_info['port']}")
        
        if ambari_info['cluster']:
            cluster_status = ambari_info['cluster']['status']
            print(f"Cluster status: {cluster_status}")
    except Exception as e:
        print(f"Status check failed: {e}")


async def demo_mode_management(client: AmbariMCPAPIClient):
    """Demonstrate mode management."""
    print("\n🔧 === Mode Management Demo ===")
    
    # List available modes
    print("1. Listing available modes...")
    try:
        modes = await client.get("/modes")
        print("Available modes:")
        for mode, description in modes['modes'].items():
            print(f"  • {mode}: {description}")
    except Exception as e:
        print(f"Failed to list modes: {e}")
        
    # Get current mode
    print("\n2. Getting current mode...")
    try:
        current_mode = await client.get("/modes/current")
        print(f"Current mode: {current_mode['mode_type']}")
        print(f"Description: {current_mode['description']}")
        print(f"Available tools: {len(current_mode['available_tools'])}")
    except Exception as e:
        print(f"Failed to get current mode: {e}")
        
    # Switch mode (demonstration)
    print("\n3. Switching to development mode...")
    try:
        switch_result = await client.post("/modes/switch", {
            "mode": "development",
            "reason": "API demonstration"
        })
        print(f"Mode switch: {switch_result['message']}")
        
        # Switch back to normal
        print("\n4. Switching back to normal mode...")
        await client.post("/modes/switch", {
            "mode": "normal",
            "reason": "End of demonstration"
        })
        print("Switched back to normal mode")
    except Exception as e:
        print(f"Mode switching failed: {e}")


async def demo_cluster_operations(client: AmbariMCPAPIClient):
    """Demonstrate cluster operations."""
    print("\n🏢 === Cluster Operations Demo ===")
    
    # Get cluster status
    print("1. Getting cluster status...")
    try:
        cluster_status = await client.get("/cluster/status")
        cluster = cluster_status['cluster']
        summary = cluster_status['summary']
        
        print(f"Cluster: {cluster['cluster_name']}")
        print(f"Version: {cluster['version']}")
        print(f"Total hosts: {cluster['total_hosts']}")
        print(f"Services: {summary['total_services']} total, {summary['running_services']} running")
        print(f"Hosts: {summary['total_hosts']} total, {summary['healthy_hosts']} healthy")
    except Exception as e:
        print(f"Failed to get cluster status: {e}")
        
    # Cluster health check
    print("\n2. Running cluster health check...")
    try:
        health = await client.get("/cluster/health")
        print(f"Cluster health: {health['status']}")
        
        if 'details' in health:
            details = health['details']
            if details.get('unhealthy_services'):
                print(f"Unhealthy services: {details['unhealthy_services']}")
            if details.get('unhealthy_hosts'):
                print(f"Unhealthy hosts: {details['unhealthy_hosts']}")
    except Exception as e:
        print(f"Cluster health check failed: {e}")


async def demo_service_management(client: AmbariMCPAPIClient):
    """Demonstrate service management."""
    print("\n⚙️ === Service Management Demo ===")
    
    # List services
    print("1. Listing services...")
    try:
        services_response = await client.get("/services")
        services = services_response['services']
        
        print(f"Found {len(services)} services:")
        for service in services[:5]:  # Show first 5
            print(f"  • {service['service_name']}: {service['state']}")
            
        # Get detailed info for first service
        if services:
            service_name = services[0]['service_name']
            print(f"\n2. Getting detailed info for {service_name}...")
            
            service_info = await client.get(f"/services/{service_name}")
            service_data = service_info['service']
            components = service_info['components']
            
            print(f"Service: {service_data['service_name']}")
            print(f"State: {service_data['state']}")
            print(f"Maintenance: {service_data['maintenance_state']}")
            print(f"Components: {len(components)}")
            
    except Exception as e:
        print(f"Service management demo failed: {e}")


async def demo_host_management(client: AmbariMCPAPIClient):
    """Demonstrate host management."""
    print("\n🖥️ === Host Management Demo ===")
    
    # List hosts
    print("1. Listing hosts...")
    try:
        hosts_response = await client.get("/hosts")
        hosts = hosts_response['hosts']
        
        print(f"Found {len(hosts)} hosts:")
        for host in hosts[:3]:  # Show first 3
            print(f"  • {host['host_name']}: {host['host_state']} ({host['health_status']})")
            
        # Get detailed info for first host
        if hosts:
            host_name = hosts[0]['host_name']
            print(f"\n2. Getting detailed info for {host_name}...")
            
            host_info = await client.get(f"/hosts/{host_name}")
            host_data = host_info['host']
            
            print(f"Host: {host_data['host_name']}")
            print(f"State: {host_data['host_state']}")
            print(f"Health: {host_data['health_status']}")
            print(f"Maintenance: {host_data['maintenance_state']}")
            
    except Exception as e:
        print(f"Host management demo failed: {e}")


async def demo_mcp_integration(client: AmbariMCPAPIClient):
    """Demonstrate MCP-specific endpoints."""
    print("\n🔗 === MCP Integration Demo ===")
    
    # List MCP tools
    print("1. Listing MCP tools...")
    try:
        tools = await client.get("/mcp/tools")
        print(f"Current mode: {tools['mode']}")
        print(f"Available tools: {len(tools['tools'])}")
        print("Tools:", ", ".join(tools['tools'][:5]) + ("..." if len(tools['tools']) > 5 else ""))
    except Exception as e:
        print(f"Failed to list MCP tools: {e}")
        
    # List MCP resources
    print("\n2. Listing MCP resources...")
    try:
        resources = await client.get("/mcp/resources")
        print("Available resources:")
        for resource in resources['resources']:
            print(f"  • {resource}")
    except Exception as e:
        print(f"Failed to list MCP resources: {e}")
        
    # List MCP prompts
    print("\n3. Listing MCP prompts...")
    try:
        prompts = await client.get("/mcp/prompts")
        print("Available prompts:")
        for prompt in prompts['available_prompts']:
            print(f"  • {prompt}")
    except Exception as e:
        print(f"Failed to list MCP prompts: {e}")


async def demo_request_monitoring(client: AmbariMCPAPIClient):
    """Demonstrate request monitoring."""
    print("\n📊 === Request Monitoring Demo ===")
    
    # List recent requests
    print("1. Listing recent requests...")
    try:
        requests_response = await client.get("/requests?limit=5")
        requests = requests_response['requests']
        
        if requests:
            print(f"Found {len(requests)} recent requests:")
            for req in requests:
                req_info = req.get('Requests', {})
                print(f"  • Request {req_info.get('id', 'N/A')}: {req_info.get('request_context', 'N/A')}")
        else:
            print("No recent requests found")
            
    except Exception as e:
        print(f"Request monitoring demo failed: {e}")


async def main():
    """Run the FastAPI demo."""
    print("🎯 Ambari MCP Server - FastAPI Demo")
    print("=" * 50)
    
    # Check if server is running
    base_url = "http://localhost:8000"
    print(f"Connecting to server at {base_url}...")
    
    try:
        async with AmbariMCPAPIClient(base_url) as client:
            # Test connection
            await client.get("/health")
            print("✅ Connected successfully!")
            
            # Run demonstrations
            await demo_health_and_status(client)
            await demo_mode_management(client)
            await demo_cluster_operations(client)
            await demo_service_management(client)
            await demo_host_management(client)
            await demo_mcp_integration(client)
            await demo_request_monitoring(client)
            
            print("\n✅ Demo completed successfully!")
            print(f"\n🌐 Visit {base_url}/docs for interactive API documentation")
            
    except httpx.ConnectError:
        print(f"❌ Could not connect to server at {base_url}")
        print("Make sure the Ambari MCP Server is running with:")
        print("  python -m ambari_mcp.main run-fastapi")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 