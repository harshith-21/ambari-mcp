#!/usr/bin/env python3
"""
Example MCP client for Ambari MCP Server.

This demonstrates how to connect to and interact with the Ambari MCP server
from an LLM client or other MCP-compatible application.
"""

import asyncio
import json
import os
from typing import Any, Dict

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class AmbariMCPClient:
    """Example client for Ambari MCP Server."""
    
    def __init__(self, server_command: str = "python", server_args: list = None):
        """Initialize the client."""
        self.server_params = StdioServerParameters(
            command=server_command,
            args=server_args or ["-m", "ambari_mcp.main", "run-mcp", "--transport", "stdio"],
            env=dict(os.environ)
        )
        
    async def connect_and_demo(self):
        """Connect to the server and run a demonstration."""
        print("🚀 Connecting to Ambari MCP Server...")
        
        async with stdio_client(self.server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize the connection
                await session.initialize()
                print("✅ Connected successfully!")
                
                # Demonstrate various MCP operations
                await self.demo_mode_management(session)
                await self.demo_cluster_operations(session)
                await self.demo_service_management(session)
                await self.demo_resources(session)
                await self.demo_prompts(session)
                
    async def demo_mode_management(self, session: ClientSession):
        """Demonstrate mode management operations."""
        print("\n📋 === Mode Management Demo ===")
        
        # List available modes
        print("1. Listing available modes...")
        result = await session.call_tool("list_available_modes", {})
        modes = json.loads(result.content[0].text)
        print(f"Available modes: {list(modes['data']['modes'].keys())}")
        
        # Get current mode
        print("\n2. Getting current mode...")
        result = await session.call_tool("get_current_mode", {})
        current_mode = json.loads(result.content[0].text)
        print(f"Current mode: {current_mode['data']['mode_type']}")
        
        # Switch to maintenance mode
        print("\n3. Switching to cluster_maintenance mode...")
        result = await session.call_tool("switch_mode", {
            "mode": "cluster_maintenance",
            "reason": "Demonstration of mode switching"
        })
        switch_result = json.loads(result.content[0].text)
        print(f"Mode switch result: {switch_result['message']}")
        
        # Switch back to normal mode
        print("\n4. Switching back to normal mode...")
        await session.call_tool("switch_mode", {
            "mode": "normal",
            "reason": "End of demonstration"
        })
        print("Switched back to normal mode")
        
    async def demo_cluster_operations(self, session: ClientSession):
        """Demonstrate cluster operations."""
        print("\n🏢 === Cluster Operations Demo ===")
        
        # Get cluster status
        print("1. Getting cluster status...")
        try:
            result = await session.call_tool("get_cluster_status", {})
            status_data = json.loads(result.content[0].text)
            
            if status_data['success']:
                cluster_data = status_data['data']
                print(f"Cluster: {cluster_data['cluster']['cluster_name']}")
                print(f"Total services: {cluster_data['summary']['total_services']}")
                print(f"Running services: {cluster_data['summary']['running_services']}")
                print(f"Total hosts: {cluster_data['summary']['total_hosts']}")
                print(f"Healthy hosts: {cluster_data['summary']['healthy_hosts']}")
            else:
                print(f"Failed to get cluster status: {status_data['message']}")
        except Exception as e:
            print(f"Error getting cluster status: {e}")
            
        # Health check
        print("\n2. Running health check...")
        try:
            result = await session.call_tool("health_check", {})
            health_data = json.loads(result.content[0].text)
            
            if health_data['success']:
                health_status = health_data['data']
                print(f"Health status: {health_status['status']}")
                if 'details' in health_status:
                    details = health_status['details']
                    if details.get('unhealthy_services'):
                        print(f"Unhealthy services: {details['unhealthy_services']}")
                    if details.get('unhealthy_hosts'):
                        print(f"Unhealthy hosts: {details['unhealthy_hosts']}")
            else:
                print(f"Health check failed: {health_data['message']}")
        except Exception as e:
            print(f"Error running health check: {e}")
            
    async def demo_service_management(self, session: ClientSession):
        """Demonstrate service management operations."""
        print("\n⚙️ === Service Management Demo ===")
        
        # List services
        print("1. Listing services...")
        try:
            result = await session.call_tool("list_services", {})
            services_data = json.loads(result.content[0].text)
            
            if services_data['success']:
                services = services_data['data']['services']
                print(f"Found {len(services)} services:")
                for service in services[:5]:  # Show first 5 services
                    print(f"  • {service['service_name']}: {service['state']}")
                    
                # Get detailed info for first service if available
                if services:
                    service_name = services[0]['service_name']
                    print(f"\n2. Getting detailed info for {service_name}...")
                    
                    result = await session.call_tool("get_service_info", {
                        "service_name": service_name
                    })
                    service_info = json.loads(result.content[0].text)
                    
                    if service_info['success']:
                        service_data = service_info['data']['service']
                        components = service_info['data']['components']
                        print(f"Service {service_name}:")
                        print(f"  State: {service_data['state']}")
                        print(f"  Maintenance: {service_data['maintenance_state']}")
                        print(f"  Components: {len(components)}")
            else:
                print(f"Failed to list services: {services_data['message']}")
        except Exception as e:
            print(f"Error listing services: {e}")
            
    async def demo_resources(self, session: ClientSession):
        """Demonstrate MCP resources."""
        print("\n📄 === Resources Demo ===")
        
        # List available resources
        resources = await session.list_resources()
        print(f"Available resources: {len(resources.resources)}")
        for resource in resources.resources:
            print(f"  • {resource.uri}")
            
        # Read current mode resource
        print("\n1. Reading current mode resource...")
        try:
            from pydantic import AnyUrl
            mode_resource = await session.read_resource(AnyUrl("ambari://mode/current"))
            if mode_resource.contents:
                mode_data = json.loads(mode_resource.contents[0].text)
                print(f"Current mode: {mode_data['mode_type']}")
                print(f"Description: {mode_data['description']}")
        except Exception as e:
            print(f"Error reading mode resource: {e}")
            
        # Read documentation resource
        print("\n2. Reading documentation resource...")
        try:
            doc_resource = await session.read_resource(AnyUrl("ambari://documentation/modes"))
            if doc_resource.contents:
                print("Documentation preview:")
                print(doc_resource.contents[0].text[:200] + "...")
        except Exception as e:
            print(f"Error reading documentation: {e}")
            
    async def demo_prompts(self, session: ClientSession):
        """Demonstrate MCP prompts."""
        print("\n💬 === Prompts Demo ===")
        
        # List available prompts
        prompts = await session.list_prompts()
        print(f"Available prompts: {len(prompts.prompts)}")
        for prompt in prompts.prompts:
            print(f"  • {prompt.name}: {prompt.description}")
            
        # Get cluster overview prompt
        print("\n1. Getting cluster overview prompt...")
        try:
            prompt_result = await session.get_prompt("cluster_overview", {})
            print("Cluster overview prompt:")
            for message in prompt_result.messages:
                print(f"  {message.content.text[:100]}...")
        except Exception as e:
            print(f"Error getting cluster overview prompt: {e}")
            
        # Get service management prompt
        print("\n2. Getting service management prompt...")
        try:
            prompt_result = await session.get_prompt("service_management", {
                "service_name": "HDFS",
                "operation": "status"
            })
            print("Service management prompt:")
            print(f"  {prompt_result.messages[0].content.text[:100]}...")
        except Exception as e:
            print(f"Error getting service management prompt: {e}")


async def main():
    """Run the demo client."""
    print("🎯 Ambari MCP Client Demo")
    print("=" * 50)
    
    # Create and run the client
    client = AmbariMCPClient()
    
    try:
        await client.connect_and_demo()
        print("\n✅ Demo completed successfully!")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main()) 