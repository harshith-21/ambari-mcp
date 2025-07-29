# Claude Desktop Setup Guide

## Quick Setup (5 minutes)

### 1. Install Ambari MCP Server
```bash
# Install the server
pip install -r requirements.txt
pip install -e .

# Test it works
python -m ambari_mcp.main test-connection
```

### 2. Configure Claude Desktop

Find your config file:
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json` 
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

### 3. Add Configuration

#### For Single Cluster (Simple):
```json
{
  "mcpServers": {
    "ambari": {
      "command": "python",
      "args": ["-m", "ambari_mcp.main", "run-mcp", "--transport", "stdio"],
      "env": {
        "AMBARI_HOST": "your-ambari-server.com",
        "AMBARI_USERNAME": "admin",
        "AMBARI_PASSWORD": "admin"
      }
    }
  }
}
```

#### For Multiple Clusters (Advanced):
```json
{
  "mcpServers": {
    "ambari-enhanced": {
      "command": "python",
      "args": [
        "-c", 
        "from ambari_mcp.enhanced_server import EnhancedAmbariMCPServer; from ambari_mcp.config import Settings; import asyncio; asyncio.run(EnhancedAmbariMCPServer(Settings()).run_stdio())"
      ]
    }
  }
}
```

### 4. Restart Claude Desktop

Completely quit and restart Claude Desktop.

### 5. Test the Connection

In Claude Desktop, try:

**Single Cluster:**
```
"What's the status of my Ambari cluster?"
```

**Multiple Clusters:**
```
"I have clusters at dev.company.com and prod.company.com - register both and check their health"
```

## Conversation Examples

### Basic Cluster Management
```
You: Check my cluster health
Claude: [Uses health_check tool] Your cluster is healthy with 12 services running...

You: Start the YARN service
Claude: [Uses start_service] Starting YARN service... Request submitted successfully.

You: Switch to maintenance mode  
Claude: [Uses switch_mode] Switched to cluster_maintenance mode for safety.
```

### Multi-Cluster Management
```
You: Register my dev cluster at 192.168.1.100
Claude: [Uses register_ambari_target] Registered development cluster successfully.

You: Show me all my registered clusters
Claude: [Uses list_ambari_targets] You have 2 registered clusters: development, production

You: Check health of all clusters
Claude: [Uses health_check_all_targets] Development: Healthy, Production: Degraded (2 services down)
```

### Advanced Operations
```
You: I need to do maintenance on my production environment
Claude: I'll help you with maintenance. Let me switch to maintenance mode and provide a checklist.
[Uses switch_mode and maintenance_checklist prompt]

You: Update HDFS configuration to increase block size
Claude: I'll switch to config_edit mode for safety and help you update the configuration.
[Uses switch_mode, then update_configuration]
```

## Troubleshooting

### Server Not Found
```
Error: Server "ambari" not found
```
- Check the config file path is correct
- Verify JSON syntax is valid
- Restart Claude Desktop completely

### Connection Failed
```
Error: Failed to connect to Ambari
```
- Check `AMBARI_HOST` is accessible
- Verify username/password are correct
- Test with: `python -m ambari_mcp.main test-connection`

### Python Module Not Found
```
Error: No module named 'ambari_mcp'
```
- Run `pip install -e .` in the project directory
- Check Python path includes the project

## Features Available in Claude

✅ **All MCP Tools**: 19+ tools for cluster management
✅ **Mode Switching**: Normal, maintenance, scale-up, config-edit, development
✅ **Multi-Cluster**: Enhanced server supports multiple clusters
✅ **Context Awareness**: Claude understands operational context
✅ **Safety Features**: Confirmations for dangerous operations
✅ **Real-time Monitoring**: Health checks and request status
✅ **Configuration Management**: Safe config updates with rollback

## Security Notes

- Credentials are in the config file (consider using environment variables)
- Enhanced server allows per-conversation credentials (more secure)
- Use SSL for production environments
- Consider using service accounts with limited permissions

## Next Steps

1. **Start Simple**: Use single cluster config first
2. **Test Operations**: Try basic health checks and service management
3. **Explore Modes**: Switch between operational modes
4. **Multi-Cluster**: Upgrade to enhanced server for multiple clusters
5. **Automation**: Build complex workflows using Claude's reasoning

Happy cluster management! 🚀 