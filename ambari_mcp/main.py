"""Main entry point for Ambari MCP Server."""

import asyncio
import logging
import signal
import sys
from typing import Optional

import click
import uvicorn
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.table import Table

from .config import Settings, get_settings, MCPModeType
from .server import AmbariMCPServer
from .fastapi_app import get_fastapi_app


# Global console for rich output
console = Console()


def setup_logging(settings: Settings):
    """Setup logging configuration."""
    log_level = getattr(logging, settings.logging.level.value)
    
    if settings.logging.format.value == "json":
        import structlog
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
        
        logging.basicConfig(
            level=log_level,
            handlers=[logging.FileHandler(settings.logging.file)] if settings.logging.file else [],
            format="%(message)s"
        )
    else:
        # Rich text logging
        logging.basicConfig(
            level=log_level,
            format="%(message)s",
            datefmt="[%X]",
            handlers=[RichHandler(rich_tracebacks=True)]
        )
    
    # Set third-party library log levels
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn").setLevel(logging.INFO)


def display_banner(settings: Settings):
    """Display application banner."""
    banner_text = f"""
[bold blue]Ambari MCP Server[/bold blue]
Version: {settings.mcp_server.version}
Mode: {settings.mcp_server.mode.value}

[yellow]Ambari Connection:[/yellow]
Host: {settings.ambari.host}:{settings.ambari.port}
Cluster: {settings.ambari.cluster_name or 'Auto-detect'}

[green]Server Configuration:[/green]
MCP Port: {settings.mcp_server.port}
FastAPI Port: {settings.fastapi.port}
    """
    
    console.print(Panel(banner_text, title="🚀 Starting Ambari MCP Server", border_style="blue"))


def display_mode_info(settings: Settings):
    """Display operational mode information."""
    mode_descriptions = {
        MCPModeType.NORMAL: "Full access to all operations with confirmations for dangerous actions",
        MCPModeType.CLUSTER_MAINTENANCE: "Restricted mode for maintenance - only monitoring and safe shutdown",
        MCPModeType.SCALE_UP: "Optimized for scaling operations - service shutdowns disabled",
        MCPModeType.CONFIG_EDIT: "Configuration management mode - service operations disabled",
        MCPModeType.DEVELOPMENT: "Development mode with enhanced logging and no confirmations"
    }
    
    table = Table(title="Operational Modes")
    table.add_column("Mode", style="cyan")
    table.add_column("Description", style="white")
    table.add_column("Current", style="green")
    
    for mode, description in mode_descriptions.items():
        current = "✓" if mode == settings.mcp_server.mode else ""
        table.add_row(mode.value, description, current)
    
    console.print(table)


# Global server instance for signal handling
server_instance: Optional[AmbariMCPServer] = None


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    console.print("\n[yellow]Received shutdown signal. Cleaning up...[/yellow]")
    if server_instance:
        asyncio.create_task(server_instance.shutdown())
    sys.exit(0)


@click.group()
@click.option('--config', '-c', help='Configuration file path')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.pass_context
def cli(ctx, config, verbose):
    """Ambari MCP Server - Model Context Protocol server for Apache Ambari."""
    ctx.ensure_object(dict)
    
    # Load settings
    settings = get_settings()
    if verbose:
        from .config import LogLevel
        settings.logging.level = LogLevel.DEBUG
    
    setup_logging(settings)
    ctx.obj['settings'] = settings


@cli.command()
@click.option('--host', default='0.0.0.0', help='Host to bind to')
@click.option('--port', default=8001, help='Port to bind to')
@click.option('--transport', default='stdio', type=click.Choice(['stdio', 'sse', 'streamable-http']),
              help='Transport protocol to use')
