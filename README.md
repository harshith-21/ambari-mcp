# Ambari MCP Server

A comprehensive **Model Context Protocol (MCP) server** for Apache Ambari cluster management, enabling LLMs to interact with Ambari clusters through standardized tools, resources, and prompts.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-1.12.2-green.svg)](https://pypi.org/project/mcp/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.6-red.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)

## 🚀 Features

### Core MCP Capabilities
- **🛠️ Comprehensive Tools**: Service management, host monitoring, configuration updates, health checks
- **📄 Rich Resources**: Cluster status, operational modes, documentation
- **💬 Context-Aware Prompts**: Maintenance workflows, scaling guides, configuration management
- **🔄 Mode-Based Operations**: Different behavioral contexts for various operational scenarios

### Operational Modes
- **Normal**: Full access with safety confirmations
- **Cluster Maintenance**: Restricted to monitoring and safe shutdown operations
- **Scale Up**: Optimized for capacity expansion (prevents accidental shutdowns)
- **Config Edit**: Focused on configuration management (service operations disabled)
- **Development**: Enhanced logging with no confirmations for rapid development

### Integration Options
- **MCP Server**: Standard MCP protocol support (stdio, SSE, streamable HTTP)
- **FastAPI REST Interface**: Web API for demonstrations and integrations
- **CLI Interface**: Command-line tools for server management and testing
- **Docker Support**: Containerized deployment with docker-compose

## 📋 Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Usage Examples](#usage-examples)
- [Architecture](#architecture)
- [API Reference](#api-reference)
- [Development](#development)
- [Docker Deployment](#docker-deployment)
- [Contributing](#contributing)

## 🔧 Installation

### Prerequisites
- Python 3.11 or higher
- Apache Ambari server (accessible via REST API)
- Optional: Docker for containerized deployment

### Install from Source

```bash
# Clone the repository
git clone <repository-url>
cd ambari_mcp

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

### Docker Installation

```bash
# Build and run with docker-compose
docker-compose up -d

# Or build manually
docker build -t ambari-mcp .
docker run -p 8000:8000 -p 8001:8001 ambari-mcp
```

## ⚡ Quick Start

### 1. Configure Ambari Connection

Create a `.env` file (copy from `env.example`):

```bash
# Ambari Configuration
AMBARI_HOST=your-ambari-server
AMBARI_PORT=8080
AMBARI_USERNAME=admin
AMBARI_PASSWORD=admin
AMBARI_CLUSTER_NAME=YourCluster
```

### 2. Test Connection

```bash
python -m ambari_mcp.main test-connection
```

### 3. Run MCP Server

```bash
# Run MCP server with stdio transport
python -m ambari_mcp.main run-mcp

# Run with HTTP transport
python -m ambari_mcp.main run-mcp --transport streamable-http --port 8001

# Run FastAPI interface
python -m ambari_mcp.main run-fastapi --port 8000

# Run both concurrently
python -m ambari_mcp.main run-both
```

### 4. Test with Example Client

```bash
# Run MCP client example
python examples/mcp_client_example.py

# Run FastAPI demo
python examples/fastapi_demo.py
```

## ⚙️ Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AMBARI_HOST` | localhost | Ambari server hostname |
| `AMBARI_PORT` | 8080 | Ambari server port |
| `AMBARI_USERNAME` | admin | Ambari username |
| `AMBARI_PASSWORD` | admin | Ambari password |
| `AMBARI_CLUSTER_NAME` | - | Default cluster name (auto-detect if empty) |
| `AMBARI_USE_SSL` | false | Use HTTPS for Ambari connections |
| `MCP_SERVER_NAME` | ambari-mcp | MCP server name |
| `MCP_MODE` | normal | Initial operational mode |
| `LOG_LEVEL` | INFO | Logging level |

### Operational Modes Configuration

Each mode has specific restrictions and behaviors:

```python
# Normal Mode - Full access with confirmations
mode_manager.switch_mode("normal")

# Maintenance Mode - Read-only with safe shutdown only
mode_manager.switch_mode("cluster_maintenance")

# Scale Up Mode - Prevents service shutdowns
mode_manager.switch_mode("scale_up")

# Config Edit Mode - Configuration management only
mode_manager.switch_mode("config_edit")

# Development Mode - All operations without confirmations
mode_manager.switch_mode("development")
```

## 📚 Usage Examples

### MCP Client Integration

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Connect to Ambari MCP Server
server_params = StdioServerParameters(
    command="python",
    args=["-m", "ambari_mcp.main", "run-mcp", "--transport", "stdio"]
)

async with stdio_client(server_params) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()
        
        # Switch to maintenance mode
        result = await session.call_tool("switch_mode", {
            "mode": "cluster_maintenance",
            "reason": "Scheduled maintenance"
        })
        
        # Get cluster status
        status = await session.call_tool("get_cluster_status", {})
        
        # Stop a service safely
        result = await session.call_tool("stop_service", {
            "service_name": "YARN"
        })
```

### FastAPI REST Interface

```python
import httpx

async with httpx.AsyncClient() as client:
    # Get cluster health
    health = await client.get("http://localhost:8000/cluster/health")
    
    # Switch operational mode
    mode_switch = await client.post("http://localhost:8000/modes/switch", 
        json={"mode": "scale_up", "reason": "Adding new nodes"})
    
    # Start a service
    start_result = await client.post("http://localhost:8000/services/HDFS/start")
```

### CLI Operations

```bash
# Server information
python -m ambari_mcp.main info

# Test Ambari connection
python -m ambari_mcp.main test-connection MyCluster

# Run with specific configuration
python -m ambari_mcp.main run-mcp --host 0.0.0.0 --port 8001 --transport sse

# Run FastAPI with auto-reload
python -m ambari_mcp.main run-fastapi --reload
```

### LLM Integration Examples

#### Cluster Overview Prompt
```
Use the cluster_overview prompt to get a comprehensive view:
- Overall cluster health status
- Service states and any issues  
- Host health and capacity
- Recent operations or changes
- Recommendations for any issues found
```

#### Service Management Workflow
```
1. Switch to appropriate mode for the operation
2. Check current service status
3. Verify service dependencies
4. Execute operation with proper confirmations
5. Monitor operation progress
6. Verify successful completion
```

## 🏗️ Architecture

### Component Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   LLM Client    │    │   FastAPI Web    │    │   CLI Tools     │
│                 │    │   Interface      │    │                 │
└─────────┬───────┘    └────────┬─────────┘    └─────────┬───────┘
          │                     │                        │
          └─────────────────────┼────────────────────────┘
                                │
                    ┌───────────▼───────────┐
                    │   Ambari MCP Server   │
                    │                       │
                    │  ┌─────────────────┐  │
                    │  │  Mode Manager   │  │
                    │  │  - Normal       │  │
                    │  │  - Maintenance  │  │
                    │  │  - Scale Up     │  │
                    │  │  - Config Edit  │  │
                    │  │  - Development  │  │
                    │  └─────────────────┘  │
                    │                       │
                    │  ┌─────────────────┐  │
                    │  │ MCP Components  │  │
                    │  │  - Tools        │  │
                    │  │  - Resources    │  │
                    │  │  - Prompts      │  │
                    │  └─────────────────┘  │
                    └───────────┬───────────┘
                                │
                    ┌───────────▼───────────┐
                    │   Ambari Client      │
                    │   - REST API         │
                    │   - Authentication   │
                    │   - Error Handling   │
                    │   - Retry Logic      │
                    └───────────┬───────────┘
                                │
                    ┌───────────▼───────────┐
                    │  Apache Ambari       │
                    │  Cluster Management  │
                    └─────────────────────────┘
```

### MCP Tools Available

| Tool | Description | Modes |
|------|-------------|-------|
| `switch_mode` | Change operational mode | All |
| `get_cluster_status` | Get comprehensive cluster status | All |
| `list_services` | List all cluster services | All |
| `start_service` | Start a stopped service | Normal, Scale Up, Development |
| `stop_service` | Stop a running service | Normal, Maintenance, Development |
| `restart_service` | Restart a service | Normal, Scale Up, Development |
| `get_service_info` | Get detailed service information | All |
| `list_hosts` | List all cluster hosts | All |
| `get_host_info` | Get detailed host information | All |
| `get_configurations` | Retrieve configuration settings | All |
| `update_configuration` | Update configuration properties | Normal, Scale Up, Config Edit, Development |
| `health_check` | Perform cluster health check | All |
| `get_request_status` | Check operation status | All |

### MCP Resources Available

| Resource | Description |
|----------|-------------|
| `ambari://cluster/{name}/status` | Real-time cluster status |
| `ambari://mode/current` | Current operational mode info |
| `ambari://documentation/modes` | Mode documentation |
| `ambari://documentation/api` | API operation documentation |

### MCP Prompts Available

| Prompt | Description | Use Case |
|--------|-------------|----------|
| `cluster_overview` | Comprehensive cluster analysis | Health monitoring |
| `service_management` | Service operation guidance | Service lifecycle |
| `maintenance_checklist` | Maintenance workflow | Planned maintenance |
| `scale_up_planning` | Capacity expansion guide | Cluster scaling |
| `configuration_management` | Config change workflow | Configuration updates |

## 📖 API Reference

### FastAPI Endpoints

#### Health & Status
- `GET /health` - Server health check
- `GET /status` - Comprehensive server status

#### Mode Management  
- `GET /modes` - List available modes
- `GET /modes/current` - Get current mode
- `POST /modes/switch` - Switch operational mode

#### Cluster Operations
- `GET /cluster/status` - Get cluster status
- `GET /cluster/health` - Cluster health check

#### Service Management
- `GET /services` - List services
- `GET /services/{name}` - Get service details
- `POST /services/{name}/start` - Start service
- `POST /services/{name}/stop` - Stop service
- `POST /services/{name}/restart` - Restart service

#### Host Management
- `GET /hosts` - List hosts
- `GET /hosts/{name}` - Get host details

#### Configuration Management
- `GET /configurations/{type}` - Get configuration
- `PUT /configurations/{type}` - Update configuration

#### Request Monitoring
- `GET /requests` - List recent requests
- `GET /requests/{id}` - Get request status

#### MCP Integration
- `GET /mcp/tools` - List available MCP tools
- `GET /mcp/resources` - List available MCP resources
- `GET /mcp/prompts` - List available MCP prompts

## 🔨 Development

### Setting up Development Environment

```bash
# Clone and setup
git clone <repository-url>
cd ambari_mcp
python -m venv venv
source venv/bin/activate

# Install with development dependencies
pip install -r requirements.txt
pip install -e .

# Run tests
pytest

# Code formatting
black ambari_mcp/
isort ambari_mcp/

# Type checking
mypy ambari_mcp/
```

### Running in Development Mode

```bash
# Run with auto-reload and debug logging
python -m ambari_mcp.main run-both --mcp-transport streamable-http

# Run FastAPI with reload
python -m ambari_mcp.main run-fastapi --reload

# Run in development mode (no confirmations)
MCP_MODE=development python -m ambari_mcp.main run-mcp
```

### Testing

```bash
# Unit tests
pytest tests/

# Integration tests (requires Ambari)
pytest tests/integration/

# Test with example scripts
python examples/mcp_client_example.py
python examples/fastapi_demo.py
```

## 🐳 Docker Deployment

### Using Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Scale for high availability
docker-compose up -d --scale ambari-mcp=3

# Stop services
docker-compose down
```

### Manual Docker Deployment

```bash
# Build image
docker build -t ambari-mcp .

# Run MCP server
docker run -d \
  --name ambari-mcp-server \
  -p 8001:8001 \
  -e AMBARI_HOST=your-ambari-server \
  -e AMBARI_USERNAME=admin \
  -e AMBARI_PASSWORD=admin \
  ambari-mcp

# Run FastAPI interface
docker run -d \
  --name ambari-mcp-api \
  -p 8000:8000 \
  -e AMBARI_HOST=your-ambari-server \
  ambari-mcp \
  python -m ambari_mcp.main run-fastapi
```

### Environment Configuration

```yaml
# docker-compose.override.yml
version: '3.8'
services:
  ambari-mcp:
    environment:
      - AMBARI_HOST=production-ambari.example.com
      - AMBARI_USERNAME=mcp-user
      - AMBARI_PASSWORD=secure-password
      - AMBARI_CLUSTER_NAME=ProductionCluster
      - LOG_LEVEL=INFO
      - MCP_MODE=normal
```

## 🤝 Contributing

We welcome contributions! Please see our contributing guidelines:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes** with proper tests and documentation
4. **Run the test suite**: `pytest`
5. **Format your code**: `black . && isort .`
6. **Commit your changes**: `git commit -m 'Add amazing feature'`
7. **Push to the branch**: `git push origin feature/amazing-feature`
8. **Open a Pull Request**

### Development Guidelines

- Follow PEP 8 style guidelines
- Add type hints for all functions
- Include docstrings for public APIs
- Write tests for new functionality
- Update documentation for new features

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Model Context Protocol](https://github.com/modelcontextprotocol) for the MCP specification
- [Apache Ambari](https://ambari.apache.org/) for cluster management capabilities
- [FastAPI](https://fastapi.tiangolo.com/) for the REST interface framework
- [Anthropic](https://www.anthropic.com/) for MCP development and support

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/your-repo/ambari-mcp/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-repo/ambari-mcp/discussions)
- **Documentation**: See the `/docs` directory for detailed documentation

---

**Built with ❤️ for the Apache Ambari and MCP communities** 