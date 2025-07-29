from setuptools import setup, find_packages

setup(
    name="ambari_mcp",
    version="1.0.0",
    description="MCP Server for Apache Ambari Operations",
    author="Ambari MCP Team",
    packages=find_packages(),
    python_requires=">=3.11",
    install_requires=[
        "mcp[cli]==1.12.2",
        "fastapi==0.115.6",
        "uvicorn[standard]==0.32.1",
        "httpx==0.28.1",
        "aiohttp==3.11.11",
        "pydantic==2.10.4",
        "pydantic-settings==2.7.0",
        "asyncio-mqtt==0.16.2",
        "structlog==25.4.0",
        "click==8.1.8",
        "rich==13.9.4",
        "python-multipart==0.0.20",
    ],
    entry_points={
        "console_scripts": [
            "ambari-mcp=ambari_mcp.main:main",
        ],
    },
) 