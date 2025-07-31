# Ambari MCP Server

A Model Context Protocol (MCP) server that provides tools for interacting with Apache Ambari clusters.

## Features

- Get cluster information from Ambari servers
- Built with FastMCP for easy tool development
- Uses `uv` for fast dependency management

## Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) package manager
- Access to an Ambari server

## Quick Start

### 1. Setup the project

```bash
make all
```

This creates the `config.json` file needed for MCP integration.

### 2. Run the server

```bash
make run
```

## Available Make Commands

| Command | Description |
|---------|-------------|
| `make all` | Create config.json (default target) |
| `make config` | Create config.json for MCP integration |
| `make sync` | Sync dependencies with uv |
| `make run` | Run the MCP server |
| `make clean` | Remove config.json and clean uv cache |
| `make help` | Show all available commands |

## Configuration

The `make config` command creates a `config.json` file with the following structure:

```json
{
  "mcpServers": {
    "ambari-mcp": {
      "command": "/path/to/uv",
      "args": [
        "--directory",
        "/path/to/project",
        "run",
        "main.py"
      ]
    }
  }
}
```

This configuration can be used with MCP-compatible clients like Claude Desktop.

## Available Tools

### Component Management Tools
- **Service Operations**: `start_service`, `stop_service`, `restart_service`
- **Component Operations**: `start_component`, `stop_component`, `restart_component`
- **Status Monitoring**: `get_service_status`

### Configuration Management Tools
- **Configuration Retrieval**: `get_service_config`, `get_service_config_versions`
- **Configuration Updates**: `update_service_config`, `rollback_service_config`
- **Repository Management**: `update_repository_url`, `register_repository_version`, `get_cluster_repositories`

### Service Health & Monitoring Tools
- **Health Checks**: `run_service_check`, `get_service_health`, `get_component_health`, `get_host_health`
- **Alerts & Monitoring**: `get_alerts`, `get_request_status`, `get_cluster_metrics`

### Cluster Information Tools
- **Basic Info**: `get_cluster_name` - Retrieves cluster name from Ambari server
- **Host Inventory**: `get_all_hosts` - Lists all hosts using `/api/v1/clusters/{cluster}/hosts`
- **Host Details**: `get_host_details` - Gets detailed host metrics including memory using `/api/v1/clusters/{cluster}/hosts/{hostname}`
- **Host Components**: `get_host_components` - Lists all components on a specific host
- **Cluster Summary**: `get_cluster_host_summary` - Aggregated cluster-wide host metrics and health status

### Example Usage:
```python
# Get all hosts in cluster (real API call)
get_all_hosts(
    server_url="http://ambari-server.example.com",
    cluster_name="ODP_Quantum",
    username="admin",
    password="admin",
    port="8080"
)

# Get detailed host metrics including memory (real API call)
get_host_details(
    server_url="http://ambari-server.example.com",
    cluster_name="ODP_Quantum", 
    hostname="master1.example.com",
    username="admin",
    password="admin",
    port="8080"
)

# Restart a service (single operation, not stop+start)
restart_service(
    server_url="http://ambari-server.example.com",
    cluster_name="my-cluster",
    service_name="HDFS",
    username="admin",
    password="admin",
    port="8080"
)

# Update repository URL for new version
update_repository_url(
    server_url="http://ambari-server.example.com",
    cluster_name="my-cluster",
    stack_name="HDP",
    stack_version="2.7",
    os_type="redhat7",
    repo_id="HDP-2.7",
    base_url="http://new-repo.example.com/HDP/centos7/2.x/updates/2.7.8.0"
)

# Get comprehensive service health
get_service_health(
    server_url="http://ambari-server.example.com",
    cluster_name="my-cluster",
    service_name="YARN"
)
```

## Development

### Project Structure

