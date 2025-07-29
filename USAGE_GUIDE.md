# Ambari MCP Server - Usage Guide

This guide provides practical examples and workflows for using the Ambari MCP Server in various scenarios.

## Table of Contents

- [Getting Started](#getting-started)
- [Operational Modes](#operational-modes)
- [Common Workflows](#common-workflows)
- [LLM Integration Patterns](#llm-integration-patterns)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

## Getting Started

### Initial Setup and Verification

```bash
# 1. Test Ambari connectivity
python -m ambari_mcp.main test-connection

# 2. View server information
python -m ambari_mcp.main info

# 3. Start the server
python -m ambari_mcp.main run-both
```

### Basic Health Check Workflow

```python
# MCP Client Example
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def health_check_workflow():
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "ambari_mcp.main", "run-mcp", "--transport", "stdio"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # 1. Check current mode
            mode_result = await session.call_tool("get_current_mode", {})
            print(f"Current mode: {mode_result}")
            
            # 2. Perform health check
            health_result = await session.call_tool("health_check", {})
            print(f"Cluster health: {health_result}")
            
            # 3. Get cluster status
            status_result = await session.call_tool("get_cluster_status", {})
            print(f"Cluster status: {status_result}")
```

## Operational Modes

### Normal Mode - Daily Operations

**Use Case**: Regular cluster management and monitoring

```python
# Switch to normal mode
await session.call_tool("switch_mode", {
    "mode": "normal", 
    "reason": "Daily operations"
})

# Available operations with confirmations
await session.call_tool("restart_service", {"service_name": "YARN"})
await session.call_tool("update_configuration", {
    "config_type": "yarn-site",
    "properties": '{"yarn.scheduler.capacity.maximum-applications": "10000"}'
})
```

### Cluster Maintenance Mode - Planned Maintenance

**Use Case**: Scheduled maintenance windows, system updates

```python
# Enter maintenance mode
await session.call_tool("switch_mode", {
    "mode": "cluster_maintenance",
    "reason": "Scheduled maintenance window"
})

# Safe shutdown sequence
services_to_stop = ["OOZIE", "HIVE", "YARN", "MAPREDUCE2"]
for service in services_to_stop:
    result = await session.call_tool("stop_service", {"service_name": service})
    print(f"Stopping {service}: {result}")
    
    # Monitor shutdown
    while True:
        status = await session.call_tool("get_service_info", {"service_name": service})
        if status["data"]["service"]["state"] == "INSTALLED":
            break
        await asyncio.sleep(10)

# Perform maintenance tasks here...

# Restart services in reverse order
for service in reversed(services_to_stop):
    await session.call_tool("start_service", {"service_name": service})
```

### Scale Up Mode - Capacity Expansion

**Use Case**: Adding new nodes, expanding cluster capacity

```python
# Enter scale-up mode
await session.call_tool("switch_mode", {
    "mode": "scale_up",
    "reason": "Adding 5 new data nodes"
})

# Scale-up workflow
# 1. Check current capacity
cluster_status = await session.call_tool("get_cluster_status", {})
current_hosts = len(cluster_status["data"]["hosts"])

# 2. Update configurations for new capacity
await session.call_tool("update_configuration", {
    "config_type": "hdfs-site",
    "properties": '{"dfs.replication": "3", "dfs.namenode.replication.min": "2"}'
})

# 3. Restart services to apply new configurations
priority_services = ["HDFS", "YARN", "HBASE"]
for service in priority_services:
    await session.call_tool("restart_service", {"service_name": service})
```

### Config Edit Mode - Configuration Management

**Use Case**: Making configuration changes without service disruption risk

```python
# Enter config edit mode
await session.call_tool("switch_mode", {
    "mode": "config_edit",
    "reason": "Updating Hadoop configurations"
})

# Configuration management workflow
# 1. Backup current configuration
hdfs_config = await session.call_tool("get_configurations", {"config_type": "hdfs-site"})

# 2. Update configurations safely
new_configs = {
    "dfs.block.size": "268435456",  # 256MB blocks
    "dfs.namenode.handler.count": "20",
    "dfs.datanode.max.transfer.threads": "8192"
}

await session.call_tool("update_configuration", {
    "config_type": "hdfs-site",
    "properties": json.dumps(new_configs)
})

# 3. Validate configuration
updated_config = await session.call_tool("get_configurations", {"config_type": "hdfs-site"})
```

### Development Mode - Testing and Development

**Use Case**: Development, testing, rapid iteration

```python
# Enter development mode
await session.call_tool("switch_mode", {
    "mode": "development",
    "reason": "Testing new configurations"
})

# Rapid testing without confirmations
test_services = ["ZOOKEEPER", "KAFKA"]
for service in test_services:
    # Stop and start rapidly for testing
    await session.call_tool("stop_service", {"service_name": service})
    await session.call_tool("start_service", {"service_name": service})
```

## Common Workflows

### Service Lifecycle Management

```python
async def manage_service_lifecycle(session, service_name, operation):
    """Complete service lifecycle management with monitoring."""
    
    # 1. Check current service state
    service_info = await session.call_tool("get_service_info", {"service_name": service_name})
    current_state = service_info["data"]["service"]["state"]
    print(f"{service_name} current state: {current_state}")
    
    # 2. Perform operation based on current state and desired operation
    if operation == "restart":
        if current_state == "STARTED":
            stop_result = await session.call_tool("stop_service", {"service_name": service_name})
            request_id = stop_result.get("request_id")
            
            # Monitor stop operation
            if request_id:
                await monitor_request(session, request_id)
        
        # Start the service
        start_result = await session.call_tool("start_service", {"service_name": service_name})
        request_id = start_result.get("request_id")
        
        # Monitor start operation
        if request_id:
            await monitor_request(session, request_id)
    
    # 3. Verify final state
    final_info = await session.call_tool("get_service_info", {"service_name": service_name})
    final_state = final_info["data"]["service"]["state"]
    print(f"{service_name} final state: {final_state}")

async def monitor_request(session, request_id):
    """Monitor request progress until completion."""
    while True:
        status = await session.call_tool("get_request_status", {"request_id": request_id})
        request_status = status["data"]["request_status"]["Requests"]["request_status"]
        
        print(f"Request {request_id} status: {request_status}")
        
        if request_status in ["COMPLETED", "FAILED", "ABORTED"]:
            break
            
        await asyncio.sleep(5)
```

### Cluster Health Monitoring

```python
async def comprehensive_health_check(session):
    """Perform comprehensive cluster health monitoring."""
    
    health_report = {
        "timestamp": datetime.utcnow().isoformat(),
        "overall_health": "unknown",
        "services": {},
        "hosts": {},
        "recommendations": []
    }
    
    # 1. Overall cluster health
    health_result = await session.call_tool("health_check", {})
    health_report["overall_health"] = health_result["data"]["status"]
    
    # 2. Service-level health
    services_result = await session.call_tool("list_services", {})
    for service in services_result["data"]["services"]:
        service_name = service["service_name"]
        service_state = service["state"]
        
        health_report["services"][service_name] = {
            "state": service_state,
            "healthy": service_state == "STARTED",
            "maintenance_mode": service["maintenance_state"] == "ON"
        }
        
        if service_state != "STARTED":
            health_report["recommendations"].append(
                f"Service {service_name} is not running (state: {service_state})"
            )
    
    # 3. Host-level health
    hosts_result = await session.call_tool("list_hosts", {})
    for host in hosts_result["data"]["hosts"]:
        host_name = host["host_name"]
        host_health = host["health_status"]
        
        health_report["hosts"][host_name] = {
            "health_status": host_health,
            "host_state": host["host_state"],
            "healthy": host_health == "HEALTHY"
        }
        
        if host_health != "HEALTHY":
            health_report["recommendations"].append(
                f"Host {host_name} is not healthy (status: {host_health})"
            )
    
    return health_report
```

### Configuration Management Workflow

```python
async def safe_configuration_update(session, config_type, new_properties, affected_services):
    """Safely update configuration with service restart coordination."""
    
    # 1. Switch to config edit mode
    await session.call_tool("switch_mode", {
        "mode": "config_edit",
        "reason": f"Updating {config_type} configuration"
    })
    
    # 2. Backup current configuration
    current_config = await session.call_tool("get_configurations", {"config_type": config_type})
    backup = {
        "timestamp": datetime.utcnow().isoformat(),
        "config_type": config_type,
        "configuration": current_config["data"]["configuration"]
    }
    
    # 3. Apply new configuration
    await session.call_tool("update_configuration", {
        "config_type": config_type,
        "properties": json.dumps(new_properties)
    })
    
    # 4. Switch back to normal mode for service operations
    await session.call_tool("switch_mode", {"mode": "normal"})
    
    # 5. Restart affected services
    for service in affected_services:
        print(f"Restarting {service} to apply configuration changes...")
        await manage_service_lifecycle(session, service, "restart")
    
    # 6. Verify configuration was applied
    updated_config = await session.call_tool("get_configurations", {"config_type": config_type})
    
    return {
        "backup": backup,
        "updated_config": updated_config,
        "services_restarted": affected_services
    }
```

## LLM Integration Patterns

### Using MCP Resources for Context

```python
# Read cluster status resource for context
from pydantic import AnyUrl

async def get_cluster_context(session):
    """Get comprehensive cluster context for LLM."""
    
    # Read cluster status resource
    cluster_resource = await session.read_resource(
        AnyUrl("ambari://cluster/MyCluster/status")
    )
    cluster_data = json.loads(cluster_resource.contents[0].text)
    
    # Read current mode resource
    mode_resource = await session.read_resource(
        AnyUrl("ambari://mode/current")
    )
    mode_data = json.loads(mode_resource.contents[0].text)
    
    # Read documentation resource
    docs_resource = await session.read_resource(
        AnyUrl("ambari://documentation/modes")
    )
    documentation = docs_resource.contents[0].text
    
    return {
        "cluster": cluster_data,
        "mode": mode_data,
        "documentation": documentation
    }
```

### Using MCP Prompts for Guidance

```python
async def get_maintenance_guidance(session, cluster_name=None):
    """Get step-by-step maintenance guidance using MCP prompts."""
    
    # Get maintenance checklist prompt
    prompt_result = await session.get_prompt("maintenance_checklist", {
        "cluster_name": cluster_name
    })
    
    # Extract guidance from prompt messages
    guidance = []
    for message in prompt_result.messages:
        if hasattr(message.content, 'text'):
            guidance.append(message.content.text)
    
    return guidance

async def get_scaling_plan(session, target_capacity):
    """Get scaling plan using MCP prompts."""
    
    prompt_result = await session.get_prompt("scale_up_planning", {
        "target_capacity": target_capacity
    })
    
    return prompt_result.messages[0].content.text
```

### Context-Aware Operations

```python
async def context_aware_service_management(session, service_name, operation):
    """Perform service management with full context awareness."""
    
    # 1. Get current context
    context = await get_cluster_context(session)
    current_mode = context["mode"]["mode_type"]
    
    # 2. Check if operation is allowed in current mode
    if not can_perform_operation(current_mode, operation):
        # Suggest appropriate mode
        suggested_mode = suggest_mode_for_operation(operation)
        
        print(f"Operation '{operation}' not allowed in '{current_mode}' mode.")
        print(f"Consider switching to '{suggested_mode}' mode.")
        
        # Optionally switch mode automatically
        await session.call_tool("switch_mode", {
            "mode": suggested_mode,
            "reason": f"Required for {operation} operation on {service_name}"
        })
    
    # 3. Get service-specific guidance
    guidance = await session.get_prompt("service_management", {
        "service_name": service_name,
        "operation": operation
    })
    
    print(f"Guidance: {guidance.messages[0].content.text}")
    
    # 4. Perform operation with monitoring
    await manage_service_lifecycle(session, service_name, operation)

def can_perform_operation(mode, operation):
    """Check if operation is allowed in current mode."""
    mode_restrictions = {
        "cluster_maintenance": ["start_service", "restart_service", "update_configuration"],
        "scale_up": ["stop_service"],
        "config_edit": ["start_service", "stop_service", "restart_service"]
    }
    
    if mode == "normal" or mode == "development":
        return True
    
    return operation not in mode_restrictions.get(mode, [])

def suggest_mode_for_operation(operation):
    """Suggest appropriate mode for operation."""
    operation_modes = {
        "start_service": "normal",
        "stop_service": "cluster_maintenance", 
        "restart_service": "normal",
        "update_configuration": "config_edit"
    }
    
    return operation_modes.get(operation, "normal")
```

## Troubleshooting

### Connection Issues

```python
async def diagnose_connection_issues(session):
    """Diagnose and report connection issues."""
    
    try:
        # Test basic connectivity
        health_result = await session.call_tool("health_check", {})
        
        if not health_result["success"]:
            print(f"Connection issue: {health_result['message']}")
            return False
            
    except Exception as e:
        print(f"Failed to connect to Ambari: {e}")
        
        # Provide troubleshooting steps
        print("\nTroubleshooting steps:")
        print("1. Check AMBARI_HOST and AMBARI_PORT environment variables")
        print("2. Verify Ambari server is running and accessible")
        print("3. Check username/password credentials")
        print("4. Verify network connectivity to Ambari server")
        print("5. Check SSL configuration if using HTTPS")
        
        return False
    
    return True
```

### Service Operation Failures

```python
async def diagnose_service_issues(session, service_name):
    """Diagnose service-related issues."""
    
    # Get detailed service information
    service_info = await session.call_tool("get_service_info", {"service_name": service_name})
    
    if not service_info["success"]:
        print(f"Failed to get service info: {service_info['message']}")
        return
    
    service_data = service_info["data"]["service"]
    components = service_info["data"]["components"]
    
    print(f"\nService Diagnosis for {service_name}:")
    print(f"State: {service_data['state']}")
    print(f"Maintenance Mode: {service_data['maintenance_state']}")
    print(f"Components: {len(components)}")
    
    # Check component states
    unhealthy_components = []
    for component in components:
        if component["state"] not in ["STARTED", "INSTALLED"]:
            unhealthy_components.append(component)
    
    if unhealthy_components:
        print(f"\nUnhealthy components ({len(unhealthy_components)}):")
        for comp in unhealthy_components:
            print(f"  - {comp['component_name']}: {comp['state']} on {comp['host_name']}")
    
    # Check recent requests
    recent_requests = await session.call_tool("list_recent_requests", {"limit": 5})
    
    if recent_requests["success"]:
        print(f"\nRecent operations:")
        for req in recent_requests["data"]["requests"][:3]:
            req_info = req.get("Requests", {})
            print(f"  - Request {req_info.get('id')}: {req_info.get('request_context')}")
```

## Best Practices

### 1. Mode Management

```python
# Always use appropriate modes for operations
async def best_practice_mode_usage(session):
    """Demonstrate best practices for mode usage."""
    
    # For routine operations
    await session.call_tool("switch_mode", {"mode": "normal"})
    
    # For maintenance windows
    await session.call_tool("switch_mode", {
        "mode": "cluster_maintenance",
        "reason": "Monthly maintenance window"
    })
    
    # For configuration changes
    await session.call_tool("switch_mode", {
        "mode": "config_edit", 
        "reason": "Performance tuning"
    })
    
    # Always switch back when done
    await session.call_tool("switch_mode", {"mode": "normal"})
```

### 2. Error Handling

```python
async def robust_operation_with_error_handling(session, service_name, operation):
    """Demonstrate robust error handling patterns."""
    
    max_retries = 3
    retry_delay = 10
    
    for attempt in range(max_retries):
        try:
            result = await session.call_tool(f"{operation}_service", {
                "service_name": service_name
            })
            
            if result["success"]:
                print(f"Operation {operation} succeeded on attempt {attempt + 1}")
                return result
            else:
                print(f"Operation failed: {result['message']}")
                
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            
        if attempt < max_retries - 1:
            print(f"Retrying in {retry_delay} seconds...")
            await asyncio.sleep(retry_delay)
    
    print(f"Operation {operation} failed after {max_retries} attempts")
    return None
```

### 3. Monitoring and Logging

```python
async def operation_with_comprehensive_logging(session, operation_details):
    """Demonstrate comprehensive logging during operations."""
    
    operation_id = f"op_{int(time.time())}"
    
    print(f"[{operation_id}] Starting operation: {operation_details}")
    
    # Log current state
    cluster_status = await session.call_tool("get_cluster_status", {})
    print(f"[{operation_id}] Pre-operation cluster state logged")
    
    try:
        # Perform operation
        result = await perform_operation(session, operation_details)
        
        # Log result
        print(f"[{operation_id}] Operation completed: {result['success']}")
        
        # Log post-operation state
        post_status = await session.call_tool("get_cluster_status", {})
        print(f"[{operation_id}] Post-operation cluster state logged")
        
        return result
        
    except Exception as e:
        print(f"[{operation_id}] Operation failed with exception: {e}")
        raise
```

### 4. Resource Cleanup

```python
async def operation_with_cleanup(session):
    """Demonstrate proper resource cleanup patterns."""
    
    original_mode = None
    
    try:
        # Store original mode
        mode_info = await session.call_tool("get_current_mode", {})
        original_mode = mode_info["data"]["mode_type"]
        
        # Switch to required mode
        await session.call_tool("switch_mode", {"mode": "config_edit"})
        
        # Perform operations...
        
    finally:
        # Always restore original mode
        if original_mode:
            await session.call_tool("switch_mode", {"mode": original_mode})
```

This usage guide provides comprehensive examples for integrating the Ambari MCP Server into various workflows and applications. The patterns shown here can be adapted for specific use cases and integrated into larger automation systems. 