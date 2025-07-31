from mcp.server.fastmcp import FastMCP
from .tools import register_tools as register_ambari_tools
from .resources import register_resources as register_ambari_resources  
from .prompts import register_prompts as register_ambari_prompts

def register_tools(mcp: FastMCP):
    """Register all Ambari tools with the MCP server"""
    register_ambari_tools(mcp)

def register_resources(mcp: FastMCP):
    """Register all Ambari resources with the MCP server"""
    register_ambari_resources(mcp)

def register_prompts(mcp: FastMCP):
    """Register all Ambari prompts with the MCP server"""
    register_ambari_prompts(mcp)

def register_all(mcp: FastMCP):
    """Register all Ambari MCP components (tools, resources, prompts)"""
    register_tools(mcp)
    register_resources(mcp)
    register_prompts(mcp) 