```
ambari-mcp/
├── main.py                                    # MCP server implementation
├── pyproject.toml                            # Project dependencies
├── Makefile                                  # Build and run commands
├── config.json                               # MCP configuration (generated)
├── README.md                                 # This file
└── mcp_definitions/                          # MCP definitions
    └── ambari/                               # Ambari component
        ├── __init__.py                       # Unified registration
        ├── tools/                            # MCP Tools (Functions)
        │   ├── __init__.py                   # Tools registration
        │   ├── cluster_info.py               # Cluster information tools
        │   ├── component_management.py       # Start/stop/restart services & components
        │   ├── config_management.py          # Configuration & repository management
        │   └── service_checks.py             # Health checks & monitoring
        ├── resources/                        # MCP Resources (File-like data)
        │   ├── __init__.py                   # Resources registration
        │   ├── cluster_status.py             # Cluster overview & status data
        │   ├── service_configs.py            # Service & configuration data
        │   └── host_info.py                  # Host information & metrics data
        └── prompts/                          # MCP Prompts (Templates)
            ├── __init__.py                   # Prompts registration
            ├── troubleshooting.py            # Troubleshooting guides & workflows
            ├── deployment.py                 # Deployment templates (future)
            └── maintenance.py                # Maintenance procedures (future)
```

### Dependencies

The project uses `uv` for dependency management. Dependencies are defined in `pyproject.toml`:

- `fastmcp`: Framework for building MCP servers
- `httpx`: HTTP client for API requests

## Available Resources

### Cluster Status Resources
- **Cluster Overview**: `ambari://cluster-overview/{cluster_name}` - Basic cluster information
- **Service Status**: `ambari://service-status/{cluster_name}/{service_name}` - Basic service information  
- **Host Details**: `ambari://host-details/{cluster_name}/{host_name}` - Basic host information

### Host Information Resources
- **All Hosts**: `ambari://hosts/{cluster_name}` - Complete host inventory with specs and components
- **Host Components Matrix**: `ambari://host-components/{cluster_name}` - Component distribution across hosts
- **Host Metrics**: `ambari://host-metrics/{cluster_name}` - Resource utilization and performance metrics

### Service Configuration Resources
- **All Services**: `ambari://services/{cluster_name}` - Complete service inventory with status and components
- **Configuration Types**: `ambari://config-types/{cluster_name}` - Available configuration files and versions
- **Cluster Alerts**: `ambari://alerts/{cluster_name}` - Current alerts, warnings, and recommendations

**Note**: Resources provide structured sample data that LLMs can read and understand. For real-time data with server connections and authentication, use the **Tools** instead.

### Example Resource Usage:
```
# Get complete host inventory
ambari://hosts/my-cluster

# Get all services and their status
ambari://services/my-cluster

# Get component distribution matrix
ambari://host-components/my-cluster

# Get current alerts and recommendations
ambari://alerts/my-cluster

# Get configuration types and versions
ambari://config-types/my-cluster

# Get host performance metrics
ambari://host-metrics/my-cluster
```

## Available Prompts

### Troubleshooting Prompts
- **Service Down**: `ambari-service-down-troubleshooting` - Step-by-step service recovery guide
- **Performance Issues**: `ambari-performance-issues` - Performance troubleshooting and optimization
- **Configuration Management**: `ambari-configuration-management` - Safe configuration change procedures

### Example Prompt Usage:
```
# Get troubleshooting guide for HDFS service issues
ambari-service-down-troubleshooting(service_name="HDFS", cluster_name="my-cluster")

# Get performance troubleshooting guide
ambari-performance-issues(cluster_name="my-cluster")
```

### Adding New Components

To add a new component (e.g., `kafka`, `spark`):

1. **Create component directory**: `mcp_definitions/kafka/`
2. **Follow the same structure**:
   ```
   kafka/
   ├── __init__.py           # Unified registration
   ├── tools/                # Kafka-specific tools
   ├── resources/            # Kafka-specific resources  
   └── prompts/              # Kafka-specific prompts
   ```
3. **Update main.py**:
   ```python
   import mcp_definitions.kafka as kafka
   kafka.register_all(mcp)
   ```

### Adding New Tools to Existing Components

1. Add new functions to appropriate module in `mcp_definitions/ambari/tools/`
2. Follow existing patterns for async functions and type hints
3. Include comprehensive docstrings with parameter descriptions
4. Test with `make run`

## Troubleshooting

### Common Issues

1. **`uv` not found**: Install uv following the [official documentation](https://docs.astral.sh/uv/getting-started/installation/)

2. **Permission errors**: Ensure the project directory is writable

3. **Connection errors**: Verify Ambari server URL, credentials, and network connectivity

### Cleaning Up

If you encounter issues, try cleaning and rebuilding:

```bash
make clean
make all
```

## License

This project is open source. Please check the license file for details.