@click.pass_context
def run_mcp(ctx, host, port, transport):
    """Run the MCP server."""
    settings = ctx.obj['settings']
    global server_instance
    
    # For stdio transport, suppress all console output to avoid breaking JSON-RPC
    if transport != 'stdio':
        display_banner(settings)
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        server_instance = AmbariMCPServer(settings)
        
        if transport != 'stdio':
            console.print(f"[green]Starting MCP server with {transport} transport on {host}:{port}[/green]")
        
        # Use the async versions of the FastMCP methods that don't create their own event loop
        async def run_server():
            if transport == 'stdio':
                await server_instance.run_stdio()
            elif transport == 'sse':
                await server_instance.run_sse(host, port)
            elif transport == 'streamable-http':
                await server_instance.run_streamable_http(host, port)
        
        # Run the server with asyncio.run()
        asyncio.run(run_server())
                
    except KeyboardInterrupt:
        if transport != 'stdio':
            console.print("\n[yellow]Shutting down MCP server...[/yellow]")
    except Exception as e:
        # For stdio mode, print errors to stderr to avoid breaking JSON-RPC
        if transport == 'stdio':
            print(f"Error running MCP server: {e}", file=sys.stderr)
        else:
            console.print(f"[red]Error running MCP server: {e}[/red]")
        raise
    finally:
        # Cleanup
        if server_instance:
            async def cleanup():
                await server_instance.shutdown()
            try:
                asyncio.run(cleanup())
            except Exception as e:
                if transport == 'stdio':
                    print(f"Cleanup error: {e}", file=sys.stderr)
                else:
                    console.print(f"[yellow]Cleanup error: {e}[/yellow]")


@cli.command()
@click.option('--host', default='0.0.0.0', help='Host to bind to')
@click.option('--port', default=8000, help='Port to bind to')
@click.option('--reload', is_flag=True, help='Enable auto-reload for development')
@click.pass_context
def run_fastapi(ctx, host, port, reload):
    """Run the FastAPI REST interface."""
    settings = ctx.obj['settings']
    
    display_banner(settings)
    
    console.print(f"[green]Starting FastAPI server on {host}:{port}[/green]")
    console.print(f"[blue]API Documentation: http://{host}:{port}/docs[/blue]")
    
    # Update settings
    settings.fastapi.host = host
    settings.fastapi.port = port
    settings.fastapi.reload = reload
    
    app = get_fastapi_app()
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=reload,
        log_level=settings.logging.level.value.lower()
    )


@cli.command()
@click.option('--mcp-host', default='0.0.0.0', help='MCP server host')
@click.option('--mcp-port', default=8001, help='MCP server port')
@click.option('--api-host', default='0.0.0.0', help='FastAPI server host')
@click.option('--api-port', default=8000, help='FastAPI server port')
@click.option('--mcp-transport', default='streamable-http', 
              type=click.Choice(['sse', 'streamable-http']), help='MCP transport protocol')
@click.pass_context
async def run_both(ctx, mcp_host, mcp_port, api_host, api_port, mcp_transport):
    """Run both MCP server and FastAPI interface concurrently."""
    settings = ctx.obj['settings']
    global server_instance
    
    display_banner(settings)
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    async def run_mcp_server():
        """Run MCP server."""
        try:
            server_instance = AmbariMCPServer(settings)
            console.print(f"[green]Starting MCP server with {mcp_transport} transport on {mcp_host}:{mcp_port}[/green]")
            
            if mcp_transport == 'sse':
                await server_instance.run_sse(mcp_host, mcp_port)
            else:
                await server_instance.run_streamable_http(mcp_host, mcp_port)
        except Exception as e:
            console.print(f"[red]MCP server error: {e}[/red]")
            raise
    
    def run_fastapi_server():
        """Run FastAPI server."""
        try:
            console.print(f"[green]Starting FastAPI server on {api_host}:{api_port}[/green]")
            console.print(f"[blue]API Documentation: http://{api_host}:{api_port}/docs[/blue]")
            
            app = get_fastapi_app()
            uvicorn.run(
                app,
                host=api_host,
                port=api_port,
                log_level=settings.logging.level.value.lower()
            )
        except Exception as e:
            console.print(f"[red]FastAPI server error: {e}[/red]")
            raise
    
    try:
        # Run both servers concurrently
        await asyncio.gather(
            run_mcp_server(),
            asyncio.to_thread(run_fastapi_server)
        )
    except KeyboardInterrupt:
        console.print("\n[yellow]Shutting down servers...[/yellow]")
    finally:
        if server_instance:
            await server_instance.shutdown()


