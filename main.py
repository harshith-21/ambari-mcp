from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP(title="ambari-mcp", description="Serve api tools for ambari")

#### TOOLS ####

@mcp.tool()
async def get_cluster_name(server_url :str, username :str="admin", password :str="admin", port :str="8080") -> str:
    """print cluster name.

    Args:
        server_url: The url of the ambari server
        username: The username to access the ambari server
        password: The password to access the ambari server
        port: The port of the ambari server
    """
    # Create a client
    client = httpx.AsyncClient()

    # Get the cluster name
    response = await client.get(f"{server_url}:{port}/api/v1/clusters", auth=(username, password))
    cluster_name = response.json()["items"][0]["Clusters"]["cluster_name"]

    return cluster_name

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')