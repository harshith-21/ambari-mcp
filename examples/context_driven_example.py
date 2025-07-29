#!/usr/bin/env python3
"""
Context-Driven Ambari MCP Example.

This demonstrates how LLMs can provide Ambari connection details
dynamically through tool parameters rather than server configuration.
"""

import asyncio
import json

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def demonstrate_context_driven_connections():
    """Demonstrate various ways to provide Ambari connection context."""
    
    # Use enhanced server
    server_params = StdioServerParameters(
        command="python",
        args=["-c", """
from ambari_mcp.enhanced_server import EnhancedAmbariMCPServer
from ambari_mcp.config import Settings
import asyncio

async def main():
    settings = Settings()
    server = EnhancedAmbariMCPServer(settings)
    await server.run_stdio()

asyncio.run(main())
        """],
        env={}
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            print("🎯 Context-Driven Ambari MCP Demo")
            print("=" * 50)
            
            # Scenario 1: LLM provides connection details directly
            print("\n📍 Scenario 1: Direct connection details from LLM")
            result = await session.call_tool("get_cluster_status_enhanced", {
                "ambari_host": "dev-ambari.company.com",
                "ambari_port": 8080,
                "ambari_username": "admin",
                "ambari_password": "admin",
                "cluster_name": "DevCluster"
            })
            print(f"Result: {json.loads(result.content[0].text)['message']}")
            
            # Scenario 2: Register targets for reuse
            print("\n📍 Scenario 2: Register targets for reuse")
            
            # Register development environment
            await session.call_tool("register_ambari_target", {
                "target_name": "development",
                "ambari_host": "dev-ambari.company.com",
                "ambari_port": 8080,
                "ambari_username": "dev-admin",
                "ambari_password": "dev-password",
                "cluster_name": "DevCluster"
            })
            
            # Register production environment
            await session.call_tool("register_ambari_target", {
                "target_name": "production",
                "ambari_host": "prod-ambari.company.com", 
                "ambari_port": 8443,
                "ambari_username": "prod-admin",
                "ambari_password": "prod-password",
                "ambari_use_ssl": True,
                "cluster_name": "ProdCluster"
            })
            
            # List registered targets
            targets_result = await session.call_tool("list_ambari_targets", {})
            targets_data = json.loads(targets_result.content[0].text)
            print(f"Registered targets: {list(targets_data['data']['targets'].keys())}")
            
            # Scenario 3: Use registered targets
            print("\n📍 Scenario 3: Use registered targets")
            
            # Get status from development
            dev_result = await session.call_tool("get_cluster_status_enhanced", {
                "target_name": "development"
            })
            print(f"Dev cluster: {json.loads(dev_result.content[0].text)['message']}")
            
            # Start service on production (if it exists)
            try:
                prod_result = await session.call_tool("start_service_enhanced", {
                    "service_name": "ZOOKEEPER",
                    "target_name": "production"
                })
                print(f"Production operation: {json.loads(prod_result.content[0].text)['message']}")
            except Exception as e:
                print(f"Production operation failed (expected): {e}")
            
            # Scenario 4: Health check all targets
            print("\n📍 Scenario 4: Multi-cluster health check")
            health_result = await session.call_tool("health_check_all_targets", {})
            health_data = json.loads(health_result.content[0].text)
            print(f"Health check: {health_data['message']}")
            
            # Scenario 5: Context-driven prompts
            print("\n📍 Scenario 5: Context-driven guidance")
            
            # Get multi-cluster overview prompt
            prompt_result = await session.get_prompt("multi_cluster_overview", {
                "environment": "production"
            })
            print("Multi-cluster guidance:")
            print(prompt_result.messages[0].content.text[:200] + "...")
            
            # Get context-driven operation prompt
            context_prompt = await session.get_prompt("context_driven_operation", {
                "operation": "restart_service",
                "context_hints": "HDFS service in the production environment seems slow"
            })
            print("\nContext-driven operation guidance:")
            print(context_prompt.messages[0].content.text[:200] + "...")


async def demonstrate_llm_conversation_flow():
    """Demonstrate how this would work in an LLM conversation."""
    
    print("\n🤖 LLM Conversation Flow Example")
    print("=" * 50)
    
    conversation_examples = [
        {
            "user": "Check the status of my development Hadoop cluster",
            "llm_reasoning": "User mentioned 'development' and 'Hadoop cluster'. I should check if there are registered targets first, then either use a registered dev target or ask for connection details.",
            "mcp_calls": [
                ("list_ambari_targets", {}),
                ("get_cluster_status_enhanced", {"target_name": "development"})
            ]
        },
        {
            "user": "Start YARN service on the cluster at 192.168.1.100",
            "llm_reasoning": "User provided specific IP address. I should use direct connection with the provided host.",
            "mcp_calls": [
                ("start_service_enhanced", {
                    "service_name": "YARN",
                    "ambari_host": "192.168.1.100",
                    "ambari_username": "admin",  # Default, could ask user
                    "ambari_password": "admin"   # Default, could ask user
                })
            ]
        },
        {
            "user": "I need to manage multiple clusters - dev at dev.company.com and prod at prod.company.com",
            "llm_reasoning": "User wants to manage multiple clusters. I should register both targets for easier future reference.",
            "mcp_calls": [
                ("register_ambari_target", {
                    "target_name": "dev",
                    "ambari_host": "dev.company.com"
                }),
                ("register_ambari_target", {
                    "target_name": "prod", 
                    "ambari_host": "prod.company.com"
                })
            ]
        },
        {
            "user": "Show me the health of all my clusters",
            "llm_reasoning": "User wants overview of all clusters. I should use the multi-cluster health check.",
            "mcp_calls": [
                ("health_check_all_targets", {})
            ]
        }
    ]
    
    for i, example in enumerate(conversation_examples, 1):
        print(f"\nExample {i}:")
        print(f"User: \"{example['user']}\"")
        print(f"LLM Reasoning: {example['llm_reasoning']}")
        print("MCP Tool Calls:")
        for tool_name, params in example['mcp_calls']:
            print(f"  - {tool_name}({params})")


def show_architectural_benefits():
    """Show the benefits of the context-driven approach."""
    
    print("\n✅ Architectural Benefits")
    print("=" * 50)
    
    benefits = [
        {
            "aspect": "Flexibility",
            "old": "Server hardcoded to single Ambari cluster",
            "new": "LLM can target any cluster dynamically"
        },
        {
            "aspect": "Multi-tenancy", 
            "old": "One server per cluster needed",
            "new": "Single server handles multiple clusters"
        },
        {
            "aspect": "Security",
            "old": "Credentials in server configuration",
            "new": "Credentials provided per-operation or via secure context"
        },
        {
            "aspect": "Context Awareness",
            "old": "No understanding of user intent/environment",
            "new": "LLM can infer target from conversation context"
        },
        {
            "aspect": "Scalability",
            "old": "Static configuration limits growth",
            "new": "Dynamic registration supports any number of clusters"
        },
        {
            "aspect": "User Experience",
            "old": "Users must know server configuration",
            "new": "Users can specify targets naturally in conversation"
        }
    ]
    
    for benefit in benefits:
        print(f"\n{benefit['aspect']}:")
        print(f"  Before: {benefit['old']}")
        print(f"  After:  {benefit['new']}")


async def main():
    """Run all demonstrations."""
    try:
        await demonstrate_context_driven_connections()
        await demonstrate_llm_conversation_flow()
        show_architectural_benefits()
        
        print("\n✅ Context-driven approach provides much better flexibility!")
        print("The LLM can now:")
        print("- Target multiple clusters dynamically")
        print("- Infer targets from conversation context")
        print("- Register new targets on-demand")
        print("- Provide connection details per-operation")
        print("- Manage multi-cluster environments seamlessly")
        
    except Exception as e:
        print(f"Demo failed: {e}")
        print("\nNote: This demo requires the enhanced server implementation.")
        print("The enhanced server allows dynamic Ambari connections.")


if __name__ == "__main__":
    asyncio.run(main()) 