@cli.command()
@click.pass_context
def info(ctx):
    """Display server information and configuration."""
    settings = ctx.obj['settings']
    
    # Server info
    console.print(Panel(f"""
[bold blue]Ambari MCP Server Information[/bold blue]

[yellow]Version:[/yellow] {settings.mcp_server.version}
[yellow]Current Mode:[/yellow] {settings.mcp_server.mode.value}

[yellow]Ambari Configuration:[/yellow]
  Host: {settings.ambari.host}:{settings.ambari.port}
  Username: {settings.ambari.username}
  SSL: {'Enabled' if settings.ambari.use_ssl else 'Disabled'}
  Cluster: {settings.ambari.cluster_name or 'Auto-detect'}

[yellow]Server Configuration:[/yellow]
  MCP Host: {settings.mcp_server.host}:{settings.mcp_server.port}
  FastAPI Host: {settings.fastapi.host}:{settings.fastapi.port}
  Log Level: {settings.logging.level.value}
    """, title="Server Information", border_style="blue"))
    
    # Display mode information
    display_mode_info(settings)


@cli.command()
@click.argument('cluster_name', required=False)
@click.pass_context
def test_connection(ctx, cluster_name):
    """Test connection to Ambari server."""
    async def _test():
        settings = ctx.obj['settings']
        
        console.print("[yellow]Testing Ambari connection...[/yellow]")
        
        try:
            from .client import AmbariClient
            
            async with AmbariClient(settings.ambari) as client:
                # Test basic connectivity
                clusters = await client.get_clusters()
                
                if not clusters:
                    console.print("[red]❌ No clusters found[/red]")
                    return
                
                console.print(f"[green]✅ Connected successfully![/green]")
                console.print(f"[blue]Found {len(clusters)} cluster(s):[/blue]")
                
                for cluster in clusters:
                    console.print(f"  • {cluster.cluster_name} (Version: {cluster.version}, Hosts: {cluster.total_hosts})")
                
                # Test health check
                if cluster_name:
                    target_cluster = cluster_name
                else:
                    target_cluster = clusters[0].cluster_name
                
                console.print(f"\n[yellow]Running health check for cluster '{target_cluster}'...[/yellow]")
                health = await client.health_check()
                
                status_color = "green" if health["status"] == "healthy" else "yellow" if health["status"] == "degraded" else "red"
                console.print(f"[{status_color}]Status: {health['status'].upper()}[/{status_color}]")
                
                if "details" in health:
                    details = health["details"]
                    if details.get("unhealthy_services"):
                        console.print(f"[red]Unhealthy services: {', '.join(details['unhealthy_services'])}[/red]")
                    if details.get("unhealthy_hosts"):
                        console.print(f"[red]Unhealthy hosts: {', '.join(details['unhealthy_hosts'])}[/red]")
                        
                console.print(f"\n[green]✅ Ambari connection test completed successfully![/green]")
                
        except Exception as e:
            console.print(f"[red]❌ Connection failed: {e}[/red]")
            import traceback
            if ctx.obj.get('verbose'):
                console.print(f"[red]Traceback: {traceback.format_exc()}[/red]")
            sys.exit(1)
    
    asyncio.run(_test())


# Async command wrapper
def async_command(f):
    """Decorator to run async commands."""
    import functools
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))
    return wrapper


# Apply async wrapper to async commands
run_both = async_command(run_both)


def main():
    """Main entry point."""
    try:
        cli()
    except KeyboardInterrupt:
        # Check if we're in stdio mode by looking at command line args
        if '--transport' in sys.argv and 'stdio' in sys.argv:
            print("Interrupted by user", file=sys.stderr)
        else:
            console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        # Check if we're in stdio mode by looking at command line args
        if '--transport' in sys.argv and 'stdio' in sys.argv:
            print(f"Fatal error: {e}", file=sys.stderr)
        else:
            console.print(f"[red]Fatal error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main() 