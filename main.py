from mcp.server.fastmcp import FastMCP
import mcp_definitions.ambari as ambari

# Initialize FastMCP server
mcp = FastMCP(title="ambari-mcp", description="Serve api tools for ambari")

# Register all Ambari components (tools, resources, prompts)
ambari.register_all(mcp)

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')