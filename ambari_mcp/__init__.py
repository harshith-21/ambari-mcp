"""
Ambari MCP Server - Model Context Protocol server for Apache Ambari operations.

This package provides a comprehensive MCP server that enables LLMs to interact
with Apache Ambari clusters through standardized tools, resources, and prompts.
"""

__version__ = "1.0.0"
__author__ = "Ambari MCP Team"
__description__ = "MCP Server for Apache Ambari Operations"

from .server import AmbariMCPServer
from .client import AmbariClient
from .modes import MCPMode, MCPModeManager
from .config import Settings

__all__ = [
    "AmbariMCPServer",
    "AmbariClient", 
    "MCPMode",
    "MCPModeManager",
    "Settings",
] 